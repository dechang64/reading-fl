"""共享 CSS — 所有页面通过 inject_css() 注入"""

CSS = """<style>
/* 隐藏 Streamlit 默认元素 */
#MainMenu, footer, header {visibility: hidden}
.block-container {padding-top: 0.5rem; padding-bottom: 2rem; max-width: 520px}

/* 全局字体 */
.stApp {font-family: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', serif}

/* 卡片样式 */
.card {
    background: #f5f0e8;
    border-radius: 12px;
    padding: 1.2rem;
    margin: 0.8rem 0;
    border: 1px solid #e8dfd0;
}
.card-dark {
    background: #2c1810;
    color: #f5f0e8;
    border-radius: 12px;
    padding: 1.2rem;
    margin: 0.8rem 0;
}

/* 场景卡片 */
.scene-card {
    background: linear-gradient(135deg, #f5f0e8, #e8dfd0);
    border-radius: 16px;
    padding: 1.5rem;
    margin: 0.5rem 0;
    border: 1px solid #d4c5a9;
    cursor: pointer;
    transition: all 0.3s;
}
.scene-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(44,24,16,0.12);
    border-color: #b8860b;
}

/* 聊天气泡 */
.chat-ai {
    background: #e8dfd0;
    border-radius: 16px 16px 16px 4px;
    padding: 0.8rem 1rem;
    margin: 0.4rem 0;
    max-width: 85%;
}
.chat-user {
    background: #2c1810;
    color: #f5f0e8;
    border-radius: 16px 16px 4px 16px;
    padding: 0.8rem 1rem;
    margin: 0.4rem 0;
    max-width: 85%;
    margin-left: auto;
}

/* 标签 */
.tag {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    background: rgba(184,134,11,0.1);
    color: #b8860b;
    border-radius: 99px;
    font-size: 0.8rem;
    margin: 0.15rem;
}

/* 模式指示器 */
.mock-badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    background: rgba(192,57,43,0.1);
    color: #c0392b;
    border-radius: 99px;
    font-size: 0.7rem;
}

/* Hero 头部 */
.hero {
    background: linear-gradient(135deg, #2c1810, #4a2c1a 50%, #3d1f0e);
    padding: 2.5rem 1.5rem 2rem;
    color: #f5f0e8;
    text-align: center;
    position: relative;
    overflow: hidden;
    border-radius: 0 0 16px 16px;
}
.hero::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse at 30% 50%, rgba(184,134,11,0.12), transparent 60%);
    pointer-events: none;
}
.hero h1 {
    font-size: 1.8rem;
    font-weight: 700;
    letter-spacing: 0.4rem;
    position: relative;
}
.hero .sub {
    opacity: 0.7;
    font-size: 0.85rem;
    margin: 0.4rem 0 0.8rem;
    position: relative;
}
.hero .motto {
    font-size: 0.8rem;
    opacity: 0.5;
    font-style: italic;
    position: relative;
}

/* 安全徽章 */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.3rem 0.8rem;
    background: rgba(45,106,79,0.1);
    color: #2d6a4f;
    border-radius: 99px;
    font-size: 0.75rem;
}

/* 结果卡片 */
.result-type {
    font-size: 2.5rem;
    font-weight: 800;
    color: #c0392b;
    text-align: center;
    letter-spacing: 0.3rem;
    margin: 0.5rem 0;
}
.result-desc {
    text-align: center;
    font-size: 0.9rem;
    color: #8b7355;
    margin-bottom: 0.8rem;
}
.result-scene {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.8rem;
    background: #fff;
    border-radius: 12px;
    border: 1px solid #e8dfd0;
    margin-bottom: 0.8rem;
}
.result-scene .icon {
    font-size: 2rem;
    width: 48px;
    text-align: center;
}
.result-scene .name {
    font-weight: 600;
    font-size: 0.95rem;
    color: #2c1810;
}
.result-scene .info {
    font-size: 0.8rem;
    color: #8b7355;
    margin-top: 0.1rem;
}
.result-reason {
    background: #f5f0e8;
    border-radius: 12px;
    padding: 0.8rem;
    margin: 0.8rem 0;
    font-size: 0.85rem;
    line-height: 1.7;
    color: #2c1810;
}
.result-quote {
    text-align: center;
    font-style: italic;
    color: #8b7355;
    font-size: 0.85rem;
    padding: 0.8rem;
    border-left: 3px solid #b8860b;
    margin: 0.8rem 0;
}

/* 星座按钮 */
.zodiac-btn {
    background: #fff;
    border: 1px solid #e8dfd0;
    border-radius: 12px;
    padding: 0.6rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
}
.zodiac-btn:hover {
    border-color: #b8860b;
    box-shadow: 0 4px 12px rgba(44,24,16,0.08);
}

/* 星盘卡片 */
.chart-planet {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.5rem 0.7rem;
    background: #fff;
    border-radius: 10px;
    margin: 0.3rem 0;
    border: 1px solid #e8dfd0;
}
.chart-planet .p-icon {
    font-size: 1.3rem;
    width: 32px;
    text-align: center;
    flex-shrink: 0;
}
.chart-planet .p-info { flex: 1; }
.chart-planet .p-name { font-size: 0.78rem; font-weight: 600; }
.chart-planet .p-sign { font-size: 0.7rem; color: #8b7355; }
.chart-planet .p-desc { font-size: 0.72rem; color: #2c1810; margin-top: 0.1rem; line-height: 1.5; }

/* 星盘总结 */
.chart-summary {
    background: linear-gradient(135deg, #2c1810, #4a2c1a);
    color: #f5f0e8;
    border-radius: 12px;
    padding: 1rem;
    margin: 0.8rem 0;
    text-align: center;
}

/* 元素标签 */
.elem-label {
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.3rem 0;
    margin-top: 0.5rem;
}

/* 动画 */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fadeIn 0.5s ease-out; }
</style>"""

import streamlit as st

def inject_css():
    """在任意页面注入全局 CSS"""
    st.markdown(CSS, unsafe_allow_html=True)
