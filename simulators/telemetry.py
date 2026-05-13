"""
Telemetry Simulator — Generates fake drone telemetry data.

Produces structured telemetry readings for each frame timestamp,
simulating GPS position, altitude, battery, and drone status.
"""

import random
from config import DRONE_ID, LOCATIONS, PROPERTY_NAME


class TelemetrySimulator:
    """Simulates drone telemetry data for security patrol missions."""

    def __init__(self, drone_id: str = DRONE_ID):
        self.drone_id = drone_id
        self.battery = 100
        self.mission_start = True

    def get_telemetry(self, time_str: str, location: str) -> dict:
        """
        Generate telemetry data for a given time and location.

        Args:
            time_str: Time in HH:MM format (e.g., "06:00")
            location: Name of the patrol location

        Returns:
            dict with telemetry readings
        """
        # Battery drains ~2-4% per frame
        if self.mission_start:
            self.battery = random.randint(95, 100)
            self.mission_start = False
        else:
            self.battery = max(10, self.battery - random.randint(1, 3))

        # Altitude varies by location type
        altitude = self._get_altitude_for_location(location)

        # Wind speed simulation
        hour = int(time_str.split(":")[0])
        wind_speed = round(random.uniform(2.0, 15.0), 1)
        if hour >= 22 or hour < 6:
            wind_speed = round(random.uniform(1.0, 8.0), 1)  # calmer at night

        return {
            "drone_id": self.drone_id,
            "time": time_str,
            "location": location,
            "property": PROPERTY_NAME,
            "altitude_m": altitude,
            "battery_pct": self.battery,
            "wind_speed_kmh": wind_speed,
            "gps_signal": "strong" if random.random() > 0.1 else "moderate",
            "status": "patrolling",
        }

    def _get_altitude_for_location(self, location: str) -> int:
        """Determine drone altitude based on patrol location."""
        if "Gate" in location:
            return random.randint(10, 15)
        elif "Perimeter" in location:
            return random.randint(15, 25)
        elif "Parking" in location:
            return random.randint(12, 18)
        elif "Warehouse" in location or "Loading" in location:
            return random.randint(8, 14)
        elif "Server" in location:
            return random.randint(10, 15)
        else:
            return random.randint(12, 20)

    def reset(self):
        """Reset the simulator for a new mission."""
        self.battery = 100
        self.mission_start = True


def get_telemetry_for_frame(frame: dict, simulator: TelemetrySimulator = None) -> dict:
    """
    Convenience function to generate telemetry for a given frame.

    Args:
        frame: Frame dict with 'time' and 'location' keys
        simulator: Optional TelemetrySimulator instance

    Returns:
        Telemetry dict
    """
    if simulator is None:
        simulator = TelemetrySimulator()
    return simulator.get_telemetry(frame["time"], frame["location"])
