"""
Central configuration for the Drone Security Analyst Agent.
Loads environment variables and defines project-wide constants.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- API Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"

# --- Database Configuration ---
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "security_events.db")
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "chroma_db")
CHROMA_COLLECTION_NAME = "drone_frames"

# --- Drone Configuration ---
DRONE_ID = "DRN-01"
PROPERTY_NAME = "SecureTech Industrial Complex"

# --- Alert Severity Levels ---
SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"

# --- Locations ---
LOCATIONS = [
    "Main Gate",
    "Perimeter Fence North",
    "Perimeter Fence South",
    "Perimeter Fence East",
    "Perimeter Fence West",
    "Parking Lot A",
    "Parking Lot B",
    "Warehouse Entrance",
    "Loading Dock",
    "Admin Building",
    "Server Room Exterior",
    "Emergency Exit Rear",
]

# --- Known Vehicles (for alert rules) ---
KNOWN_VEHICLES = [
    "White Toyota Camry",
    "Silver Honda Civic",
    "Black BMW X5",
    "Blue Ford F150",
    "Red Chevrolet Silverado",
    "FedEx Delivery Van",
    "UPS Delivery Truck",
]

# --- Time Classification ---
BUSINESS_HOURS_START = 6   # 06:00
BUSINESS_HOURS_END = 22    # 22:00

def ensure_data_dir():
    """Create the data directory if it doesn't exist."""
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir
