"""
Tests for the indexing system (SQLite + ChromaDB).
"""

import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from indexing.sqlite_store import SQLiteStore
from indexing.chroma_store import ChromaStore


class TestSQLiteStore:
    """Tests for SQLiteStore."""

    def setup_method(self):
        """Create a fresh test database."""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_events.db")
        self.store = SQLiteStore(db_path=self.db_path)

    def teardown_method(self):
        """Cleanup test database."""
        self.store.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_insert_and_retrieve_frame(self):
        """Test basic frame insertion and retrieval."""
        self.store.insert_frame(
            frame_id=1,
            timestamp="06:15",
            location="Main Gate",
            objects_detected=["White Toyota Camry"],
            event_type="vehicle_entry",
            risk_level="low",
            is_suspicious=False,
            raw_description="White Toyota Camry entering main gate",
        )

        frames = self.store.get_all_frames()
        assert len(frames) == 1
        assert frames[0]["frame_id"] == 1
        assert frames[0]["location"] == "Main Gate"

    def test_vehicle_logged_correctly(self):
        """After processing a truck frame, the DB should contain the truck entry."""
        self.store.insert_frame(
            frame_id=8,
            timestamp="09:30",
            location="Parking Lot B",
            objects_detected=["Blue Ford F150"],
            event_type="vehicle_entry",
            risk_level="medium",
            is_suspicious=False,
            raw_description="Blue Ford F150 pickup truck entering lot B",
        )

        results = self.store.query_by_object("Ford F150")
        assert len(results) >= 1
        assert results[0]["frame_id"] == 8

    def test_frame_query_by_object(self):
        """Insert 5 frames, query for 'truck', assert only truck frames returned."""
        test_frames = [
            (1, "06:00", "Main Gate", ["Security Guard"], "security_patrol", "low"),
            (2, "06:15", "Main Gate", ["White Toyota Camry"], "vehicle_entry", "low"),
            (3, "08:30", "Loading Dock", ["FedEx Delivery Truck"], "delivery", "low"),
            (4, "09:00", "Warehouse", ["Employees"], "employee_activity", "low"),
            (5, "13:00", "Loading Dock", ["UPS Delivery Truck"], "delivery", "low"),
        ]

        for fid, time, loc, objs, etype, risk in test_frames:
            self.store.insert_frame(fid, time, loc, objs, etype, risk, False, "desc")

        truck_results = self.store.query_by_object("Truck")
        assert len(truck_results) == 2  # FedEx and UPS trucks
        frame_ids = [r["frame_id"] for r in truck_results]
        assert 3 in frame_ids
        assert 5 in frame_ids

    def test_query_by_time_range(self):
        """Test time range queries."""
        self.store.insert_frame(1, "06:00", "Gate", ["Guard"], "patrol", "low", False, "")
        self.store.insert_frame(2, "12:00", "Gate", ["Car"], "entry", "low", False, "")
        self.store.insert_frame(3, "23:00", "Gate", ["SUV"], "entry", "high", True, "")

        # Query after 22:00
        results = self.store.query_by_time_range("22:00", "23:59")
        assert len(results) == 1
        assert results[0]["frame_id"] == 3

    def test_insert_and_retrieve_alert(self):
        """Test alert insertion and retrieval."""
        alert_id = self.store.insert_alert(
            frame_id=25,
            timestamp="22:15",
            rule_name="after_hours_person",
            severity="HIGH",
            message="Person detected after hours",
            location="Perimeter Fence North",
        )

        alerts = self.store.get_all_alerts()
        assert len(alerts) == 1
        assert alerts[0]["alert_id"] == alert_id
        assert alerts[0]["severity"] == "HIGH"

    def test_vehicle_count(self):
        """Test vehicle counting across multiple sightings."""
        count1 = self.store.log_vehicle("Blue Ford F150", 8, "09:30", "Parking Lot B")
        assert count1 == 1

        count2 = self.store.log_vehicle("Blue Ford F150", 11, "11:30", "Parking Lot A")
        assert count2 == 2

        total = self.store.get_vehicle_count("Blue Ford F150")
        assert total == 2

    def test_suspicious_frames(self):
        """Test querying suspicious frames."""
        self.store.insert_frame(1, "06:00", "Gate", ["Car"], "entry", "low", False, "")
        self.store.insert_frame(2, "22:15", "Fence", ["Person"], "breach", "critical", True, "")
        self.store.insert_frame(3, "23:00", "Gate", ["SUV"], "entry", "high", True, "")

        suspicious = self.store.query_suspicious_frames()
        assert len(suspicious) == 2
        frame_ids = [r["frame_id"] for r in suspicious]
        assert 2 in frame_ids
        assert 3 in frame_ids

    def test_session_stats(self):
        """Test session statistics computation."""
        self.store.insert_frame(1, "06:00", "Gate", ["Car"], "entry", "low", False, "")
        self.store.insert_frame(2, "22:15", "Fence", ["Person"], "breach", "critical", True, "")
        self.store.insert_alert(2, "22:15", "perimeter_breach", "CRITICAL", "Breach!", "Fence")

        stats = self.store.get_session_stats()
        assert stats["total_frames"] == 2
        assert stats["suspicious_frames"] == 1
        assert stats["total_alerts"] == 1
        assert stats["alerts_by_severity"]["CRITICAL"] == 1

    def test_clear_all(self):
        """Test clearing all data."""
        self.store.insert_frame(1, "06:00", "Gate", ["Car"], "entry", "low", False, "")
        self.store.insert_alert(1, "06:00", "test", "LOW", "test alert")
        self.store.clear_all()

        assert len(self.store.get_all_frames()) == 0
        assert len(self.store.get_all_alerts()) == 0


