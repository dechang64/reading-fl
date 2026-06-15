"""技术架构 — 给开发者/技术读者看 (学坐忘灯)"""
import streamlit as st
import sys
import os

st.set_page_config(page_title="技术架构 · 心灯", page_icon="🏗️", layout="centered", initial_sidebar_state="auto")

st.markdown("""
<style>
:root { --bg: #0d0d0f; --card: rgba(255,255,255,0.04); --text: #e8e4dc; --text-muted: #8b8680;
        --accent: #d4a574; --ember: #c4694a; --border: rgba(212,165,116,0.15); }
.stApp { background: linear-gradient(180deg, #0d0d0f 0%, #0a0a0c 100%); }
.main .block-container { max-width: 720px; padding-top: 1.5rem; }
h1, h2, h3 { color: var(--text) !important; font-weight: 500 !important; }
h1 { font-size: 1.7rem !important; }
h2 { font-size: 1.3rem !important; color: var(--accent) !important; margin-top: 2.5rem !important; }
h3 { font-size: 0.95rem !important; color: var(--text) !important; margin-top: 1.5rem !important; }
p, .stMarkdown { color: var(--text) !important; line-height: 1.7; }
.stCaption { color: var(--text-muted) !important; }
.code-block {
    background: #16161a;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
    font-family: "SF Mono", "Monaco", "Consolas", monospace;
    font-size: 0.82rem;
    color: var(--text);
    overflow-x: auto;
    line-height: 1.6;
}
.info-card {
    background: var(--card);
    border-left: 3px solid var(--accent);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 1rem 0;
}
.privacy-strip {
    background: linear-gradient(90deg, rgba(196,105,74,0.1) 0%, rgba(212,165,116,0.1) 100%);
    border: 1px solid var(--border); border-radius: 8px;
    padding: 0.7rem 1rem; color: var(--accent);
    font-size: 0.88rem; text-align: center; margin: 1rem 0;
}
@media (max-width: 640px) {
    .main .block-container { padding-left: 0.9rem !important; padding-right: 0.9rem !important; }
    h1 { font-size: 1.4rem !important; }
    .code-block { font-size: 0.75rem !important; }
}
</style>
""", unsafe_allow_html=True)


# 兼容老 webview:深 fallback CSS
st.markdown('<style>\n/* 兼容老 webview 的深 fallback */\nhtml, body, .stApp, [data-testid="stAppViewContainer"] {\n    background: #0d0d0f !important;\n    color: #e8e4dc !important;\n}\nsection[data-testid="stSidebar"] {\n    background-color: #0a0a0c !important;\n    color: #e8e4dc !important;\n    border-right: 1px solid rgba(212, 165, 116, 0.15) !important;\n}\nsection[data-testid="stSidebar"] * {\n    color: #e8e4dc !important;\n}\nsection[data-testid="stSidebar"] h1,\nsection[data-testid="stSidebar"] h2,\nsection[data-testid="stSidebar"] h3,\nsection[data-testid="stSidebar"] p,\nsection[data-testid="stSidebar"] span,\nsection[data-testid="stSidebar"] a,\nsection[data-testid="stSidebar"] .stCaption {\n    color: #e8e4dc !important;\n}\n.main .block-container,\n.main p,\n.main h1, .main h2, .main h3, .main h4,\n.main .stMarkdown, .main .stText, .main .stCaption {\n    color: #e8e4dc !important;\n}\n</style>', unsafe_allow_html=True)

st.page_link("app.py", label="← 回到首页", icon="🏠")

st.markdown("# 🏗️ 技术架构")
st.caption("FL + HNSW + 区块链审计 — 你的书摘,留在你手中")
st.markdown("""
<div class="privacy-strip">
    🔒 你的阅读数据永远不会离开你的书社
</div>
""", unsafe_allow_html=True)

# 4 个核心模块
st.markdown("## 4 大核心模块")

modules = [
    {
        "name": "联邦学习 (Federated Learning)",
        "icon": "🧠",
        "desc": "每个读者的数据留在本地,AI 训练后只上传模型参数,服务器聚合后下发更新。原始书摘永远不出设备。",
        "code": """# 每个书社一个 FL 客户端
for round in range(num_rounds):
    local_params = client.train_on_local_data()    # 本地训练
    aggregated = server.aggregate([local_params])  # 聚合
    client.update(aggregated)                      # 下发""",
    },
    {
        "name": "HNSW 向量检索",
        "icon": "🔗",
        "desc": "基于阅读感悟的语义嵌入,在向量空间中找到「灵魂书友」。不比较原始文本,只比较高维向量距离。",
        "code": """# 把每条感悟 embedding 到 64 维
embedding = model.encode(excerpt + reflection)
index.add(reader_id, embedding)

# 找最相似的 5 个读者
similar = index.search(embedding, k=5)""",
    },
    {
        "name": "区块链审计链",
        "icon": "⛓️",
        "desc": "每次联邦训练都有 SHA-256 哈希链记录,不可篡改,可追溯每轮训练的贡献者。",
        "code": """# 每次提交都上链
chain.add_block({
    'campus': 'guild_A',
    'round': 42,
    'model_hash': '0x...',
    'timestamp': now(),
})""",
    },
    {
        "name": "多任务学习 (Multi-Head)",
        "icon": "🎭",
        "desc": "共享 Backbone + 三个任务头:情感分类 (6 类)、质量评分 (0-1)、读者匹配 (嵌入向量)。",
        "code": """# 共享层 + 任务头
backbone = SharedTextEncoder()
emotion_head = nn.Linear(64, 6)      # 6 类情绪
quality_head = nn.Linear(64, 1)      # 质量 0-1
matching_head = nn.Linear(64, 64)    # 匹配向量""",
    },
]

for m in modules:
    st.markdown(f"### {m['icon']} {m['name']}")
    st.markdown(m["desc"])
    st.markdown(f'<div class="code-block">{m["code"]}</div>', unsafe_allow_html=True)

# 数据流
st.markdown("## 训练数据流")

st.markdown("""
```
3 书社客户端                       FL Server (聚合)
┌──────────┐  ┌──────────┐  ┌──────────┐
│ 夜读派  │  │ 晨读派  │  │ 全日派  │
│ 📖 书摘  │  │ 📖 书摘  │  │ 📖 书摘  │
│ 🧠 本地  │  │ 🧠 本地  │  │ 🧠 本地  │
│          │  │          │  │          │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │
     │  只传       │  只传        │  只传
     │  梯度       │  梯度        │  梯度
     │             │             │
     └─────────────┼─────────────┘
                   │
            ┌──────┴──────┐
            │   聚合 +   │
            │   审计链   │
            └─────────────┘
```
""")

# 隐私保证
st.markdown("## 隐私保证")

st.markdown("""
- ✅ **书摘原文**: 永远只在书社本地,从未上传
- ✅ **感悟文本**: 永远只在书社本地,从未上传
- ✅ **跨书社传输**: 只有模型参数(梯度) + 共振摘录(去标识化)
- ✅ **审计链**: 不可篡改,可追溯每轮训练
- ✅ **可证伪**: 任何第三方可以用脚本验证我们没有上传原始书摘
""")

# 联系
st.markdown("---")
st.caption("📖 Reading-FL · License: MIT · Powered by FedCtx")
