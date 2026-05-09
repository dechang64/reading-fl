"""全局配置：API密钥、常量、环境检测"""

import os

# ── GLM API（智谱AI，OpenAI 兼容格式）──
GLM_API_KEY = os.environ.get("GLM_API_KEY", "")
GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

# ── MiniMax API（仅用于音乐生成，可选）──
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = "https://api.minimaxi.com"

# ── 模型 ──
CHAT_MODEL = "glm-4-flash"          # GLM 免费模型，速度快，适合对话
MUSIC_MODEL = "music-2.6-free"      # MiniMax 音乐模型

# ── 数据库（Streamlit Cloud 无持久文件系统，用内存数据库）──
DB_PATH = os.environ.get("TREEHOLE_DB_PATH", ":memory:")

# ── 模式检测 ──
MOCK_MODE = not GLM_API_KEY

# ── 设计令牌 ──
INK = "#2c1810"
PAPER = "#f5f0e8"
PAPER2 = "#e8dfd0"
RED = "#c0392b"
GOLD = "#b8860b"
JADE = "#2d6a4f"
MUTED = "#8b7355"

# ── 6大场景（与原版 index.html SCENES 完全对齐）──
SCENES = [
    {"name": "潇湘馆", "icon": "🎋", "desc": "竹林深处，月影斑驳",
     "mood": "孤独、思念", "char": "林黛玉", "theory": "叙事疗法",
     "style": "倾听你的心事", "color": "#2d6a4f"},
    {"name": "蘅芜苑", "icon": "🌿", "desc": "幽香弥漫，清冷如月",
     "mood": "迷茫、压抑", "char": "薛宝钗", "theory": "认知行为疗法",
     "style": "理性帮你理清", "color": "#5a7d6b"},
    {"name": "怡红院", "icon": "🌸", "desc": "花团锦簇，温暖如春",
     "mood": "焦虑、不安", "char": "贾宝玉", "theory": "人本主义",
     "style": "温柔化解不安", "color": "#c0392b"},
    {"name": "稻香村", "icon": "🌾", "desc": "田园宁静，炊烟袅袅",
     "mood": "疲惫、倦怠", "char": "李纨", "theory": "正念+ACT",
     "style": "安静的陪伴", "color": "#8b7355"},
    {"name": "藕香榭", "icon": "🪷", "desc": "碧水清波，荷香四溢",
     "mood": "纠结、犹豫", "char": "史湘云", "theory": "积极心理学",
     "style": "大大方方翻篇", "color": "#d4a574"},
    {"name": "秋爽斋", "icon": "📜", "desc": "窗明几净，笔墨书香",
     "mood": "愤怒、不满", "char": "探春", "theory": "赋权+SFBT",
     "style": "陪你把话说清楚", "color": "#a0522d"},
]

SCENE_MAP = {s["name"]: s for s in SCENES}

# ── 树洞释放方式 ──
RELEASE_METHODS = {
    "wind":  {"icon": "🍃", "title": "已随风飘散", "sub": "风会带走它"},
    "lake":  {"icon": "💧", "title": "已沉入湖底", "sub": "湖水会记住它"},
    "petal": {"icon": "🌸", "title": "已化为花瓣", "sub": "花瓣会替你开"},
    "smoke": {"icon": "🕯️", "title": "已燃为青烟", "sub": "烟会替你说"},
}

# ── 情绪分类 ──
EMOTIONS = ["悲伤", "焦虑", "愤怒", "迷茫", "疲惫", "孤独", "平静", "感恩", "期待"]

# ── 音乐场景 ──
MUSIC_PLACES = ["潇湘馆", "蘅芜苑", "怡红院", "稻香村", "藕香榭", "秋爽斋"]
MUSIC_MOODS = ["宁静", "释然", "思念", "疗愈", "欢愉", "沉思"]
