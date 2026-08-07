"""
DroneEduAI — Central Configuration
All paths, color tokens, and timing constants live here.
"""
import os

# ---------------------------------------------------------------------------
# Base directories
# ---------------------------------------------------------------------------
DRONE_EDU_DIR = os.path.dirname(os.path.abspath(__file__))   # .../DroneEduAI/
PROJECT_ROOT  = os.path.dirname(DRONE_EDU_DIR)                # .../AI_Drone_Edu_v2/

# ---------------------------------------------------------------------------
# Asset & model paths
# ---------------------------------------------------------------------------
ICONS_DIR          = os.path.join(PROJECT_ROOT, "icons")
GESTURE_TESTER_DIR = os.path.join(PROJECT_ROOT, "GestureTesterApp")
MODEL_TRAINER_DIR  = os.path.join(PROJECT_ROOT, "AIGestureModelTrainer")

DEFAULT_TASK_PATH   = os.path.join(GESTURE_TESTER_DIR, "hand_landmarker.task")
DEFAULT_MODEL_PATH  = os.path.join(MODEL_TRAINER_DIR,  "models", "gesture_model.pkl")
DEFAULT_SCALER_PATH = os.path.join(MODEL_TRAINER_DIR,  "models", "scaler.pkl")

# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------
DEFAULT_CAMERA_INDEX = 0
CAMERA_WIDTH  = 640    # Reduced from 720p to 480p for lighter CPU usage
CAMERA_HEIGHT = 480

# ---------------------------------------------------------------------------
# Gesture verification
# ---------------------------------------------------------------------------
GESTURE_CONFIRM_DURATION_MS       = 5000  # hold for 5 s to confirm
GESTURE_CONFIDENCE_THRESHOLD      = 60.0  # minimum % confidence
GESTURE_PROGRESS_UPDATE_INTERVAL  = 100   # ms between progress ticks

# ---------------------------------------------------------------------------
# Color palette  (Dark Theme)
# ---------------------------------------------------------------------------
COLOR_BG      = "#0F172A"
COLOR_CARD    = "#1E293B"
COLOR_BORDER  = "#334155"
COLOR_ACCENT  = "#8B5CF6"   # purple
COLOR_SUCCESS = "#22C55E"   # green
COLOR_DANGER  = "#EF4444"   # red
COLOR_WARNING = "#F59E0B"   # amber
COLOR_INFO    = "#3B82F6"   # blue
COLOR_TEXT    = "#F8FAFC"
COLOR_SUBTEXT = "#94A3B8"
COLOR_MUTED   = "#475569"

# Per-command accent colors
BLOCK_COLORS = {
    "TAKEOFF":   "#22C55E",
    "LAND":      "#EF4444",
    "FORWARD":   "#8B5CF6",
    "BACKWARD":  "#8B5CF6",
    "LEFT":      "#3B82F6",
    "RIGHT":     "#3B82F6",
    "UP":        "#06B6D4",
    "DOWN":      "#06B6D4",
    "HOVER":     "#F59E0B",
}

# Per-command SVG icon file stem
BLOCK_ICONS = {
    "TAKEOFF":   "takeoff",
    "LAND":      "land",
    "FORWARD":   "forward",
    "BACKWARD":  "backward",
    "LEFT":      "left",
    "RIGHT":     "right",
    "UP":        "up",
    "DOWN":      "down",
    "HOVER":     "hover",
}