class TestChromaStore:
    """Tests for ChromaStore."""

    def setup_method(self):
        """Create a fresh test ChromaDB."""
        self.test_dir = tempfile.mkdtemp()
        self.chroma_path = os.path.join(self.test_dir, "test_chroma")
        self.store = ChromaStore(db_path=self.chroma_path, collection_name="test_frames", use_cloud=False)

    def teardown_method(self):
        """Cleanup."""
        try:
            self.store.clear_all()
        except Exception:
            pass

    def test_add_and_count_frames(self):
        """Test adding frames and counting them."""
        self.store.add_frame(1, "06:00", "Main Gate", "Car entering gate", "vehicle_entry", "low")
        self.store.add_frame(2, "22:15", "Fence", "Person near fence at night", "suspicious_activity", "high")

        assert self.store.get_frame_count() == 2

    def test_semantic_search(self):
        """Test semantic search returns relevant results."""
        self.store.add_frame(1, "06:00", "Main Gate", "White Toyota Camry employee arriving for work", "vehicle_entry", "low")
        self.store.add_frame(2, "22:15", "Perimeter Fence", "Person in dark clothing near fence at night", "suspicious_activity", "high")
        self.store.add_frame(3, "08:30", "Loading Dock", "FedEx delivery truck unloading packages", "delivery", "low")

        # Search for nighttime suspicious activity
        results = self.store.semantic_search("suspicious person at night near fence", top_k=3)
        assert len(results) > 0

        # The fence/night frame should be most relevant
        assert results[0]["frame_id"] == 2

    def test_search_by_vehicle(self):
        """Test searching for vehicles returns vehicle frames."""
        self.store.add_frame(1, "06:00", "Gate", "Toyota Camry entering the property", "vehicle_entry", "low")
        self.store.add_frame(2, "09:00", "Warehouse", "Workers entering warehouse", "employee_activity", "low")
        self.store.add_frame(3, "13:00", "Dock", "UPS delivery truck at dock", "delivery", "low")

        results = self.store.semantic_search("delivery truck", top_k=3)
        assert len(results) > 0
        # The UPS truck should be most relevant
        assert results[0]["frame_id"] == 3

    def test_clear_all(self):
        """Test clearing the collection."""
        self.store.add_frame(1, "06:00", "Gate", "Test frame", "test", "low")
        assert self.store.get_frame_count() == 1

        self.store.clear_all()
        assert self.store.get_frame_count() == 0
