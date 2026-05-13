"""
Tests for the LangChain agent integration.
Note: These tests mock the LLM to avoid API calls during testing.
"""

import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indexing.sqlite_store import SQLiteStore
from indexing.chroma_store import ChromaStore
from alerts.rules_engine import AlertManager
from agent.tools import init_tools, log_event, check_alert_rules, query_past_events, generate_summary
import json


class TestAgentTools:
    """Tests for the agent's custom tools (without LLM calls)."""

    def setup_method(self):
        self.test_dir = tempfile.mkdtemp()
        self.sqlite = SQLiteStore(db_path=os.path.join(self.test_dir, "test.db"))
        self.chroma = ChromaStore(db_path=os.path.join(self.test_dir, "chroma"), collection_name="test")
        self.alerts = AlertManager()
        init_tools(self.sqlite, self.chroma, self.alerts)

    def teardown_method(self):
        self.sqlite.close()
        try:
            self.chroma.clear_all()
        except Exception:
            pass

    def test_log_event_tool(self):
        """Test the log_event tool writes to both stores."""
        event = {
            "frame_id": 1, "timestamp": "06:15", "location": "Main Gate",
            "objects": ["White Toyota Camry"], "event_type": "vehicle_entry",
            "risk_level": "low", "is_suspicious": False,
            "description": "Employee arrival", "raw_description": "Camry at gate",
        }
        result = log_event.invoke(json.dumps(event))
        assert "Event logged" in result
        assert self.sqlite.get_all_frames()[0]["frame_id"] == 1

    def test_check_alert_rules_tool(self):
        """Test the check_alert_rules tool detects threats."""
        analysis = {
            "frame_id": 25, "time": "22:15", "location": "Perimeter Fence North",
            "objects": ["Person"], "event_type": "perimeter_breach",
            "risk_level": "critical", "is_suspicious": True,
            "description": "Person climbing fence", "raw_description": "Person climbing fence",
        }
        result = check_alert_rules.invoke(json.dumps(analysis))
        assert "ALERTS TRIGGERED" in result

    def test_query_past_events_tool(self):
        """Test querying after logging events."""
        event = {
            "frame_id": 8, "timestamp": "09:30", "location": "Parking Lot B",
            "objects": ["Blue Ford F150"], "event_type": "vehicle_entry",
            "risk_level": "medium", "is_suspicious": False,
            "description": "Truck entering lot", "raw_description": "F150 truck",
        }
        log_event.invoke(json.dumps(event))
        result = query_past_events.invoke("Ford F150")
        assert "Frame 8" in result

    def test_generate_summary_tool(self):
        """Test summary generation."""
        event = {
            "frame_id": 1, "timestamp": "06:00", "location": "Gate",
            "objects": ["Car"], "event_type": "entry", "risk_level": "low",
            "is_suspicious": False, "description": "Normal", "raw_description": "Car",
        }
        log_event.invoke(json.dumps(event))
        result = generate_summary.invoke("")
        assert "Total Frames" in result

    def test_agent_context_via_vehicle_tracking(self):
        """Test that the same vehicle across 3 frames is tracked."""
        for i, (fid, time, loc) in enumerate([(8, "09:30", "Lot B"), (11, "11:30", "Lot A"), (17, "15:00", "Gate")]):
            event = {
                "frame_id": fid, "timestamp": time, "location": loc,
                "objects": ["Blue Ford F150"], "event_type": "vehicle_entry",
                "risk_level": "medium", "is_suspicious": i > 0,
                "description": f"F150 seen at {loc}", "raw_description": f"F150 at {loc}",
            }
            result = log_event.invoke(json.dumps(event))

        # After 3 sightings, vehicle re-entry should be noted
        count = self.sqlite.get_vehicle_count("Blue Ford F150")
        assert count == 3
