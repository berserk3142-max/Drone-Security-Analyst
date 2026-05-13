"""
SQLite Store — Structured storage for drone security events and alerts.

Provides relational database storage with fast querying by object type,
time range, location, and event type.
"""

import sqlite3
import json
import os
from config import SQLITE_DB_PATH, ensure_data_dir


class SQLiteStore:
    """SQLite-based structured storage for security events and alerts."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or SQLITE_DB_PATH
        ensure_data_dir()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """Create the frames and alerts tables if they don't exist."""
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS frames (
                frame_id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                location TEXT NOT NULL,
                objects_detected TEXT,
                event_type TEXT,
                risk_level TEXT,
                is_suspicious INTEGER DEFAULT 0,
                raw_description TEXT,
                analysis_summary TEXT,
                agent_response TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                frame_id INTEGER,
                timestamp TEXT NOT NULL,
                rule_name TEXT,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                location TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (frame_id) REFERENCES frames(frame_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehicle_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_description TEXT NOT NULL,
                frame_id INTEGER,
                timestamp TEXT NOT NULL,
                location TEXT,
                entry_count INTEGER DEFAULT 1,
                FOREIGN KEY (frame_id) REFERENCES frames(frame_id)
            )
        """)

        self.conn.commit()

    def insert_frame(self, frame_id: int, timestamp: str, location: str,
                     objects_detected: list, event_type: str, risk_level: str,
                     is_suspicious: bool, raw_description: str,
                     analysis_summary: str = "", agent_response: str = "") -> bool:
        """
        Insert a processed frame into the database.

        Returns:
            True if inserted, False if frame_id already exists
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO frames
                (frame_id, timestamp, location, objects_detected, event_type,
                 risk_level, is_suspicious, raw_description, analysis_summary, agent_response)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                frame_id, timestamp, location,
                json.dumps(objects_detected) if isinstance(objects_detected, list) else objects_detected,
                event_type, risk_level,
                1 if is_suspicious else 0,
                raw_description, analysis_summary, agent_response
            ))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"SQLite insert error: {e}")
            return False

    def insert_alert(self, frame_id: int, timestamp: str, rule_name: str,
                     severity: str, message: str, location: str = "") -> int:
        """
        Insert an alert and return its ID.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO alerts (frame_id, timestamp, rule_name, severity, message, location)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (frame_id, timestamp, rule_name, severity, message, location))
        self.conn.commit()
        return cursor.lastrowid

    def log_vehicle(self, vehicle_description: str, frame_id: int,
                    timestamp: str, location: str) -> int:
        """Log a vehicle sighting and return the entry count for this vehicle."""
        cursor = self.conn.cursor()

        # Count previous sightings
        cursor.execute(
            "SELECT COUNT(*) FROM vehicle_log WHERE vehicle_description = ?",
            (vehicle_description,)
        )
        count = cursor.fetchone()[0] + 1

        cursor.execute("""
            INSERT INTO vehicle_log (vehicle_description, frame_id, timestamp, location, entry_count)
            VALUES (?, ?, ?, ?, ?)
        """, (vehicle_description, frame_id, timestamp, location, count))
        self.conn.commit()
        return count

    def query_by_object(self, object_type: str) -> list[dict]:
        """Search frames where objects_detected contains the given object type."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM frames WHERE objects_detected LIKE ?",
            (f"%{object_type}%",)
        )
        return [dict(row) for row in cursor.fetchall()]

    def query_by_time_range(self, start_time: str, end_time: str) -> list[dict]:
        """Get frames within a time range (HH:MM format)."""
        cursor = self.conn.cursor()

        start_minutes = self._time_to_minutes(start_time)
        end_minutes = self._time_to_minutes(end_time)

        # Get all frames and filter in Python for overnight ranges
        cursor.execute("SELECT * FROM frames")
        all_frames = [dict(row) for row in cursor.fetchall()]

        if end_minutes < start_minutes:
            # Overnight range (e.g., 22:00 to 02:00)
            return [f for f in all_frames
                    if self._time_to_minutes(f["timestamp"]) >= start_minutes
                    or self._time_to_minutes(f["timestamp"]) <= end_minutes]
        else:
            return [f for f in all_frames
                    if start_minutes <= self._time_to_minutes(f["timestamp"]) <= end_minutes]

    def query_by_location(self, location: str) -> list[dict]:
        """Search frames by location."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM frames WHERE location LIKE ?",
            (f"%{location}%",)
        )
        return [dict(row) for row in cursor.fetchall()]

    def query_suspicious_frames(self) -> list[dict]:
        """Get all frames flagged as suspicious."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM frames WHERE is_suspicious = 1")
        return [dict(row) for row in cursor.fetchall()]

    def get_all_alerts(self) -> list[dict]:
        """Get all triggered alerts."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM alerts ORDER BY created_at")
        return [dict(row) for row in cursor.fetchall()]

    def get_alerts_by_severity(self, severity: str) -> list[dict]:
        """Get alerts filtered by severity level."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM alerts WHERE severity = ?", (severity,))
        return [dict(row) for row in cursor.fetchall()]

    def get_vehicle_count(self, vehicle_description: str) -> int:
        """Get the number of times a vehicle has been seen."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM vehicle_log WHERE vehicle_description = ?",
            (vehicle_description,)
        )
        return cursor.fetchone()[0]

    def get_all_frames(self) -> list[dict]:
        """Get all stored frames."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM frames ORDER BY frame_id")
        return [dict(row) for row in cursor.fetchall()]

    def get_session_stats(self) -> dict:
        """Get summary statistics for the current session."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM frames")
        total_frames = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM frames WHERE is_suspicious = 1")
        suspicious = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM alerts")
        total_alerts = cursor.fetchone()[0]

        cursor.execute("SELECT severity, COUNT(*) FROM alerts GROUP BY severity")
        alerts_by_severity = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total_frames": total_frames,
            "suspicious_frames": suspicious,
            "total_alerts": total_alerts,
            "alerts_by_severity": alerts_by_severity,
        }

    def clear_all(self):
        """Clear all data — used for testing and fresh sessions."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM alerts")
        cursor.execute("DELETE FROM vehicle_log")
        cursor.execute("DELETE FROM frames")
        self.conn.commit()

    def close(self):
        """Close the database connection."""
        self.conn.close()

    @staticmethod
    def _time_to_minutes(time_str: str) -> int:
        """Convert HH:MM to total minutes."""
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
