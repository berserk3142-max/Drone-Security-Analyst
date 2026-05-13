"""
Tests for the telemetry simulator.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulators.telemetry import TelemetrySimulator, get_telemetry_for_frame
from config import DRONE_ID


class TestTelemetrySimulator:
    """Tests for TelemetrySimulator."""

    def test_telemetry_structure(self):
        """Test that telemetry output has all required fields."""
        sim = TelemetrySimulator()
        telemetry = sim.get_telemetry("06:00", "Main Gate")

        assert "drone_id" in telemetry
        assert "time" in telemetry
        assert "location" in telemetry
        assert "altitude_m" in telemetry
        assert "battery_pct" in telemetry
        assert "wind_speed_kmh" in telemetry
        assert "gps_signal" in telemetry
        assert "status" in telemetry

    def test_drone_id(self):
        """Test that the drone ID matches configuration."""
        sim = TelemetrySimulator()
        telemetry = sim.get_telemetry("06:00", "Main Gate")
        assert telemetry["drone_id"] == DRONE_ID

    def test_battery_drain(self):
        """Test that battery decreases over time."""
        sim = TelemetrySimulator()
        t1 = sim.get_telemetry("06:00", "Main Gate")
        t2 = sim.get_telemetry("06:15", "Parking Lot A")
        t3 = sim.get_telemetry("06:30", "Warehouse Entrance")

        assert t1["battery_pct"] >= t2["battery_pct"]
        assert t2["battery_pct"] >= t3["battery_pct"]

    def test_altitude_varies_by_location(self):
        """Test that altitude varies based on location type."""
        sim = TelemetrySimulator()
        gate = sim.get_telemetry("06:00", "Main Gate")
        perimeter = sim.get_telemetry("06:15", "Perimeter Fence North")

        # Gate altitude: 10-15m, Perimeter: 15-25m
        assert 8 <= gate["altitude_m"] <= 20
        assert 10 <= perimeter["altitude_m"] <= 30

    def test_location_coverage(self):
        """Test telemetry works for all defined locations."""
        sim = TelemetrySimulator()
        locations = [
            "Main Gate", "Perimeter Fence North", "Parking Lot A",
            "Warehouse Entrance", "Loading Dock", "Server Room Exterior",
        ]
        for loc in locations:
            telemetry = sim.get_telemetry("12:00", loc)
            assert telemetry["location"] == loc

    def test_reset(self):
        """Test that reset restores battery."""
        sim = TelemetrySimulator()
        sim.get_telemetry("06:00", "Main Gate")
        sim.get_telemetry("06:15", "Main Gate")
        sim.get_telemetry("06:30", "Main Gate")

        sim.reset()
        fresh = sim.get_telemetry("07:00", "Main Gate")
        assert fresh["battery_pct"] >= 95

    def test_convenience_function(self):
        """Test the get_telemetry_for_frame convenience function."""
        frame = {"time": "09:00", "location": "Loading Dock"}
        telemetry = get_telemetry_for_frame(frame)

        assert telemetry["time"] == "09:00"
        assert telemetry["location"] == "Loading Dock"

    def test_wind_speed_range(self):
        """Test wind speed is within reasonable range."""
        sim = TelemetrySimulator()
        for _ in range(20):
            t = sim.get_telemetry("12:00", "Main Gate")
            assert 0 <= t["wind_speed_kmh"] <= 20

    def test_gps_signal_values(self):
        """Test GPS signal is one of expected values."""
        sim = TelemetrySimulator()
        for _ in range(20):
            t = sim.get_telemetry("12:00", "Main Gate")
            assert t["gps_signal"] in ("strong", "moderate")
