DEFECT_CLASSES = ["missing_hole", "mouse_bite", "open_circuit", "short", "spur", "spurious_copper"]

DEFECT_COLORS = {
    "missing_hole": "#ef4444",
    "mouse_bite": "#f97316",
    "open_circuit": "#eab308",
    "short": "#dc2626",
    "spur": "#22c55e",
    "spurious_copper": "#a855f7",
    "good": "#6b7280",
}

DEFECT_DESCRIPTIONS = {
    "missing_hole": "Drill hole absent — prevents component mounting",
    "mouse_bite": "Copper nibble on trace edge — may cause open circuit",
    "open_circuit": "Broken copper trace — signal interruption",
    "short": "Unintended copper bridge — signal shorting",
    "spur": "Extra copper protrusion — potential short risk",
    "spurious_copper": "Unwanted copper deposit — manufacturing contamination",
}

SEVERITY_LEVELS = {
    "missing_hole": {"severity": "critical", "color": "#ef4444"},
    "open_circuit": {"severity": "critical", "color": "#ef4444"},
    "short": {"severity": "critical", "color": "#ef4444"},
    "mouse_bite": {"severity": "major", "color": "#f97316"},
    "spur": {"severity": "minor", "color": "#22c55e"},
    "spurious_copper": {"severity": "major", "color": "#f97316"},
}

FACTORY_PRESETS = {
    "shenzhen_smt": {
        "name": "Shenzhen SMT Plant",
        "lines": 8,
        "capacity": 50000,
        "defect_dist": {"short": 0.25, "open_circuit": 0.20, "spurious_copper": 0.15, "missing_hole": 0.15, "spur": 0.10, "mouse_bite": 0.15},
    },
    "dongguan_pcb": {
        "name": "Dongguan PCB Plant",
        "lines": 5,
        "capacity": 30000,
        "defect_dist": {"short": 0.20, "open_circuit": 0.25, "spurious_copper": 0.10, "missing_hole": 0.20, "spur": 0.15, "mouse_bite": 0.10},
    },
    "suzhou_hdi": {
        "name": "Suzhou HDI Plant",
        "lines": 3,
        "capacity": 15000,
        "defect_dist": {"short": 0.15, "open_circuit": 0.15, "spurious_copper": 0.25, "missing_hole": 0.20, "spur": 0.15, "mouse_bite": 0.10},
    },
}

COLORS = {
    "primary": "#38bdf8",
    "secondary": "#8b5cf6",
    "accent": "#22c55e",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "bg_dark": "#0a0e1a",
    "bg_card": "#111827",
    "text": "#e2e8f0",
    "text_muted": "#64748b",
    "missing_hole": "#ef4444",
    "mouse_bite": "#f97316",
    "open_circuit": "#eab308",
    "short": "#dc2626",
    "spur": "#22c55e",
    "spurious_copper": "#a855f7",
    "good": "#6b7280",
}
