"""
Aegis Drone Command — FastAPI Backend Server
Serves the military-industrial UI and provides REST API endpoints.
"""
import os, sys, json, time, asyncio, threading, tempfile, base64
from datetime import datetime
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PYTHONIOENCODING"] = "utf-8"

from fastapi import FastAPI, UploadFile, File, Query, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

from config import ensure_data_dir, OPENAI_API_KEY, OPENAI_MODEL
from simulators.frames import get_simulated_frames
from simulators.telemetry import TelemetrySimulator
from analysis.vlm_analyzer import analyze_frame
from agent.security_agent import SecurityAgent
from indexing.sqlite_store import SQLiteStore
from indexing.chroma_store import ChromaStore
from alerts.rules_engine import AlertManager

app = FastAPI(title="Aegis Drone Command")

# --- State ---
sim_state = {
    "running": False,
    "halt_requested": False,
    "results": [],
    "alerts": [],
    "frames_done": 0,
    "objects_count": 0,
    "summary": "",
    "total_frames": 30,
}

# --- Static files ---
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# --- API ---
@app.get("/api/status")
async def get_status():
    return sim_state

@app.post("/api/reset")
async def reset_state():
    """Force-reset the simulation state (unlocks if stuck)."""
    sim_state["running"] = False
    sim_state["halt_requested"] = False
    return {"status": "reset", "message": "Simulation state reset successfully"}

@app.post("/api/halt")
async def halt_simulation():
    """Emergency halt — stop the running simulation immediately."""
    if sim_state["running"]:
        sim_state["halt_requested"] = True
        return {"status": "halting", "message": "Emergency halt signal sent. Simulation stopping..."}
    else:
        return {"status": "idle", "message": "No simulation is currently running."}

@app.get("/api/simulate")
async def simulate():
    """SSE endpoint — streams frame results in real-time."""
    # Auto-reset stale lock (if running flag stuck from a dropped connection)
    if sim_state["running"]:
        sim_state["running"] = False

    async def event_generator():
        sim_state["running"] = True
        sim_state["halt_requested"] = False
        sim_state["results"] = []
        sim_state["alerts"] = []
        sim_state["frames_done"] = 0
        sim_state["objects_count"] = 0
        sim_state["summary"] = ""

        try:
            ensure_data_dir()
            sqlite_store = SQLiteStore()
            chroma_store = ChromaStore()
            alert_manager = AlertManager()
            telemetry_sim = TelemetrySimulator()
            sqlite_store.clear_all()
            try: chroma_store.clear_all()
            except: pass

            yield {"event": "status", "data": json.dumps({"message": "Agent initializing..."})}
            agent = SecurityAgent(sqlite_store, chroma_store, alert_manager)
            yield {"event": "status", "data": json.dumps({"message": "Agent ready. Starting patrol..."})}

            frames = get_simulated_frames()
            sim_state["total_frames"] = len(frames)

            for i, frame in enumerate(frames):
                # Check for emergency halt
                if sim_state["halt_requested"]:
                    yield {"event": "halted", "data": json.dumps({
                        "message": "EMERGENCY HALT — Simulation stopped by operator.",
                        "frames_completed": sim_state["frames_done"],
                    })}
                    break

                telemetry = telemetry_sim.get_telemetry(frame["time"], frame["location"])

                loop = asyncio.get_event_loop()
                analysis = await loop.run_in_executor(None, analyze_frame, frame["description"], telemetry)
                agent_result = await loop.run_in_executor(None, agent.process_frame, frame, analysis, telemetry)

                frame_alerts = [a for a in alert_manager.fired_alerts if a not in sim_state["alerts"]]
                sim_state["alerts"].extend(frame_alerts)

                objects = analysis.get("objects", [])
                sim_state["objects_count"] += len(objects)
                sim_state["frames_done"] = i + 1

                entry = {
                    "frame_id": frame["frame_id"],
                    "time": frame["time"],
                    "location": frame["location"],
                    "objects": objects,
                    "event_type": analysis.get("event_type", "unknown"),
                    "risk_level": analysis.get("risk_level", "low").upper(),
                    "description": analysis.get("description", ""),
                    "is_suspicious": analysis.get("is_suspicious", False),
                    "recommended_action": analysis.get("recommended_action", ""),
                    "agent_response": agent_result.get("agent_response", ""),
                    "alerts": frame_alerts,
                }
                sim_state["results"].append(entry)
                yield {"event": "frame", "data": json.dumps(entry, default=str)}
                await asyncio.sleep(0.5)

            # Generate summary
            yield {"event": "status", "data": json.dumps({"message": "Generating AI summary..."})}
            try:
                summary = await loop.run_in_executor(None, agent.get_summary)
                sim_state["summary"] = summary
            except Exception as e:
                sim_state["summary"] = f"Summary error: {e}"

            try: sqlite_store.close()
            except: pass

            yield {"event": "complete", "data": json.dumps({
                "summary": sim_state["summary"],
                "total_frames": sim_state["frames_done"],
                "total_alerts": len(sim_state["alerts"]),
                "total_objects": sim_state["objects_count"],
            })}
        except asyncio.CancelledError:
            pass
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"message": str(e)})}
        finally:
            sim_state["running"] = False

    return EventSourceResponse(event_generator())

