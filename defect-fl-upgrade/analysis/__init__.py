# ── analysis/__init__.py ──
from .detector import PCBDefectDetector
from .fl_engine import DefectFLEngine

# DINOv2PCBExtractor requires torchvision — lazy import to avoid
# ModuleNotFoundError on Streamlit Cloud where torchvision may be unavailable.
try:
    from .feature_extractor import DINOv2PCBExtractor
except (ImportError, ModuleNotFoundError):
    DINOv2PCBExtractor = None
