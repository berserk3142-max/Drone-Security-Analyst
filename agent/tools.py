"""
Agent Tools — Custom LangChain tools for the security analyst agent.

Provides four tools:
1. log_event — Write events to SQLite + ChromaDB
2. check_alert_rules — Evaluate alert conditions
3. query_past_events — Search historical frames
4. generate_summary — Produce session summary
"""

import json
from langchain.tools import tool
from indexing.sqlite_store import SQLiteStore
from indexing.chroma_store import ChromaStore
from alerts.rules_engine import AlertManager

# Global instances (initialized when agent is created)
_sqlite_store: SQLiteStore = None
_chroma_store: ChromaStore = None
_alert_manager: AlertManager = None


def init_tools(sqlite_store: SQLiteStore, chroma_store: ChromaStore,
               alert_manager: AlertManager):
    """Initialize the tool dependencies."""
    global _sqlite_store, _chroma_store, _alert_manager
    _sqlite_store = sqlite_store
    _chroma_store = chroma_store
    _alert_manager = alert_manager


@tool
def log_event(event_json: str) -> str:
    """Log a security event to the database. Input must be a JSON string with keys:
    frame_id (int), timestamp (str), location (str), objects (list of strings),
    event_type (str), risk_level (str), is_suspicious (bool), description (str),
    raw_description (str, optional).
    Returns a confirmation message."""
    try:
        event = json.loads(event_json)

        frame_id = event.get("frame_id", 0)
        timestamp = event.get("timestamp", "")
        location = event.get("location", "")
        objects = event.get("objects", [])
        event_type = event.get("event_type", "normal_operations")
        risk_level = event.get("risk_level", "low")
        is_suspicious = event.get("is_suspicious", False)
        description = event.get("description", "")
        raw_description = event.get("raw_description", "")

        # Log to SQLite
        _sqlite_store.insert_frame(
            frame_id=frame_id,
            timestamp=timestamp,
            location=location,
            objects_detected=objects,
            event_type=event_type,
            risk_level=risk_level,
            is_suspicious=is_suspicious,
            raw_description=raw_description,
            analysis_summary=description,
        )

        # Log to ChromaDB for semantic search
        _chroma_store.add_frame(
            frame_id=frame_id,
            timestamp=timestamp,
            location=location,
            description=f"{raw_description} {description}",
            event_type=event_type,
            risk_level=risk_level,
            objects_detected=", ".join(objects) if isinstance(objects, list) else str(objects),
        )

        # Track vehicles
        for obj in objects:
            obj_lower = obj.lower()
            if any(v in obj_lower for v in ["car", "truck", "vehicle", "van", "sedan", "suv",
                                             "camry", "civic", "bmw", "ford", "chevrolet",
                                             "silverado", "f150"]):
                count = _sqlite_store.log_vehicle(obj, frame_id, timestamp, location)
                if count > 1:
                    return (f"Event logged: Frame {frame_id} at {timestamp} ({location}). "
                            f"[!] VEHICLE RE-ENTRY: {obj} seen {count} times today.")

        return f"Event logged: Frame {frame_id} at {timestamp} ({location}). {event_type} - {risk_level} risk."

    except json.JSONDecodeError:
        return f"Error: Invalid JSON input. Please provide a valid JSON string."
    except Exception as e:
        return f"Error logging event: {str(e)}"