@app.get("/api/alerts")
async def get_alerts(severity: str = None):
    alerts = sim_state["alerts"]
    if severity:
        alerts = [a for a in alerts if a.get("severity","").upper() == severity.upper()]
    return {"alerts": alerts, "total": len(alerts)}

@app.get("/api/frames")
async def get_frames():
    return {"frames": sim_state["results"], "total": len(sim_state["results"])}

@app.get("/api/frames/search")
async def search_frames(q: str = "", time_filter: str = "any", risk: str = ""):
    try:
        store = SQLiteStore()
        if q:
            results = store.query_by_object(q)
        else:
            results = store.get_all_frames()
        if risk:
            results = [r for r in results if r.get("risk_level","").upper() == risk.upper()]
        if time_filter == "after_hours":
            results = [r for r in results if _is_after_hours(r.get("timestamp",""))]
        elif time_filter == "business":
            results = [r for r in results if not _is_after_hours(r.get("timestamp",""))]
        store.close()
        return {"results": results, "total": len(results)}
    except Exception as e:
        return {"results": [], "total": 0, "error": str(e)}

@app.get("/api/semantic")
async def semantic_search(q: str = ""):
    try:
        chroma = ChromaStore()
        results = chroma.semantic_search(q, top_k=10)
        return {"results": results, "total": len(results)}
    except Exception as e:
        return {"results": [], "total": 0, "error": str(e)}

@app.get("/api/summary")
async def get_summary():
    return {"summary": sim_state["summary"]}

@app.post("/api/generate_summary")
async def generate_summary_now():
    """Generate a fresh AI summary from stored data."""
    if sim_state["running"]:
        return JSONResponse({"error": "Simulation is running, please wait"}, 409)

    results = sim_state["results"]
    if not results:
        return {"summary": "No data available. Run simulation from Live Feed first to collect frame data."}

    try:
        # Build context from in-memory results
        frame_summaries = []
        for r in results:
            risk = r.get("risk_level", "LOW")
            objs = ", ".join(r.get("objects", []))
            desc = r.get("description", "")
            frame_summaries.append(
                f"Frame {r.get('frame_id','?')} at {r.get('time','')} [{r.get('location','')}]: "
                f"Risk={risk}, Objects=[{objs}], Description: {desc}"
            )

        alert_count = len(sim_state["alerts"])
        total_frames = sim_state["frames_done"]
        total_objects = sim_state["objects_count"]

        context = (
            f"Monitoring Session Report:\n"
            f"Total Frames Analyzed: {total_frames}\n"
            f"Total Objects Detected: {total_objects}\n"
            f"Total Alerts Fired: {alert_count}\n\n"
            f"Frame Details:\n" + "\n".join(frame_summaries)
        )

        sqlite_store = SQLiteStore()
        chroma_store = ChromaStore()
        alert_manager = AlertManager()
        agent = SecurityAgent(sqlite_store, chroma_store, alert_manager)

        # Ask agent to summarize with context
        loop = asyncio.get_event_loop()
        def _gen():
            try:
                result = agent.agent.invoke({
                    "messages": [
                        {"role": "user", "content": f"Based on the following surveillance monitoring data, generate a comprehensive security summary:\n\n{context}\n\nProvide a professional security briefing with key findings, risk assessment, and recommendations."}
                    ]
                })
                output_messages = result.get("messages", [])
                for msg in reversed(output_messages):
                    if hasattr(msg, 'content') and msg.content and hasattr(msg, 'type') and msg.type == 'ai':
                        return msg.content
                return "Summary generated but no content returned."
            except Exception as e:
                return f"Error: {e}"

        summary = await loop.run_in_executor(None, _gen)
        sim_state["summary"] = summary
        sqlite_store.close()
        return {"summary": summary}
    except Exception as e:
        return {"summary": f"Error generating summary: {str(e)}"}

