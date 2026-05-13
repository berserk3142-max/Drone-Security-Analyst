"""
Alert Rules Engine — Evaluates security conditions and triggers alerts.

Defines a set of configurable rules that are evaluated against each frame's
analysis results. Fires alerts when conditions are met.
"""

from config import (
    SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL,
    KNOWN_VEHICLES, BUSINESS_HOURS_START, BUSINESS_HOURS_END
)


# --- Alert Rule Definitions ---
ALERT_RULES = [
    {
        "name": "after_hours_person",
        "description": "Person detected outside business hours",
        "severity": SEVERITY_HIGH,
        "message": "[WARNING] Person detected after hours at {location} - {details}",
    },
    {
        "name": "perimeter_breach",
        "description": "Person near or attempting to breach perimeter fence",
        "severity": SEVERITY_CRITICAL,
        "message": "[CRITICAL] PERIMETER BREACH at {location} - {details}",
    },
    {
        "name": "unauthorized_access",
        "description": "Unauthorized access attempt to restricted area",
        "severity": SEVERITY_CRITICAL,
        "message": "[CRITICAL] UNAUTHORIZED ACCESS ATTEMPT at {location} - {details}",
    },
    {
        "name": "unknown_vehicle_night",
        "description": "Unrecognized vehicle detected after hours",
        "severity": SEVERITY_HIGH,
        "message": "[WARNING] Unknown vehicle at {location} after hours - {details}",
    },
    {
        "name": "vehicle_reentry",
        "description": "Same vehicle seen multiple times (possible surveillance)",
        "severity": SEVERITY_MEDIUM,
        "message": "[ALERT] Vehicle re-entry detected: {details} - seen {count} times at {location}",
    },
    {
        "name": "suspicious_behavior",
        "description": "Suspicious activity detected (loitering, photographing, circling)",
        "severity": SEVERITY_HIGH,
        "message": "[WARNING] Suspicious behavior at {location} - {details}",
    },
    {
        "name": "door_anomaly",
        "description": "Door open or ajar when it should be closed",
        "severity": SEVERITY_MEDIUM,
        "message": "[ALERT] Door anomaly at {location} - {details}",
    },
    {
        "name": "unauthorized_parking",
        "description": "Vehicle parked in unauthorized zone",
        "severity": SEVERITY_LOW,
        "message": "[INFO] Unauthorized parking at {location} - {details}",
    },
]


