"""
Video Detector — Grounding DINO + DeepSORT real-time object detection & tracking.

Uses Grounding DINO (via HuggingFace Transformers) for open-vocabulary,
text-prompted zero-shot object detection. Combined with DeepSORT for
persistent object tracking across frames.

Key advantages over YOLOv8:
  - Text prompt detection: detect any object by description
  - Zero-shot: no retraining needed for new object types
  - Open vocabulary: "person with helmet", "red car", "intruder near fence"
  - Dynamic prompts: change detection targets at runtime
"""

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
from deep_sort_realtime.deepsort_tracker import DeepSort


# Security-focused detection prompt — period-separated object classes
# Grounding DINO requires lowercase text with periods between classes
SECURITY_PROMPT = (
    "person . car . truck . motorcycle . bicycle . bus . "
    "backpack . suitcase . bag . dog . cat . bird . "
    "laptop . cell phone . helmet . weapon . knife . gun . "
    "fence . gate . door . fire . smoke . drone . van . "
    "uniform . flashlight . camera ."
)

# Grounding DINO model ID from HuggingFace Hub
GDINO_MODEL_ID = "IDEA-Research/grounding-dino-tiny"

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
    "weapon": (0, 0, 255),       # Red
    "knife": (0, 0, 255),        # Red
    "gun": (0, 0, 255),          # Red
    "fire": (0, 50, 255),        # Red-orange
    "smoke": (128, 128, 128),    # Gray
    "drone": (255, 0, 255),      # Magenta
    "default": (0, 255, 0),      # Green
}


class VideoDetector:
    """Grounding DINO + DeepSORT object detection and tracking for drone footage."""

    def __init__(self, confidence: float = 0.4, text_prompt: str = None):
        """
        Initialize the detector.

        Args:
            confidence: Minimum detection confidence (box_threshold)
            text_prompt: Custom text prompt for detection (period-separated).
                         Defaults to SECURITY_PROMPT.
        """
        print(f"[Grounding DINO] Loading model: {GDINO_MODEL_ID}...")
        self.processor = AutoProcessor.from_pretrained(GDINO_MODEL_ID)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(GDINO_MODEL_ID)

        # Use GPU if available, otherwise CPU
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = self.model.to(self.device)
        self.model.eval()
        print(f"[Grounding DINO] Model loaded on {self.device}")

        self.tracker = DeepSort(
            max_age=30,
            n_init=3,
            max_iou_distance=0.7,
        )
        self.confidence = confidence
        self.text_threshold = 0.25
        self.text_prompt = text_prompt or SECURITY_PROMPT
        self.frame_count = 0
        self.total_detections = 0
        self.unique_tracks = set()

    def process_frame(self, frame: np.ndarray) -> dict:
        """
        Process a single video frame through Grounding DINO + DeepSORT.

        Args:
            frame: OpenCV BGR frame (numpy array)

        Returns:
            Dict with annotated_frame, detections, tracks, and metadata
        """
        self.frame_count += 1

        # Convert BGR (OpenCV) to RGB (PIL)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        h, w = frame.shape[:2]

        # Run Grounding DINO detection
        inputs = self.processor(
            images=pil_image,
            text=self.text_prompt,
            return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)

        # Post-process results
        results = self.processor.post_process_grounded_object_detection(
            outputs,
            inputs.input_ids,
            threshold=self.confidence,
            text_threshold=self.text_threshold,
            target_sizes=[(h, w)]
        )

        detections = []
        raw_detections = []

        if results and len(results) > 0:
            result = results[0]
            boxes = result["boxes"]
            scores = result["scores"]
            # Use text_labels if available, otherwise fall back to labels
            labels = result.get("text_labels", result.get("labels", []))

            for i in range(len(boxes)):
                box = boxes[i].cpu().tolist()
                conf = scores[i].cpu().item()
                raw_label = labels[i]
                # Handle both string labels and tensor indices
                if isinstance(raw_label, str):
                    label = raw_label.strip().lower()
                else:
                    label = str(raw_label).strip().lower()

                # Skip empty labels or zero-area bounding boxes
                if not label:
                    continue

                x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
                if (x2 - x1) <= 0 or (y2 - y1) <= 0:
                    continue

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

    def set_prompt(self, prompt: str):
        """
        Dynamically update the detection text prompt.

        This is a key advantage over YOLO — change what you detect at runtime.

        Args:
            prompt: Period-separated detection classes (e.g., "person . weapon . fire .")
        """
        self.text_prompt = prompt.lower()

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