# --- Video Analysis ---
from openai import OpenAI as _OpenAI
_vision_client = _OpenAI(api_key=OPENAI_API_KEY)

# Lazy-loaded Grounding DINO detector for video analysis
_gdino_detector = None

def _get_detector():
    """Lazily initialize Grounding DINO detector to avoid slow startup."""
    global _gdino_detector
    if _gdino_detector is None:
        from detector import VideoDetector
        _gdino_detector = VideoDetector(confidence=0.3)
    else:
        _gdino_detector.reset()
    return _gdino_detector

def _extract_frames(video_path, interval_sec=2, max_frames=20):
    """Extract frames from video at regular intervals with high quality."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total / fps

    # Dynamically adjust interval to cover more of the video
    if duration > 0:
        # Aim for ~max_frames evenly spaced across the video
        ideal_interval = max(duration / max_frames, 1.0)
        interval_sec = min(interval_sec, ideal_interval)

    step = max(int(fps * interval_sec), 1)
    frames = []
    idx = 0
    while cap.isOpened() and len(frames) < max_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            break
        # Higher JPEG quality for better object identification
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        b64 = base64.b64encode(buf).decode('utf-8')
        timestamp_sec = idx / fps
        frames.append({
            "index": len(frames),
            "timestamp": f"{int(timestamp_sec//60):02d}:{int(timestamp_sec%60):02d}",
            "base64": b64,
            "raw_frame": frame,  # Keep raw frame for Grounding DINO detection
        })
        idx += step
    cap.release()
    return frames, round(duration, 1)

def _detect_objects_gdino(frame_bgr):
    """Run Grounding DINO object detection on a raw OpenCV frame."""
    try:
        detector = _get_detector()
        result = detector.process_frame(frame_bgr)
        objects = []
        seen = set()
        for track in result.get("active_tracks", []):
            label = track.get("label", "unknown")
            if label not in seen:
                objects.append(label)
                seen.add(label)
        for det in result.get("raw_detections", []):
            label = det.get("label", "unknown")
            if label not in seen:
                objects.append(label)
                seen.add(label)
        return objects, result.get("raw_detections", [])
    except Exception as e:
        print(f"  [Grounding DINO Error] {e}")
        return [], []

def _describe_frame_with_vision(b64_image, detected_objects=None):
    """Send frame to OpenAI Vision API for detailed description."""
    detector_hint = ""
    if detected_objects:
        detector_hint = f"\n\nNote: Grounding DINO (open-vocabulary detector) has identified these objects in the frame: {', '.join(detected_objects)}. Use this to cross-reference your analysis."
    try:
        resp = _vision_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "You are an expert security surveillance analyst specializing in drone footage analysis. "
                    "Your job is to provide extremely detailed, accurate descriptions of what you see in each frame.\n\n"
                    "IMPORTANT — You MUST identify and list:\n"
                    "1. ALL people visible: count them, describe their clothing, positions, and actions\n"
                    "2. ALL vehicles: type (car, truck, van, motorcycle, bicycle), color, make/model if visible, license plates if readable\n"
                    "3. ALL animals: species, count, behavior\n"
                    "4. ALL objects of interest: bags, packages, tools, weapons, barriers, equipment\n"
                    "5. Environmental details: lighting conditions (day/night), weather, visibility\n"
                    "6. Activities: what are people/vehicles doing? entering, leaving, loading, standing, running?\n"
                    "7. Security concerns: anything unusual, out of place, or suspicious\n\n"
                    "Be SPECIFIC with numbers (e.g., '3 people' not 'several people'). "
                    "Be SPECIFIC with positions (e.g., 'near the entrance gate' not 'in the area'). "
                    "Describe in 4-6 detailed sentences."
                )},
                {"role": "user", "content": [
                    {"type": "text", "text": f"Analyze this drone surveillance frame in detail. Identify every person, vehicle, animal, and object visible.{detector_hint}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}", "detail": "high"}}
                ]}
            ],
            max_tokens=500,
            temperature=0.1,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Frame captured. Automated description unavailable: {e}"

@app.post("/api/analyze_video")
async def analyze_video(file: UploadFile = File(...)):
    """Upload a video file, extract frames, analyze each with AI, stream results."""
    # Save uploaded file to temp
    ensure_data_dir()
    tmp_path = os.path.join(os.path.dirname(__file__), "data", f"_upload_{int(time.time())}.mp4")
    try:
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)
    except Exception as e:
        return JSONResponse({"error": f"Upload failed: {e}"}, 500)

    async def event_gen():
        try:
            yield {"event": "status", "data": json.dumps({"message": "Extracting frames from video..."})}

            loop = asyncio.get_event_loop()
            frames, duration = await loop.run_in_executor(None, _extract_frames, tmp_path)

            yield {"event": "status", "data": json.dumps({
                "message": f"Extracted {len(frames)} frames from {duration}s video. Starting AI analysis...",
                "total_frames": len(frames), "duration": duration
            })}

            locations = ["Main Gate", "Perimeter Fence North", "Parking Lot A", "Warehouse Entrance", "Loading Dock"]
            telemetry_sim = TelemetrySimulator()

            for i, frame_data in enumerate(frames):
                yield {"event": "status", "data": json.dumps({"message": f"Analyzing frame {i+1}/{len(frames)} — Running Grounding DINO detection..."})}

                # Step 1: Run Grounding DINO object detection on the raw frame
                raw_frame = frame_data.get("raw_frame")
                gdino_objects = []
                gdino_detections = []
                if raw_frame is not None:
                    gdino_objects, gdino_detections = await loop.run_in_executor(
                        None, _detect_objects_gdino, raw_frame
                    )

                yield {"event": "status", "data": json.dumps({"message": f"Analyzing frame {i+1}/{len(frames)} — Running vision AI..."})}

                # Step 2: Get AI description with Grounding DINO hints for cross-referencing
                description = await loop.run_in_executor(
                    None, _describe_frame_with_vision, frame_data["base64"], gdino_objects
                )

                # Build telemetry
                telemetry = {
                    "time": frame_data["timestamp"],
                    "location": locations[i % len(locations)],
                    "drone_id": "UNIT-07",
                    "altitude_m": 120,
                    "property": "SecureTech Industrial Complex",
                }

                # Step 3: Run through existing analysis pipeline
                analysis = await loop.run_in_executor(None, analyze_frame, description, telemetry)

                # Step 4: Merge objects — combine Grounding DINO detections with VLM-identified objects
                vlm_objects = analysis.get("objects", [])
                merged_objects = list(vlm_objects)  # Start with VLM objects
                vlm_lower = {o.lower() for o in vlm_objects}
                for gobj in gdino_objects:
                    if gobj.lower() not in vlm_lower:
                        merged_objects.append(gobj)

                # Add detection counts from Grounding DINO for more accuracy
                det_counts = {}
                for det in gdino_detections:
                    label = det.get("label", "unknown")
                    det_counts[label] = det_counts.get(label, 0) + 1

                entry = {
                    "frame_id": i + 1,
                    "time": frame_data["timestamp"],
                    "location": telemetry["location"],
                    "objects": merged_objects,
                    "detections": [{"label": d["label"], "confidence": d["confidence"]} for d in gdino_detections],
                    "detection_counts": det_counts,
                    "event_type": analysis.get("event_type", "unknown"),
                    "risk_level": analysis.get("risk_level", "low").upper(),
                    "description": analysis.get("description", description[:200]),
                    "is_suspicious": analysis.get("is_suspicious", False),
                    "recommended_action": analysis.get("recommended_action", ""),
                    "frame_description": description,
                }

                yield {"event": "frame", "data": json.dumps(entry, default=str)}
                await asyncio.sleep(0.3)

            yield {"event": "complete", "data": json.dumps({
                "message": "Video analysis complete.",
                "total_frames": len(frames),
            })}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"message": str(e)})}
        finally:
            try: os.remove(tmp_path)
            except: pass

    return EventSourceResponse(event_gen())

@app.get("/api/stats")
async def get_stats():
    try:
        s = SQLiteStore()
        stats = s.get_session_stats()
        s.close()
        return stats
    except:
        return {"total_frames": 0, "suspicious_frames": 0, "total_alerts": 0, "alerts_by_severity": {}}

def _is_after_hours(timestamp: str) -> bool:
    try:
        h = int(timestamp.split(":")[0])
        return h >= 22 or h < 6
    except:
        return False

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
