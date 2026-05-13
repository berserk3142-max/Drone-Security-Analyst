"""
Tests for the alert rules engine.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alerts.rules_engine import AlertManager, ALERT_RULES


class TestAlertManager:
    """Tests for the AlertManager and alert rules."""

    def setup_method(self):
        """Reset alert manager before each test."""
        self.manager = AlertManager()

    def test_alert_fires_at_midnight(self):
        """A person detected after midnight should trigger an after-hours alert."""
        analysis = {
            "frame_id": 99,
            "time": "00:15",
            "location": "Loading Dock",
            "objects": ["Person"],
            "event_type": "person_detected",
            "risk_level": "high",
            "is_suspicious": True,
            "description": "Person in dark clothing at loading dock",
            "raw_description": "Person in dark clothing near loading dock at night",
        }

        alerts = self.manager.evaluate_rules(analysis)

        # Should fire the after_hours_person rule
        rule_names = [a["rule_name"] for a in alerts]
        assert "after_hours_person" in rule_names

    def test_perimeter_breach_alert(self):
        """Person attempting to climb a perimeter fence should trigger CRITICAL alert."""
        analysis = {
            "frame_id": 26,
            "time": "22:30",
            "location": "Perimeter Fence North",
            "objects": ["Person"],
            "event_type": "perimeter_breach",
            "risk_level": "critical",
            "is_suspicious": True,
            "description": "Person attempting to climb the fence",
            "raw_description": "Person climbing the north perimeter fence",
        }

        alerts = self.manager.evaluate_rules(analysis)

        # Should fire perimeter_breach
        rule_names = [a["rule_name"] for a in alerts]
        assert "perimeter_breach" in rule_names

        # Should be CRITICAL severity
        breach_alert = next(a for a in alerts if a["rule_name"] == "perimeter_breach")
        assert breach_alert["severity"] == "CRITICAL"

    def test_no_false_alert_daytime_employee(self):
        """Normal employee activity during business hours should not trigger after-hours alerts."""
        analysis = {
            "frame_id": 5,
            "time": "09:00",
            "location": "Main Gate",
            "objects": ["Silver Honda Civic"],
            "event_type": "vehicle_entry",
            "risk_level": "low",
            "is_suspicious": False,
            "description": "Employee vehicle entering during business hours",
            "raw_description": "Silver Honda Civic arriving at main gate",
        }

        alerts = self.manager.evaluate_rules(analysis)

        # Should NOT fire after_hours or perimeter alerts
        rule_names = [a["rule_name"] for a in alerts]
        assert "after_hours_person" not in rule_names
        assert "perimeter_breach" not in rule_names

    def test_unknown_vehicle_night(self):
        """Unknown vehicle at night should trigger high-severity alert."""
        analysis = {
            "frame_id": 27,
            "time": "23:00",
            "location": "Main Gate",
            "objects": ["Dark SUV"],
            "event_type": "vehicle_entry",
            "risk_level": "high",
            "is_suspicious": True,
            "description": "Unidentified dark SUV at gate after hours",
            "raw_description": "Dark SUV with tinted windows idling near main gate at night",
        }

        alerts = self.manager.evaluate_rules(analysis)
        rule_names = [a["rule_name"] for a in alerts]
        assert "unknown_vehicle_night" in rule_names

    def test_vehicle_reentry_alert(self):
        """Vehicle seen multiple times should trigger re-entry alert."""
        analysis = {
            "frame_id": 11,
            "time": "11:30",
            "location": "Parking Lot A",
            "objects": ["Blue Ford F150"],
            "event_type": "vehicle_entry",
            "risk_level": "medium",
            "is_suspicious": True,
            "description": "Same vehicle circling parking lot",
            "raw_description": "Blue Ford F150 circling lot",
        }

        context = {"vehicle_count": 3, "vehicle_name": "Blue Ford F150"}
        alerts = self.manager.evaluate_rules(analysis, context)
        rule_names = [a["rule_name"] for a in alerts]
        assert "vehicle_reentry" in rule_names

    def test_unauthorized_access(self):
        """Person with ski mask at server room should trigger CRITICAL alert."""
        analysis = {
            "frame_id": 28,
            "time": "23:30",
            "location": "Server Room Exterior",
            "objects": ["Person"],
            "event_type": "unauthorized_access",
            "risk_level": "critical",
            "is_suspicious": True,
            "description": "Person in ski mask attempting access",
            "raw_description": "Person in ski mask at server room door with device on keycard reader",
        }

        alerts = self.manager.evaluate_rules(analysis)
        rule_names = [a["rule_name"] for a in alerts]
        assert "unauthorized_access" in rule_names

    def test_door_anomaly(self):
        """Open door after hours should trigger alert."""
        analysis = {
            "frame_id": 20,
            "time": "17:30",
            "location": "Emergency Exit Rear",
            "objects": [],
            "event_type": "door_anomaly",
            "risk_level": "medium",
            "is_suspicious": False,
            "description": "Rear emergency exit door ajar",
            "raw_description": "Emergency exit door is ajar, partially open",
        }

        alerts = self.manager.evaluate_rules(analysis)
        rule_names = [a["rule_name"] for a in alerts]
        assert "door_anomaly" in rule_names

    def test_suspicious_behavior(self):
        """Person taking photos near perimeter should trigger suspicious behavior alert."""
        analysis = {
            "frame_id": 15,
            "time": "14:30",
            "location": "Perimeter Fence East",
            "objects": ["Person"],
            "event_type": "suspicious_activity",
            "risk_level": "high",
            "is_suspicious": True,
            "description": "Person photographing the warehouse from the perimeter",
            "raw_description": "Person in dark hoodie taking photos of warehouse through fence",
        }

        alerts = self.manager.evaluate_rules(analysis)
        rule_names = [a["rule_name"] for a in alerts]
        assert "suspicious_behavior" in rule_names

    def test_alert_summary(self):
        """Test that alert summary correctly counts alerts."""
        # Fire two different alerts
        analysis1 = {
            "frame_id": 25, "time": "22:15", "location": "Perimeter Fence North",
            "objects": ["Person"], "event_type": "perimeter_breach", "risk_level": "critical",
            "is_suspicious": True, "description": "Breach attempt",
            "raw_description": "Person climbing fence",
        }
        analysis2 = {
            "frame_id": 27, "time": "23:00", "location": "Main Gate",
            "objects": ["Dark SUV"], "event_type": "vehicle_entry", "risk_level": "high",
            "is_suspicious": True, "description": "Unknown vehicle at night",
            "raw_description": "Dark SUV idling at gate",
        }

        self.manager.evaluate_rules(analysis1)
        self.manager.evaluate_rules(analysis2)

        summary = self.manager.get_alert_summary()
        assert summary["total"] > 0
        assert len(summary["alerts"]) > 0

    def test_alert_rules_defined(self):
        """Verify all expected alert rules are defined."""
        rule_names = [r["name"] for r in ALERT_RULES]
        expected = [
            "after_hours_person", "perimeter_breach", "unauthorized_access",
            "unknown_vehicle_night", "vehicle_reentry", "suspicious_behavior",
            "door_anomaly", "unauthorized_parking",
        ]
        for name in expected:
            assert name in rule_names, f"Missing rule: {name}"