class AlertManager:
    """Manages alert evaluation and tracking to prevent duplicates."""

    def __init__(self):
        self.fired_alerts: list[dict] = []
        self._alert_history: set = set()  # (rule_name, location) to prevent duplicates

    def evaluate_rules(self, frame_analysis: dict, context: dict = None) -> list[dict]:
        """
        Evaluate all alert rules against a frame analysis result.

        Args:
            frame_analysis: Dict with keys: objects, event_type, risk_level,
                           location, is_suspicious, description
            context: Additional context (vehicle counts, time info, etc.)

        Returns:
            List of triggered alert dicts
        """
        triggered = []
        context = context or {}

        time_str = frame_analysis.get("time", "12:00")
        hour = int(time_str.split(":")[0])
        location = frame_analysis.get("location", "Unknown")
        objects = frame_analysis.get("objects", [])
        event_type = frame_analysis.get("event_type", "")
        risk_level = frame_analysis.get("risk_level", "low")
        is_suspicious = frame_analysis.get("is_suspicious", False)
        description = frame_analysis.get("description", "")
        raw_description = frame_analysis.get("raw_description", "")

        is_after_hours = hour >= BUSINESS_HOURS_END or hour < BUSINESS_HOURS_START

        # Combine descriptions for matching
        full_text = f"{description} {raw_description} {event_type}".lower()

        # --- Rule: After-hours person ---
        has_person = any("person" in obj.lower() or "individual" in obj.lower()
                        or "man" in obj.lower() or "woman" in obj.lower()
                        for obj in objects) or "person" in full_text
        if is_after_hours and has_person:
            alert = self._create_alert(
                "after_hours_person", location,
                details=f"Person detected at {time_str}",
                frame_analysis=frame_analysis
            )
            if alert:
                triggered.append(alert)

        # --- Rule: Perimeter breach ---
        is_perimeter = "perimeter" in location.lower() or "fence" in location.lower()
        has_breach_indicators = any(w in full_text for w in [
            "climb", "breach", "cut", "hole", "testing", "attempting",
            "break", "intrusion", "trespass"
        ])
        if is_perimeter and has_person and (has_breach_indicators or is_suspicious):
            alert = self._create_alert(
                "perimeter_breach", location,
                details=description or "Perimeter breach attempt detected",
                frame_analysis=frame_analysis
            )
            if alert:
                triggered.append(alert)

        # --- Rule: Unauthorized access ---
        is_restricted = any(area in location.lower() for area in [
            "server room", "warehouse", "loading dock"
        ])
        has_unauthorized = any(w in full_text for w in [
            "unauthorized", "no badge", "ski mask", "break in",
            "forced entry", "no identification", "mask"
        ])
        if is_restricted and has_unauthorized:
            alert = self._create_alert(
                "unauthorized_access", location,
                details=description or "Unauthorized access attempt",
                frame_analysis=frame_analysis
            )
            if alert:
                triggered.append(alert)

        # --- Rule: Unknown vehicle at night ---
        has_vehicle = any("vehicle" in obj.lower() or "car" in obj.lower()
                         or "truck" in obj.lower() or "suv" in obj.lower()
                         or "sedan" in obj.lower() or "van" in obj.lower()
                         for obj in objects)
        is_known = any(kv.lower() in full_text for kv in KNOWN_VEHICLES)
        if is_after_hours and has_vehicle and not is_known:
            alert = self._create_alert(
                "unknown_vehicle_night", location,
                details=f"Unidentified vehicle at {time_str}",
                frame_analysis=frame_analysis
            )
            if alert:
                triggered.append(alert)

        # --- Rule: Vehicle re-entry ---
        vehicle_count = context.get("vehicle_count", 0)
        vehicle_name = context.get("vehicle_name", "")
        if vehicle_count > 1:
            alert = self._create_alert(
                "vehicle_reentry", location,
                details=vehicle_name,
                count=vehicle_count,
                frame_analysis=frame_analysis
            )
            if alert:
                triggered.append(alert)

        # --- Rule: Suspicious behavior ---
        has_suspicious = any(w in full_text for w in [
            "suspicious", "loitering", "circling", "photographing",
            "photo", "surveill", "casing", "watching"
        ])
        if has_suspicious:
            alert = self._create_alert(
                "suspicious_behavior", location,
                details=description or "Suspicious activity observed",
                frame_analysis=frame_analysis
            )
            if alert:
                triggered.append(alert)

        # --- Rule: Door anomaly ---
        has_door_issue = any(w in full_text for w in [
            "door ajar", "door open", "door unlocked", "partially open"
        ])
        if has_door_issue:
            alert = self._create_alert(
                "door_anomaly", location,
                details="Door found open/ajar outside normal hours",
                frame_analysis=frame_analysis
            )
            if alert:
                triggered.append(alert)

        # --- Rule: Unauthorized parking ---
        has_parking_violation = "unauthorized" in full_text and ("park" in full_text or "zone" in full_text)
        if has_parking_violation:
            alert = self._create_alert(
                "unauthorized_parking", location,
                details=description or "Vehicle in unauthorized zone",
                frame_analysis=frame_analysis
            )
            if alert:
                triggered.append(alert)

        return triggered

    def _create_alert(self, rule_name: str, location: str,
                      details: str = "", count: int = 0,
                      frame_analysis: dict = None) -> dict | None:
        """Create an alert if it hasn't been fired before for this location."""
        # Find the rule definition
        rule = next((r for r in ALERT_RULES if r["name"] == rule_name), None)
        if not rule:
            return None

        # Format the message
        message = rule["message"].format(
            location=location,
            details=details,
            count=count,
        )

        alert = {
            "rule_name": rule_name,
            "severity": rule["severity"],
            "message": message,
            "location": location,
            "time": frame_analysis.get("time", "") if frame_analysis else "",
            "frame_id": frame_analysis.get("frame_id", 0) if frame_analysis else 0,
        }

        self.fired_alerts.append(alert)
        return alert

    def get_alert_summary(self) -> dict:
        """Get summary of all fired alerts."""
        summary = {
            "total": len(self.fired_alerts),
            "by_severity": {},
            "alerts": self.fired_alerts,
        }
        for alert in self.fired_alerts:
            sev = alert["severity"]
            summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1
        return summary

    def reset(self):
        """Reset all alerts — for new sessions."""
        self.fired_alerts.clear()
        self._alert_history.clear()
