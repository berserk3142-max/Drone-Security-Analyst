"""
Video Detector — YOLOv8 + DeepSORT real-time object detection & tracking.

Processes drone surveillance video frame-by-frame, detecting and tracking
objects (people, vehicles, etc.) with persistent IDs across frames.
"""

import cv2
import numpy as np
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort


# Security-relevant COCO classes
SECURITY_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    14: "bird",
    15: "cat",
    16: "dog",
    24: "backpack",
    25: "umbrella",
    26: "handbag",
    27: "tie",
    28: "suitcase",
    63: "laptop",
    67: "cell phone",
}

# Risk colors for bounding boxes (BGR for OpenCV)
RISK_COLORS = {
    "person": (0, 140, 255),     # Orange
    "car": (255, 180, 0),        # Cyan-blue
    "truck": (0, 200, 255),      # Yellow-orange
    "motorcycle": (200, 100, 0), # Teal
    "bus": (150, 50, 0),         # Dark teal
    "bicycle": (180, 180, 0),    # Cyan
    "backpack": (0, 0, 255),     # Red
    "suitcase": (0, 0, 200),     # Dark red
    "default": (0, 255, 0),      # Green
}


class VideoDetector:
    """YOLOv8 + DeepSORT object detection and tracking for drone footage."""

    def __init__(self, model_name: str = "yolov8n.pt", confidence: float = 0.4):
        """
        Initialize the detector.

        Args:
            model_name: YOLOv8 model name (auto-downloads on first use)
            confidence: Minimum detection confidence threshold
        """
        self.model = YOLO(model_name)
        self.tracker = DeepSort(
            max_age=30,
            n_init=3,
            max_iou_distance=0.7,
        )
        self.confidence = confidence
        self.frame_count = 0
        self.total_detections = 0
        self.unique_tracks = set()

    def process_frame(self, frame: np.ndarray) -> dict:
        """
        Process a single video frame through YOLO + DeepSORT.

        Args:
            frame: OpenCV BGR frame (numpy array)

        Returns:
            Dict with annotated_frame, detections, tracks, and metadata
        """
        self.frame_count += 1

        # Run YOLO detection
        results = self.model(frame, verbose=False)[0]
        detections = []
        raw_detections = []

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            label = self.model.names.get(cls, f"class_{cls}")

            if conf >= self.confidence and cls in SECURITY_CLASSES:
                # DeepSORT expects [x, y, w, h]
                detections.append(([x1, y1, x2 - x1, y2 - y1], conf, label))
                raw_detections.append({
                    "label": label,
                    "confidence": round(conf, 2),
                    "bbox": [x1, y1, x2, y2],
                })

        self.total_detections += len(detections)

        # Update DeepSORT tracker
        tracks = self.tracker.update_tracks(detections, frame=frame)

        # Draw annotations on frame
        annotated = frame.copy()
        active_tracks = []

        for track in tracks:
            if not track.is_confirmed():
                continue

            tid = track.track_id
            label = track.get_det_class() or "unknown"
            x1, y1, x2, y2 = map(int, track.to_ltrb())

            self.unique_tracks.add(tid)

            # Get color based on object type
            color = RISK_COLORS.get(label, RISK_COLORS["default"])

            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Draw label background
            text = f"{label} #{tid}"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annotated, (x1, y1 - th - 10), (x1 + tw + 4, y1), color, -1)
            cv2.putText(annotated, text, (x1 + 2, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            active_tracks.append({
                "track_id": tid,
                "label": label,
                "bbox": [x1, y1, x2, y2],
            })

        # Draw frame info overlay
        info_text = f"Frame: {self.frame_count} | Objects: {len(active_tracks)} | Tracks: {len(self.unique_tracks)}"
        cv2.putText(annotated, info_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        return {
            "annotated_frame": annotated,
            "frame_id": self.frame_count,
            "raw_detections": raw_detections,
            "active_tracks": active_tracks,
            "total_objects": len(active_tracks),
            "unique_track_count": len(self.unique_tracks),
        }

    def get_detection_summary(self, tracks: list) -> str:
        """Generate a text summary of current detections for the LLM agent."""
        if not tracks:
            return "No objects detected in current frame."

        objects = {}
        for t in tracks:
            label = t["label"]
            objects[label] = objects.get(label, 0) + 1

        parts = [f"{count} {label}{'s' if count > 1 else ''}" for label, count in objects.items()]
        return f"Detected: {', '.join(parts)}"

    def reset(self):
        """Reset tracker state for a new video."""
        self.tracker = DeepSort(max_age=30, n_init=3, max_iou_distance=0.7)
        self.frame_count = 0
        self.total_detections = 0
        self.unique_tracks = set()


def get_video_info(video_path: str) -> dict:
    """Get basic video metadata."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": "Cannot open video file"}

    info = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "duration_sec": int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1)),
    }
    cap.release()
    return info
