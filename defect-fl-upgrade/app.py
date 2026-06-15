"""app.py — Defect-FL Streamlit App (v2 — Refactored)

Architecture: Sidebar navigation + Dashboard landing page
- 5 pages instead of 8 tabs
- Merged detection pipeline (Detect → Segment → Explain)
- Dashboard as entry point with usage guide
- Prominent mock-mode indicator
"""

import streamlit as st
import numpy as np
from PIL import Image, ImageDraw
import tempfile
import time
import json
import os

from utils.constants import FACTORY_PRESETS

# ── Safe import: analysis/ classes with fallback stubs ──
try:
    from analysis.detector import PCBDefectDetector
except ImportError:
    class PCBDefectDetector:
        def __init__(self, mode="mock", **kwargs):
            self.mode = mode
        def detect(self, image, conf_threshold=0.5):
            return []

try:
    from analysis.segmentor import PCBDefectSegmentor
except ImportError:
    class PCBDefectSegmentor:
        def __init__(self, mode="mock", **kwargs):
            self.mode = mode
        def segment(self, image, detections):
            return []

try:
    from analysis.fl_engine import DefectFLEngine
except ImportError:
    class DefectFLEngine:
        def __init__(self, **kwargs):
            pass
        def run_federated_training(self, n_rounds=5, n_clients=3, local_epochs=2, lr=0.001):
            return []


# ============================================================
# Page Config
# ============================================================
st.set_page_config(
    page_title="Defect-FL · Industrial Defect Detection (PCB)",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Custom CSS
# ============================================================
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
    }
    h1, h2, h3 { color: #e2e8f0 !important; }
    p, li, span { color: #cbd5e1 !important; }
    .stCaption, .stMarkdown { color: #cbd5e1 !important; }

    /* Markdown table text visible on dark background */
    table { color: #e2e8f0 !important; background-color: #1e293b !important; border-color: #334155 !important; }
    table th { color: #f1f5f9 !important; background-color: #334155 !important; border-color: #475569 !important; font-weight: 600; }
    table td { color: #e2e8f0 !important; background-color: #1e293b !important; border-color: #334155 !important; }
    table tr:nth-child(even) td { background-color: #1a2332 !important; }

    /* Metric cards */
    [data-testid="stMetricValue"] { color: #38bdf8 !important; }
    [data-testid="stMetricLabel"] { color: #94a3b8 !important; }

    /* Buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        color: white;
    }

    /* Sidebar nav styling */
    section[data-testid="stSidebar"] label[data-baseweb="radio"] {
        color: #e2e8f0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #e2e8f0 !important;
    }

    /* Demo mode banner */
    .demo-banner {
        background: linear-gradient(90deg, #f59e0b22, #f59e0b11);
        border: 1px solid #f59e0b;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        margin-bottom: 1rem;
        text-align: center;
        color: #f59e0b;
        font-weight: 600;
        font-size: 0.9rem;
    }

    /* Dashboard hero */
    .hero-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f3460 100%);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        border: 1px solid #334155;
    }
    .hero-header h1 { font-size: 2rem !important; font-weight: 700 !important; margin: 0 0 0.5rem 0 !important; color: white !important; }
    .hero-header p { font-size: 0.95rem !important; opacity: 0.8 !important; margin: 0 !important; color: white !important; }

    /* Step indicator */
    .step-active {
        background: #3b82f622;
        border: 2px solid #3b82f6;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        text-align: center;
        font-weight: 700;
        color: #3b82f6;
    }
    .step-done {
        background: #22c55e22;
        border: 2px solid #22c55e;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        text-align: center;
        font-weight: 700;
        color: #22c55e;
    }
    .step-pending {
        background: #334155;
        border: 2px solid #475569;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        text-align: center;
        font-weight: 700;
        color: #64748b;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# Session State Init
# ============================================================
if "detector" not in st.session_state:
    st.session_state.detector = PCBDefectDetector(mode="mock")
if "segmentor" not in st.session_state:
    st.session_state.segmentor = PCBDefectSegmentor(mode="mock")
if "fl_engine" not in st.session_state:
    st.session_state.fl_engine = DefectFLEngine()
if "history" not in st.session_state:
    st.session_state.history = []
if "last_detection" not in st.session_state:
    st.session_state.last_detection = None
if "last_image" not in st.session_state:
    st.session_state.last_image = None
if "conf_threshold" not in st.session_state:
    st.session_state.conf_threshold = 0.5
if "inspector_step" not in st.session_state:
    st.session_state.inspector_step = 1


# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/circuit-board.png", width=64)
    st.title("Defect-FL")
    st.caption("Industrial Defect Detection (PCB) v2.0")
    st.divider()

    # ── Navigation ──
    page = st.radio(
        "Navigate",
        [
            "🏠 Dashboard",
            "🔍 Defect Inspector",
            "🌐 Federated Learning",
            "🧠 Research Tools",
            "🎓 Student Showcase",
            "ℹ️ About",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    # ── Global Settings ──
    st.subheader("Settings")

    detect_mode = st.selectbox(
        "Detection Mode",
        ["mock", "yolo"],
        format_func=lambda x: "⚠️ Demo Mode" if x == "mock" else "YOLOv12n (Real)",
    )
    if detect_mode != st.session_state.detector.mode:
        st.session_state.detector = PCBDefectDetector(
            mode="mock" if "mock" in detect_mode else "yolo"
        )

    conf_threshold = st.slider("Confidence Threshold", 0.1, 0.95,
                               float(st.session_state.get("conf_threshold", 0.5)), 0.05)
    st.session_state.conf_threshold = conf_threshold

    st.divider()

    st.subheader("Factory Info")
    factory = st.selectbox(
        "Select Factory",
        list(FACTORY_PRESETS.keys()),
        format_func=lambda x: FACTORY_PRESETS[x]["name"],
    )
    factory_info = FACTORY_PRESETS[factory]
    st.session_state.factory_info = factory_info
    st.caption(f"Lines: {factory_info['lines']} | Capacity: {factory_info['capacity']:,}/day")

    st.divider()

    # ── Detection History ──
    st.subheader("Recent Detections")
    if st.session_state.history:
        for h in st.session_state.history[-5:]:
            status = "🔴" if h["defects"] > 0 else "✅"
            st.markdown(f"{status} **{h['factory']}** — {h['defects']} defects ({h['time']})")
    else:
        st.caption("No detections yet")


# ============================================================
# Demo Mode Banner
# ============================================================
if st.session_state.detector.mode == "mock":
    st.markdown("""
    <div class="demo-banner">
        ⚠️ Demo Mode — Detection results are simulated. Switch to YOLO mode in sidebar for real inference.
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# Route to Pages
# ============================================================
if page == "🏠 Dashboard":
    from modules import dashboard
    dashboard.render()

elif page == "🔍 Defect Inspector":
    from modules import defect_inspector
    defect_inspector.render()

elif page == "🌐 Federated Learning":
    from modules import fl_training
    fl_training.render()

elif page == "🧠 Research Tools":
    from modules import research_tools
    research_tools.render()

elif page == "🎓 Student Showcase":
    from modules import student_showcase
    student_showcase.render()

elif page == "ℹ️ About":
    from modules import about
    about.render()
