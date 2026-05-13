"""
Video Frame Simulator — Generates 30 diverse simulated drone surveillance frames.

Each frame represents a single snapshot from a drone camera, described as text.
Covers day/night scenarios, vehicles, people, suspicious/normal activity, and edge cases.
"""


def get_simulated_frames() -> list[dict]:
    """
    Returns 30 diverse simulated video frames covering a full 24-hour patrol cycle.

    Each frame is a dict with:
        - frame_id (int): Sequential frame identifier
        - time (str): Timestamp in HH:MM format
        - location (str): Where the drone is patrolling
        - description (str): Rich text description of what the camera sees

    Returns:
        List of 30 frame dictionaries
    """
    frames = [
        # === EARLY MORNING (06:00 - 08:00) — Shift start, employee arrivals ===
        {
            "frame_id": 1,
            "time": "06:00",
            "location": "Main Gate",
            "description": "Security guard opening the main gate. No vehicles or pedestrians in view. Morning light, clear visibility. Gate barrier is being raised."
        },
        {
            "frame_id": 2,
            "time": "06:15",
            "location": "Main Gate",
            "description": "White Toyota Camry approaching the main gate from the east road. Single occupant visible — appears to be an employee with a badge. Vehicle slowing down for entry."
        },
        {
            "frame_id": 3,
            "time": "06:30",
            "location": "Parking Lot A",
            "description": "White Toyota Camry parking in spot A-12. Driver exiting vehicle, wearing company uniform, walking toward Admin Building. Parking lot is mostly empty."
        },
        {
            "frame_id": 4,
            "time": "06:45",
            "location": "Perimeter Fence North",
            "description": "North perimeter fence intact. A stray cat walking along the fence line. No signs of intrusion or damage. Morning dew on the grass. Fence sensors appear normal."
        },
        {
            "frame_id": 5,
            "time": "07:00",
            "location": "Main Gate",
            "description": "Silver Honda Civic and Black BMW X5 arriving in convoy through main gate. Both vehicles have employee parking stickers visible. Normal morning traffic."
        },

        # === MID MORNING (08:00 - 11:00) — Business hours, deliveries ===
        {
            "frame_id": 6,
            "time": "08:30",
            "location": "Loading Dock",
            "description": "FedEx Delivery Van backing into Loading Dock Bay 2. Driver in FedEx uniform stepping out with a handheld scanner. Two warehouse workers approaching to receive packages."
        },
        {
            "frame_id": 7,
            "time": "09:00",
            "location": "Warehouse Entrance",
            "description": "Three employees in safety vests entering the warehouse through the main entrance. Forklift visible inside. Normal warehouse operations in progress."
        },
        {
            "frame_id": 8,
            "time": "09:30",
            "location": "Parking Lot B",
            "description": "Blue Ford F150 pickup truck entering Parking Lot B. No employee sticker visible. Truck has out-of-state license plates. Driver remains seated in vehicle for several minutes."
        },
        {
            "frame_id": 9,
            "time": "10:00",
            "location": "Admin Building",
            "description": "Group of 4 people in business attire entering the Admin Building front entrance. Appears to be a scheduled meeting — visitor badges visible on lanyards. Receptionist greeting them at the door."
        },
        {
            "frame_id": 10,
            "time": "10:30",
            "location": "Server Room Exterior",
            "description": "Maintenance technician in company coveralls using a keycard to access the Server Room exterior door. Tool bag in hand. Security badge clearly visible."
        },

        # === MIDDAY (11:00 - 14:00) — Lunch, routine activity ===
        {
            "frame_id": 11,
            "time": "11:30",
            "location": "Parking Lot A",
            "description": "Blue Ford F150 from Parking Lot B now seen driving slowly through Parking Lot A. Same out-of-state plates. Vehicle circling the lot without parking. Suspicious behavior — possible surveillance."
        },
        {
            "frame_id": 12,
            "time": "12:00",
            "location": "Admin Building",
            "description": "Multiple employees exiting Admin Building for lunch break. Approximately 8-10 people walking toward Parking Lot A. Normal midday activity."
        },
        {
            "frame_id": 13,
            "time": "12:30",
            "location": "Main Gate",
            "description": "UPS Delivery Truck entering through main gate. UPS branding clearly visible. Driver showing delivery manifest to the security guard at the checkpoint."
        },
        {
            "frame_id": 14,
            "time": "13:00",
            "location": "Loading Dock",
            "description": "UPS Delivery Truck at Loading Dock Bay 1. Three large pallets being unloaded. Warehouse supervisor checking delivery against order sheet. Normal delivery operation."
        },

        # === AFTERNOON (14:00 - 18:00) — Continued operations, end of business ===
        {
            "frame_id": 15,
            "time": "14:30",
            "location": "Perimeter Fence East",
            "description": "Person in dark hoodie standing near the east perimeter fence, looking through the chain-link. Not an employee — no badge visible. Person appears to be taking photos of the warehouse with a phone."
        },
        {
            "frame_id": 16,
            "time": "14:45",
            "location": "Perimeter Fence East",
            "description": "Same person in dark hoodie now walking along the east perimeter fence toward the south corner. Still taking photos. No vehicle visible nearby — person appears to have arrived on foot."
        },
        {
            "frame_id": 17,
            "time": "15:00",
            "location": "Main Gate",
            "description": "Blue Ford F150 exiting through main gate at moderate speed. Same out-of-state plates from earlier. Driver not making eye contact with security guard. Vehicle heading east."
        },
        {
            "frame_id": 18,
            "time": "16:30",
            "location": "Parking Lot A",
            "description": "Red Chevrolet Silverado parked in an unauthorized zone near the emergency exit. Engine running, no occupant visible inside. Hazard lights are on."
        },
        {
            "frame_id": 19,
            "time": "17:00",
            "location": "Main Gate",
            "description": "End of business traffic. Silver Honda Civic, Black BMW X5, and two other vehicles exiting through the main gate. Normal employee departure pattern. Security guard waving them through."
        },
        {
            "frame_id": 20,
            "time": "17:30",
            "location": "Emergency Exit Rear",
            "description": "Rear emergency exit door is ajar. No person visible. Door should be closed and locked at all times. Interior lights flickering — possible maintenance issue."
        },

        # === EVENING (18:00 - 22:00) — Reduced activity, transition to night ===
        {
            "frame_id": 21,
            "time": "18:30",
            "location": "Parking Lot A",
            "description": "Parking lot nearly empty. Only 3 vehicles remaining — White Toyota Camry in A-12, Red Chevrolet Silverado still in unauthorized zone (engine now off), and an unrecognized gray sedan in A-5."
        },
        {
            "frame_id": 22,
            "time": "19:00",
            "location": "Warehouse Entrance",
            "description": "Night shift security guard beginning patrol at warehouse entrance. Flashlight beam visible. Guard checking door locks and scanning badge at checkpoint. Normal shift change procedure."
        },
        {
            "frame_id": 23,
            "time": "20:00",
            "location": "Perimeter Fence South",
            "description": "Two deer near the south perimeter fence, grazing on the lawn. Motion sensors triggered but no human activity. Wildlife false alarm — common occurrence per historical data."
        },
        {
            "frame_id": 24,
            "time": "21:30",
            "location": "Main Gate",
            "description": "White Toyota Camry exiting main gate. Late departure — employee working overtime. Security guard logs the exit. Gate area well-lit, no other activity."
        },

        # === NIGHT (22:00 - 02:00) — High security, suspicious events ===
        {
            "frame_id": 25,
            "time": "22:15",
            "location": "Perimeter Fence North",
            "description": "Person in dark clothing crouching near the north perimeter fence. Appears to be testing the fence for weaknesses. No badge or identification visible. Night vision shows a backpack on the ground beside them."
        },
        {
            "frame_id": 26,
            "time": "22:30",
            "location": "Perimeter Fence North",
            "description": "Same person from Frame 25 now attempting to climb the north perimeter fence. Hands on the chain-link, one foot on the lower rail. Backpack slung over shoulder. Clear perimeter breach attempt."
        },
        {
            "frame_id": 27,
            "time": "23:00",
            "location": "Main Gate",
            "description": "Unidentified dark-colored SUV idling near the main gate with headlights off. Windows are tinted — occupants not visible. Vehicle not in the known vehicles database. License plate partially obscured by mud."
        },
        {
            "frame_id": 28,
            "time": "23:30",
            "location": "Server Room Exterior",
            "description": "Person in a ski mask approaching the Server Room exterior door. Attempting to use a device on the keycard reader. Unauthorized access attempt. No security badge visible."
        },
        {
            "frame_id": 29,
            "time": "00:15",
            "location": "Loading Dock",
            "description": "Loading dock bay 3 door partially open from inside. No scheduled deliveries at this hour. Shadow of a person visible inside the dock area. Dock lights are off — area should be fully illuminated per security protocol."
        },
        {
            "frame_id": 30,
            "time": "01:00",
            "location": "Parking Lot B",
            "description": "Two individuals near the gray sedan in Parking Lot B (same vehicle from earlier in A-5, now relocated). Trunk is open, items being loaded. Both wearing dark clothing with face coverings. Highly suspicious — potential theft in progress."
        },
    ]

    return frames


def get_frame_by_id(frame_id: int) -> dict | None:
    """Get a specific frame by its ID."""
    frames = get_simulated_frames()
    for frame in frames:
        if frame["frame_id"] == frame_id:
            return frame
    return None


def get_frames_by_time_range(start_time: str, end_time: str) -> list[dict]:
    """Get frames within a time range (HH:MM format)."""
    frames = get_simulated_frames()
    start_minutes = _time_to_minutes(start_time)
    end_minutes = _time_to_minutes(end_time)

    # Handle overnight ranges (e.g., 22:00 to 02:00)
    if end_minutes < start_minutes:
        return [f for f in frames if _time_to_minutes(f["time"]) >= start_minutes
                or _time_to_minutes(f["time"]) <= end_minutes]
    else:
        return [f for f in frames if start_minutes <= _time_to_minutes(f["time"]) <= end_minutes]


def _time_to_minutes(time_str: str) -> int:
    """Convert HH:MM to total minutes for comparison."""
    parts = time_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])