@tool
def check_alert_rules(analysis_json: str) -> str:
    """Check if a frame analysis triggers any alert rules. Input must be a JSON string
    with keys: frame_id (int), time (str), location (str), objects (list), event_type (str),
    risk_level (str), is_suspicious (bool), description (str), raw_description (str).
    Returns triggered alerts or 'No alerts triggered'."""
    try:
        analysis = json.loads(analysis_json)

        # Get vehicle context
        context = {}
        for obj in analysis.get("objects", []):
            obj_lower = obj.lower()
            if any(v in obj_lower for v in ["car", "truck", "vehicle", "van", "sedan", "suv",
                                             "camry", "civic", "bmw", "ford", "chevrolet"]):
                count = _sqlite_store.get_vehicle_count(obj)
                if count > 0:
                    context["vehicle_count"] = count
                    context["vehicle_name"] = obj

        # Evaluate rules
        triggered = _alert_manager.evaluate_rules(analysis, context)

        if triggered:
            # Log alerts to SQLite
            for alert in triggered:
                _sqlite_store.insert_alert(
                    frame_id=analysis.get("frame_id", 0),
                    timestamp=analysis.get("time", ""),
                    rule_name=alert["rule_name"],
                    severity=alert["severity"],
                    message=alert["message"],
                    location=alert.get("location", ""),
                )

            alert_msgs = [f"[{a['severity']}] {a['message']}" for a in triggered]
            return "ALERTS TRIGGERED:\n" + "\n".join(alert_msgs)
        else:
            return "No alerts triggered. All clear."

    except json.JSONDecodeError:
        return "Error: Invalid JSON input."
    except Exception as e:
        return f"Error checking alerts: {str(e)}"


@tool
def query_past_events(query: str) -> str:
    """Search past events in the database. Input should be a natural language query
    like 'truck', 'suspicious activity', 'perimeter fence', or a specific object type.
    Uses both keyword (SQLite) and semantic (ChromaDB) search.
    Returns matching events."""
    try:
        results = []

        # SQLite keyword search
        sqlite_results = _sqlite_store.query_by_object(query)
        if sqlite_results:
            results.append(f"=== SQLite Results ({len(sqlite_results)} matches) ===")
            for r in sqlite_results[:5]:
                results.append(
                    f"  Frame {r['frame_id']} [{r['timestamp']}] at {r['location']}: "
                    f"{r.get('analysis_summary', r.get('raw_description', 'N/A'))[:100]}"
                )

        # ChromaDB semantic search
        chroma_results = _chroma_store.semantic_search(query, top_k=5)
        if chroma_results:
            results.append(f"\n=== Semantic Search Results ({len(chroma_results)} matches) ===")
            for r in chroma_results[:5]:
                results.append(
                    f"  Frame {r['frame_id']} [{r.get('timestamp', 'N/A')}] at "
                    f"{r.get('location', 'N/A')}: similarity={1 - r.get('distance', 0):.2f}"
                )

        if results:
            return "\n".join(results)
        else:
            return f"No events found matching '{query}'."

    except Exception as e:
        return f"Error querying events: {str(e)}"


@tool
def generate_summary() -> str:
    """Generate a summary report of all events in the current monitoring session.
    No input required — pass an empty string or 'generate'.
    Returns a formatted session summary."""
    try:
        stats = _sqlite_store.get_session_stats()
        alerts = _sqlite_store.get_all_alerts()
        all_frames = _sqlite_store.get_all_frames()

        summary_lines = [
            "=======================================",
            "       SESSION SECURITY SUMMARY        ",
            "=======================================",
            f"",
            f"Total Frames Processed: {stats['total_frames']}",
            f"Suspicious Frames: {stats['suspicious_frames']}",
            f"Total Alerts: {stats['total_alerts']}",
        ]

        if stats["alerts_by_severity"]:
            summary_lines.append("\nAlerts by Severity:")
            for sev, count in sorted(stats["alerts_by_severity"].items()):
                summary_lines.append(f"  [{sev}]: {count}")

        if alerts:
            summary_lines.append("\nAlert Details:")
            for alert in alerts:
                summary_lines.append(
                    f"  [{alert['timestamp']}] [{alert['severity']}] {alert['message']}"
                )

        # Suspicious frame details
        suspicious = [f for f in all_frames if f.get("is_suspicious")]
        if suspicious:
            summary_lines.append(f"\nSuspicious Activity Log ({len(suspicious)} events):")
            for frame in suspicious:
                summary_lines.append(
                    f"  Frame {frame['frame_id']} [{frame['timestamp']}] at {frame['location']}: "
                    f"{frame.get('analysis_summary', 'N/A')[:80]}"
                )

        summary_lines.append("\n=======================================")
        return "\n".join(summary_lines)

    except Exception as e:
        return f"Error generating summary: {str(e)}"
