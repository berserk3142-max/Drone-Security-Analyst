"""
Drone Security Analyst Agent — Streamlit Dashboard
Full-featured UI with Live Feed simulation, Video Analysis, Alerts, Query, and Summary tabs.
"""

import streamlit as st
import sys
import os
import json
import time
import cv2
import numpy as np
from PIL import Image
from datetime import datetime

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PROPERTY_NAME, DRONE_ID, ensure_data_dir
from simulators.frames import get_simulated_frames
from simulators.telemetry import TelemetrySimulator
from analysis.vlm_analyzer import analyze_frame
from agent.security_agent import SecurityAgent
from indexing.sqlite_store import SQLiteStore
from indexing.chroma_store import ChromaStore
from alerts.rules_engine import AlertManager

# --- Page Config ---
st.set_page_config(
    page_title="Drone Security Analyst Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main .block-container { padding-top: 1.5rem; max-width: 1400px; }

div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #0f3460;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}
div[data-testid="stMetric"] label { color: #8892b0 !important; font-size: 0.85rem !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #ccd6f6 !important; font-size: 1.8rem !important; font-weight: 700 !important; }

.alert-critical { background: linear-gradient(135deg, #3d0000, #5c1010); border-left: 4px solid #ff4444; padding: 12px 16px; border-radius: 8px; margin: 6px 0; color: #ffcccc; }
.alert-high { background: linear-gradient(135deg, #3d1c00, #5c3010); border-left: 4px solid #ff8c00; padding: 12px 16px; border-radius: 8px; margin: 6px 0; color: #ffe0b2; }
.alert-medium { background: linear-gradient(135deg, #3d3d00, #5c5c10); border-left: 4px solid #ffd700; padding: 12px 16px; border-radius: 8px; margin: 6px 0; color: #fff9c4; }
.alert-low { background: linear-gradient(135deg, #003d1c, #105c30); border-left: 4px solid #00c853; padding: 12px 16px; border-radius: 8px; margin: 6px 0; color: #c8e6c9; }

.frame-card { background: linear-gradient(135deg, #0d1b2a, #1b2838); border: 1px solid #233554; border-radius: 10px; padding: 14px 18px; margin: 8px 0; }
.frame-header { color: #64ffda; font-weight: 600; font-size: 0.95rem; }
.risk-badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; }
.risk-low { background: #00c85333; color: #00c853; border: 1px solid #00c853; }
.risk-medium { background: #ffd70033; color: #ffd700; border: 1px solid #ffd700; }
.risk-high { background: #ff8c0033; color: #ff8c00; border: 1px solid #ff8c00; }
.risk-critical { background: #ff444433; color: #ff4444; border: 1px solid #ff4444; }

.header-banner { background: linear-gradient(135deg, #0a192f 0%, #112240 50%, #1a365d 100%); border: 1px solid #233554; border-radius: 16px; padding: 24px 32px; margin-bottom: 20px; text-align: center; }
.header-title { color: #64ffda; font-size: 1.8rem; font-weight: 800; letter-spacing: 2px; margin: 0; }
.header-sub { color: #8892b0; font-size: 0.9rem; margin-top: 6px; }

.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] { background-color: #112240; border-radius: 8px 8px 0 0; color: #8892b0; font-weight: 600; padding: 10px 24px; }
.stTabs [aria-selected="true"] { background-color: #1a365d !important; color: #64ffda !important; border-bottom: 3px solid #64ffda; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown(f"""
<div class="header-banner">
    <p class="header-title">🛡️ DRONE SECURITY ANALYST AGENT</p>
    <p class="header-sub">Property: {PROPERTY_NAME} &nbsp;|&nbsp; Drone: {DRONE_ID} &nbsp;|&nbsp; Mode: Autonomous Patrol &nbsp;|&nbsp; AI: GPT-4o-mini</p>
</div>
""", unsafe_allow_html=True)

# --- Session State Init ---
if "sim_running" not in st.session_state:
    st.session_state.sim_running = False
if "sim_results" not in st.session_state:
    st.session_state.sim_results = []
if "sim_alerts" not in st.session_state:
    st.session_state.sim_alerts = []
if "frames_done" not in st.session_state:
    st.session_state.frames_done = 0
if "objects_count" not in st.session_state:
    st.session_state.objects_count = 0
if "summary_text" not in st.session_state:
    st.session_state.summary_text = ""

# --- Helpers ---
def get_risk_badge(risk):
    risk = risk.upper()
    cls = {"LOW": "risk-low", "MEDIUM": "risk-medium", "HIGH": "risk-high", "CRITICAL": "risk-critical"}.get(risk, "risk-low")
    return f'<span class="risk-badge {cls}">{risk}</span>'

def get_alert_class(severity):
    return {"CRITICAL": "alert-critical", "HIGH": "alert-high", "MEDIUM": "alert-medium", "LOW": "alert-low"}.get(severity, "alert-low")

# --- Sidebar ---
with st.sidebar:
    st.markdown("### ⚙️ Controls")
    st.markdown(f"**Time:** {datetime.now().strftime('%H:%M:%S')}")
    st.markdown(f"**Frames Processed:** {st.session_state.frames_done}")
    st.markdown(f"**Alerts Fired:** {len(st.session_state.sim_alerts)}")
    st.divider()
    st.markdown("### 📊 Risk Legend")
    st.markdown("🟢 **LOW** — Normal activity")
    st.markdown("🟡 **MEDIUM** — Monitor on next pass")
    st.markdown("🟠 **HIGH** — Dispatch security")
    st.markdown("🔴 **CRITICAL** — Immediate action")
    st.divider()
    st.markdown("### 🔧 Architecture")
    st.markdown("- **VLM**: GPT-4o-mini")
    st.markdown("- **Agent**: LangGraph ReAct")
    st.markdown("- **Storage**: SQLite + ChromaDB")
    st.markdown("- **Detection**: YOLOv8 + DeepSORT")

# --- Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎬 Live Feed", "📹 Video Analysis", "🚨 Alerts", "🔍 Query Frames", "📋 Daily Summary"])

# ===================== TAB 1: LIVE FEED =====================
with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Frames Processed", st.session_state.frames_done)
    c2.metric("Objects Detected", st.session_state.objects_count)
    c3.metric("Alerts Fired", len(st.session_state.sim_alerts))
    critical_count = sum(1 for a in st.session_state.sim_alerts if a.get("severity") == "CRITICAL")
    c4.metric("Critical Alerts", critical_count)

    st.markdown("---")

    col_btn, col_status = st.columns([1, 3])
    with col_btn:
        run_btn = st.button("▶️ Run Simulation", type="primary", use_container_width=True, key="run_sim")
    with col_status:
        status_area = st.empty()

    log_area = st.container()

    if run_btn and not st.session_state.sim_running:
        st.session_state.sim_running = True
        st.session_state.sim_results = []
        st.session_state.sim_alerts = []
        st.session_state.frames_done = 0
        st.session_state.objects_count = 0

        ensure_data_dir()
        sqlite_store = SQLiteStore()
        chroma_store = ChromaStore()
        alert_manager = AlertManager()
        telemetry_sim = TelemetrySimulator()
        sqlite_store.clear_all()
        try:
            chroma_store.clear_all()
        except Exception:
            pass

        status_area.info("⏳ Initializing AI Security Agent...")
        agent = SecurityAgent(sqlite_store, chroma_store, alert_manager)
        status_area.success("✅ Agent initialized. Processing frames...")

        frames = get_simulated_frames()
        progress = st.progress(0, text="Processing frames...")

        for i, frame in enumerate(frames):
            progress.progress((i + 1) / len(frames), text=f"Processing Frame {i+1}/{len(frames)} — {frame['location']}")

            telemetry = telemetry_sim.get_telemetry(frame["time"], frame["location"])
            analysis = analyze_frame(frame["description"], telemetry)
            agent_result = agent.process_frame(frame, analysis, telemetry)

            frame_alerts = [a for a in alert_manager.fired_alerts if a.get("frame_id") == frame["frame_id"]]
            st.session_state.sim_alerts.extend(frame_alerts)

            risk = analysis.get("risk_level", "low").upper()
            objects = analysis.get("objects", [])
            st.session_state.objects_count += len(objects)
            st.session_state.frames_done = i + 1

            result_entry = {
                "frame_id": frame["frame_id"],
                "time": frame["time"],
                "location": frame["location"],
                "objects": objects,
                "event_type": analysis.get("event_type", "unknown"),
                "risk_level": risk,
                "description": analysis.get("description", ""),
                "is_suspicious": analysis.get("is_suspicious", False),
                "alerts": frame_alerts,
                "agent_response": agent_result.get("agent_response", ""),
            }
            st.session_state.sim_results.append(result_entry)

            with log_area:
                risk_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}.get(risk, "⚪")
                obj_str = ", ".join(objects) if objects else "—"

                st.markdown(f"""
<div class="frame-card">
    <div class="frame-header">{risk_icon} [{frame['time']}] Frame {frame['frame_id']} — {frame['location']} {get_risk_badge(risk)}</div>
    <div style="color:#8892b0;margin-top:6px;font-size:0.85rem;">
        <b>Event:</b> {analysis.get('event_type','—')} &nbsp;|&nbsp; <b>Objects:</b> {obj_str}
    </div>
    <div style="color:#ccd6f6;margin-top:4px;font-size:0.85rem;">{analysis.get('description','')}</div>
</div>
                """, unsafe_allow_html=True)

                for alert in frame_alerts:
                    acls = get_alert_class(alert["severity"])
                    st.markdown(f'<div class="{acls}">🚨 <b>[{alert["severity"]}]</b> {alert["message"]}</div>', unsafe_allow_html=True)

            if i < len(frames) - 1:
                time.sleep(2)

        # Generate summary
        progress.progress(1.0, text="Generating AI summary...")
        try:
            st.session_state.summary_text = agent.get_summary()
        except Exception as e:
            st.session_state.summary_text = f"Summary generation error: {e}"

        sqlite_store.close()
        st.session_state.sim_running = False
        progress.empty()
        status_area.success(f"✅ Simulation complete! {len(frames)} frames processed, {len(st.session_state.sim_alerts)} alerts fired.")

    elif st.session_state.sim_results:
        for entry in st.session_state.sim_results:
            risk = entry["risk_level"]
            risk_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}.get(risk, "⚪")
            obj_str = ", ".join(entry["objects"]) if entry["objects"] else "—"

            with log_area:
                st.markdown(f"""
<div class="frame-card">
    <div class="frame-header">{risk_icon} [{entry['time']}] Frame {entry['frame_id']} — {entry['location']} {get_risk_badge(risk)}</div>
    <div style="color:#8892b0;margin-top:6px;font-size:0.85rem;"><b>Event:</b> {entry['event_type']} &nbsp;|&nbsp; <b>Objects:</b> {obj_str}</div>
    <div style="color:#ccd6f6;margin-top:4px;font-size:0.85rem;">{entry['description']}</div>
</div>
                """, unsafe_allow_html=True)
                for alert in entry.get("alerts", []):
                    acls = get_alert_class(alert["severity"])
                    st.markdown(f'<div class="{acls}">🚨 <b>[{alert["severity"]}]</b> {alert["message"]}</div>', unsafe_allow_html=True)

# ===================== TAB 2: VIDEO ANALYSIS =====================
with tab2:
    st.markdown("### 📹 Real-Time Video Object Detection")
    st.markdown("Upload drone surveillance footage for **YOLOv8 + DeepSORT** detection and tracking.")

    uploaded = st.file_uploader("Upload drone video", type=["mp4", "avi", "mov", "mkv"], key="video_upload")

    col_conf, col_skip = st.columns(2)
    with col_conf:
        confidence = st.slider("Detection Confidence", 0.2, 0.9, 0.4, 0.05)
    with col_skip:
        frame_skip = st.slider("Process every Nth frame", 1, 10, 3, help="Skip frames for faster processing")

    if uploaded:
        temp_path = os.path.join(os.path.dirname(__file__), "data", "temp_video.mp4")
        ensure_data_dir()
        with open(temp_path, "wb") as f:
            f.write(uploaded.read())

        from detector import VideoDetector, get_video_info
        info = get_video_info(temp_path)
        st.markdown(f"**Video:** {info.get('width','?')}x{info.get('height','?')} @ {info.get('fps','?')} FPS — {info.get('total_frames','?')} frames ({info.get('duration_sec','?')}s)")

        if st.button("🚀 Start Detection", type="primary", key="start_detection"):
            detector = VideoDetector(confidence=confidence)
            cap = cv2.VideoCapture(temp_path)

            col_vid, col_log = st.columns([2, 1])
            video_placeholder = col_vid.empty()
            log_placeholder = col_log.empty()
            metrics_placeholder = st.empty()
            prog = st.progress(0)

            detection_log = []
            total = info.get("total_frames", 1)
            frame_idx = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1
                if frame_idx % frame_skip != 0:
                    continue

                result = detector.process_frame(frame)
                annotated = result["annotated_frame"]

                rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                video_placeholder.image(rgb, channels="RGB", use_container_width=True)

                for track in result["active_tracks"]:
                    detection_log.insert(0, f"[Frame {frame_idx}] {track['label']} #{track['track_id']}")

                log_placeholder.text("\n".join(detection_log[:25]))

                prog.progress(min(frame_idx / total, 1.0), text=f"Frame {frame_idx}/{total}")

                with metrics_placeholder.container():
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("Frame", frame_idx)
                    mc2.metric("Active Objects", result["total_objects"])
                    mc3.metric("Unique Tracks", result["unique_track_count"])

            cap.release()
            prog.progress(1.0, text="✅ Video analysis complete!")
            st.success(f"Processed {frame_idx} frames. Detected {detector.total_detections} objects across {len(detector.unique_tracks)} unique tracks.")

            try:
                os.remove(temp_path)
            except Exception:
                pass
    else:
        st.info("👆 Upload a drone surveillance video (.mp4, .avi, .mov) to start real-time detection with bounding boxes and tracking IDs.")

# ===================== TAB 3: ALERTS =====================
with tab3:
    st.markdown("### 🚨 Alert Dashboard")

    if st.session_state.sim_alerts:
        sev_counts = {}
        for a in st.session_state.sim_alerts:
            s = a.get("severity", "LOW")
            sev_counts[s] = sev_counts.get(s, 0) + 1

        ac1, ac2, ac3, ac4 = st.columns(4)
        ac1.metric("🔴 Critical", sev_counts.get("CRITICAL", 0))
        ac2.metric("🟠 High", sev_counts.get("HIGH", 0))
        ac3.metric("🟡 Medium", sev_counts.get("MEDIUM", 0))
        ac4.metric("🟢 Low", sev_counts.get("LOW", 0))

        st.markdown("---")

        sev_filter = st.multiselect("Filter by Severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW"], default=["CRITICAL", "HIGH", "MEDIUM", "LOW"])

        for alert in st.session_state.sim_alerts:
            if alert.get("severity") not in sev_filter:
                continue
            acls = get_alert_class(alert["severity"])
            loc = alert.get("location", "—")
            t = alert.get("time", "—")
            st.markdown(f"""
<div class="{acls}">
    <b>🚨 [{alert['severity']}]</b> &nbsp; <span style="opacity:0.7">Frame {alert.get('frame_id','?')} | {t} | {loc}</span><br>
    {alert['message']}
</div>
            """, unsafe_allow_html=True)
    else:
        st.info("No alerts yet. Run the simulation in the **Live Feed** tab first.")

# ===================== TAB 4: QUERY FRAMES =====================
with tab4:
    st.markdown("### 🔍 Query Security Events")

    ensure_data_dir()
    try:
        query_store = SQLiteStore()
        has_data = len(query_store.get_all_frames()) > 0
    except Exception:
        has_data = False
        query_store = None

    if has_data and query_store:
        qcol1, qcol2 = st.columns([2, 1])
        with qcol1:
            search_query = st.text_input("🔎 Search by object, description, or keyword", placeholder="e.g. truck, person, suspicious")
        with qcol2:
            time_filter = st.selectbox("⏰ Time Filter", ["Any Time", "Business Hours (06:00-22:00)", "After Hours (22:00-06:00)", "Morning (06:00-12:00)", "Afternoon (12:00-18:00)", "Night (18:00-06:00)"])

        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            show_suspicious = st.checkbox("🔴 Suspicious only")
        with fcol2:
            location_filter = st.text_input("📍 Location filter", placeholder="e.g. Main Gate, Perimeter")
        with fcol3:
            risk_filter = st.multiselect("Risk Level", ["low", "medium", "high", "critical"], default=["low", "medium", "high", "critical"])

        if st.button("🔍 Search", type="primary", key="search_btn"):
            results = []

            if search_query:
                results = query_store.query_by_object(search_query)
            elif show_suspicious:
                results = query_store.query_suspicious_frames()
            elif location_filter:
                results = query_store.query_by_location(location_filter)
            else:
                results = query_store.get_all_frames()

            # Apply time filter
            if time_filter != "Any Time":
                time_ranges = {
                    "Business Hours (06:00-22:00)": ("06:00", "22:00"),
                    "After Hours (22:00-06:00)": ("22:00", "06:00"),
                    "Morning (06:00-12:00)": ("06:00", "12:00"),
                    "Afternoon (12:00-18:00)": ("12:00", "18:00"),
                    "Night (18:00-06:00)": ("18:00", "06:00"),
                }
                if time_filter in time_ranges:
                    s, e = time_ranges[time_filter]
                    time_results = query_store.query_by_time_range(s, e)
                    time_ids = {r["frame_id"] for r in time_results}
                    results = [r for r in results if r["frame_id"] in time_ids]

            # Apply risk filter
            results = [r for r in results if r.get("risk_level", "low") in risk_filter]

            if results:
                st.markdown(f"**Found {len(results)} results**")
                import pandas as pd
                df = pd.DataFrame([{
                    "Frame": r["frame_id"],
                    "Time": r["timestamp"],
                    "Location": r["location"],
                    "Event": r.get("event_type", "—"),
                    "Risk": r.get("risk_level", "—").upper(),
                    "Objects": r.get("objects_detected", "—"),
                    "Description": (r.get("analysis_summary") or r.get("raw_description", ""))[:80],
                } for r in results])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.warning("No results found for the given filters.")

        # Semantic search section
        st.markdown("---")
        st.markdown("#### 🧠 Semantic Search (ChromaDB)")
        sem_query = st.text_input("Natural language query", placeholder="e.g. suspicious nighttime activity near the fence")
        if st.button("🧠 Semantic Search", key="sem_search"):
            try:
                chroma = ChromaStore()
                sem_results = chroma.semantic_search(sem_query, top_k=10)
                if sem_results:
                    import pandas as pd
                    df = pd.DataFrame([{
                        "Frame": r.get("frame_id", "?"),
                        "Time": r.get("timestamp", "—"),
                        "Location": r.get("location", "—"),
                        "Relevance": f"{(1 - r.get('distance', 0)):.1%}",
                        "Description": r.get("raw_description", r.get("document", ""))[:80],
                    } for r in sem_results])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.warning("No semantic matches found.")
            except Exception as e:
                st.error(f"Semantic search error: {e}")

        query_store.close()
    else:
        st.info("No data available. Run the simulation in the **Live Feed** tab first to populate the database.")
        if query_store:
            query_store.close()

# ===================== TAB 5: DAILY SUMMARY =====================
with tab5:
    st.markdown("### 📋 AI Security Analyst Summary")

    if st.session_state.summary_text:
        st.markdown(f"""
<div style="background:linear-gradient(135deg,#0d1b2a,#1b2838);border:1px solid #233554;border-radius:12px;padding:24px 28px;color:#ccd6f6;line-height:1.7;font-size:0.92rem;">
{st.session_state.summary_text.replace(chr(10), '<br>')}
</div>
        """, unsafe_allow_html=True)
    elif st.session_state.frames_done > 0:
        if st.button("📋 Generate Summary", type="primary"):
            with st.spinner("Generating AI summary..."):
                try:
                    sqlite_store = SQLiteStore()
                    chroma_store = ChromaStore()
                    alert_manager = AlertManager()
                    agent = SecurityAgent(sqlite_store, chroma_store, alert_manager)
                    st.session_state.summary_text = agent.get_summary()
                    sqlite_store.close()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.info("Run the simulation first to generate an AI security summary.")

    # Session stats from DB
    st.markdown("---")
    st.markdown("#### 📊 Database Statistics")
    try:
        s = SQLiteStore()
        stats = s.get_session_stats()
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Total Frames in DB", stats["total_frames"])
        sc2.metric("Suspicious Events", stats["suspicious_frames"])
        sc3.metric("Total Alerts in DB", stats["total_alerts"])

        if stats["alerts_by_severity"]:
            import pandas as pd
            sev_df = pd.DataFrame([{"Severity": k, "Count": v} for k, v in sorted(stats["alerts_by_severity"].items())])
            st.bar_chart(sev_df.set_index("Severity"))
        s.close()
    except Exception:
        st.caption("No database stats available yet.")
