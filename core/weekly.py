"""金句周报 — User 每周 1 封邮件, 5 段精选 + 配乐 + AI 评

streamlit cloud 不支持后台 CRON, 简化版: 用户主动触发
- "📩 生成我的本周金句周报" 按钮
- HTML 周报渲染在页面上 (不真发邮件, v6.5 接 Resend)
- 199 元/年 会员: 解锁"自动每周发邮件"

数据来源: st.session_state.reflections + extra_reflections
"""
import streamlit as st
import html
import datetime
import hashlib
from typing import Optional


def _get_weekly_reflections() -> list[dict]:
    """取本周 (过去 7 天) 的所有摘录

    Returns:
        list of {excerpt, book, author, emotion, reflection, ts, ...}
    """
    all_refs = st.session_state.get("_xindeng_persisted_refs", [])
    if not all_refs:
        return []

    cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
    weekly = []
    for r in all_refs:
        ts_str = r.get("timestamp", "")
        try:
            ts = datetime.datetime.fromisoformat(ts_str)
            if ts >= cutoff:
                weekly.append(r)
        except Exception:
            weekly.append(r)  # 无法解析的也保留

    return weekly


def _get_weekly_posters() -> list[dict]:
    """取本周生成的海报"""
    posters = st.session_state.get("posters", [])
    return posters[-10:]  # 最近 10 张


def _generate_ai_comment(weekly_refs: list[dict], ai_chat_func) -> str:
    """用 AMAX 给本周 5 段摘录写 1 句评语 (200 字内)

    Args:
        weekly_refs: 本周摘录列表
        ai_chat_func: core.amax_chat.chat 函数 (注入方便测试)

    Returns:
        AI 评语文本
    """
    if not weekly_refs:
        return "你本周还没写摘录 — 等你点亮几段, 我再来。"

    excerpts_text = "\n".join(
        f"《{r.get('book_title','未命名')}》: 「{r.get('excerpt_text','')[:50]}...」 ({r.get('emotion_label','')})"
        for r in weekly_refs[:5]
    )

    system = (
        "你是心灯精灵, 懂每个读者的灵魂。\n"
        "本周读者写了以下摘录, 请用一句话 (≤200 字) 写一句心灵评语, \n"
        "不堆砌, 不鸡汤, 不'你应该', 真正看见他们正在经历的。\n"
        "语气: 短句, 像树洞旁的朋友。"
    )
    user = f"本周摘录:\n{excerpts_text}\n\n请写一句评。"

    try:
        return ai_chat_func(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            character="心灯精灵",
            temperature=0.85,
            max_tokens=300,
        )
    except Exception as e:
        return f"本周, 你写了 {len(weekly_refs)} 段话 — 我在听, 我在等你。\n\n(AI 评暂不可用: {type(e).__name__})"


def render_weekly_html(
    reader_mbti: str = "—",
    reader_zodiac: str = "—",
    reader_level: str = "L1 初见者",
    weekly_refs: Optional[list[dict]] = None,
    weekly_posters: Optional[list[dict]] = None,
    ai_comment: str = "",
    week_number: int = 0,
) -> str:
    """渲染心灯周报 HTML (750xauto, 邮件宽度)

    Args:
        reader_mbti: 读者 MBTI
        reader_zodiac: 读者星座
        reader_level: 等级
        weekly_refs: 本周摘录列表
        weekly_posters: 本周海报列表 (v6.3.1)
        ai_comment: AI 评语
        week_number: 周编号 (e.g. 2026-W24)
    """
    weekly_refs = weekly_refs or []
    weekly_posters = weekly_posters or []

    # XSS 防御
    safe_mbti = html.escape(reader_mbti) or "—"
    safe_zodiac = html.escape(reader_zodiac) or "—"
    safe_level = html.escape(reader_level) or "L1 初见者"
    safe_ai = html.escape(ai_comment).replace("\n", "<br>")
    safe_week = html.escape(str(week_number)) or "0000"

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # 摘录卡片 HTML
    excerpt_cards = ""
    for i, r in enumerate(weekly_refs[:5], 1):
        safe_book = html.escape(r.get("book_title", "未命名"))
        safe_text = html.escape(r.get("excerpt_text", ""))[:120]
        safe_author = html.escape(r.get("author", ""))
        emotion_label = r.get("emotion_label", "resonance")
        emotion_cn = {
            "moved": "感动", "thinking": "思考", "resonance": "共鸣",
            "confused": "困惑", "disagree": "反对", "calm": "平静",
        }.get(emotion_label, "共鸣")

        excerpt_cards += f"""
        <div class="excerpt-card">
            <div class="excerpt-num">{i:02d}</div>
            <div class="excerpt-body">
                <div class="excerpt-quote">「{safe_text}」</div>
                <div class="excerpt-meta">
                    《{safe_book}》 {f'· {safe_author}' if safe_author else ''} · 🪔 {emotion_cn}
                </div>
            </div>
        </div>
        """

    # 海报链接 (v6.3.1)
    poster_section = ""
    if weekly_posters:
        poster_section = """
        <div class="section">
            <h2>🪔 你本周的金句海报</h2>
            <p class="section-sub">分享到朋友圈, 也许有 5 个陌生人会停下</p>
        </div>
        """
        for p in weekly_posters[:3]:
            safe_pbook = html.escape(p.get("book_title", "未命名"))
            safe_ptext = html.escape(p.get("text", ""))[:60]
            safe_pemotion = html.escape(p.get("emotion", "共鸣"))
            poster_section += f"""
            <div class="poster-card">
                <div class="poster-line">📖 {safe_pbook}</div>
                <div class="poster-line">「{safe_ptext}...」</div>
                <div class="poster-line">🪔 {safe_pemotion}</div>
            </div>
            """

    # 空周报: 兜底
    if not excerpt_cards:
        excerpt_cards = """
        <div class="empty-week">
            <div class="empty-icon">🪔</div>
            <div class="empty-text">你本周还没写摘录</div>
            <div class="empty-sub">去「写摘录」点亮一段, 下周我会在这里等你</div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>心灯周报 #{safe_week}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Noto Serif SC', 'Songti SC', serif;
    background: #f4ede0;
    color: #2a1f1a;
    line-height: 1.7;
  }}
  .container {{
    max-width: 700px;
    margin: 0 auto;
    background: #faf6ec;
  }}
  .header {{
    background: linear-gradient(135deg, #2a1f1a 0%, #4a2e1f 100%);
    color: #f4ede0;
    padding: 50px 40px;
    text-align: center;
  }}
  .logo {{ font-size: 50px; margin-bottom: 12px; }}
  .title {{ font-size: 32px; font-weight: 700; margin-bottom: 8px; letter-spacing: 0.05em; }}
  .subtitle {{ font-size: 16px; color: #d4a574; letter-spacing: 0.1em; }}
  .week-num {{
    display: inline-block;
    margin-top: 20px;
    padding: 6px 18px;
    background: rgba(212, 165, 116, 0.2);
    border: 1px solid rgba(212, 165, 116, 0.5);
    border-radius: 20px;
    font-size: 14px;
    color: #d4a574;
  }}
  .reader {{
    background: rgba(212, 165, 116, 0.1);
    padding: 20px 40px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(212, 165, 116, 0.2);
  }}
  .reader-label {{ font-size: 12px; color: #8b7355; text-transform: uppercase; letter-spacing: 0.15em; }}
  .reader-info {{ font-size: 18px; color: #2a1f1a; font-weight: 600; margin-top: 4px; }}
  .reader-info .accent {{ color: #c4694a; }}
  .date {{ font-size: 14px; color: #8b7355; }}
  .ai-comment {{
    background: linear-gradient(135deg, rgba(212, 165, 116, 0.15) 0%, rgba(196, 105, 74, 0.1) 100%);
    padding: 40px;
    margin: 30px 0;
    border-left: 4px solid #c4694a;
  }}
  .ai-comment h3 {{
    color: #c4694a;
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-bottom: 16px;
    font-weight: 600;
  }}
  .ai-comment p {{
    font-size: 20px;
    color: #1a1410;
    line-height: 1.7;
    font-style: italic;
  }}
  .section {{
    padding: 30px 40px 10px;
  }}
  .section h2 {{
    font-size: 24px;
    color: #2a1f1a;
    margin-bottom: 8px;
    font-weight: 600;
  }}
  .section-sub {{
    color: #8b7355;
    font-size: 14px;
    margin-bottom: 20px;
  }}
  .excerpt-card {{
    background: #f4ede0;
    border-radius: 8px;
    padding: 20px;
    margin: 12px 0;
    display: flex;
    gap: 16px;
    align-items: flex-start;
  }}
  .excerpt-num {{
    flex-shrink: 0;
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #d4a574 0%, #c4694a 100%);
    color: #f4ede0;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 700;
  }}
  .excerpt-body {{ flex: 1; }}
  .excerpt-quote {{
    font-size: 18px;
    color: #1a1410;
    font-style: italic;
    margin-bottom: 8px;
    line-height: 1.6;
  }}
  .excerpt-meta {{
    font-size: 13px;
    color: #6b5d4f;
  }}
  .poster-card {{
    background: #f4ede0;
    border-left: 3px solid #d4a574;
    padding: 16px 20px;
    margin: 8px 0;
    border-radius: 0 8px 8px 0;
  }}
  .poster-line {{
    font-size: 14px;
    color: #2a1f1a;
    line-height: 1.5;
  }}
  .empty-week {{
    text-align: center;
    padding: 60px 40px;
    color: #8b7355;
  }}
  .empty-icon {{ font-size: 60px; margin-bottom: 16px; opacity: 0.5; }}
  .empty-text {{ font-size: 22px; color: #6b5d4f; margin-bottom: 8px; }}
  .empty-sub {{ font-size: 14px; }}
  .footer {{
    background: #2a1f1a;
    color: #d4a574;
    padding: 40px;
    text-align: center;
    margin-top: 40px;
  }}
  .footer-logo {{ font-size: 30px; margin-bottom: 8px; }}
  .footer-text {{ font-size: 14px; margin-bottom: 4px; }}
  .footer-sub {{ font-size: 12px; color: #8b7355; margin-top: 16px; }}
  .cta {{
    display: inline-block;
    margin-top: 20px;
    padding: 12px 30px;
    background: linear-gradient(135deg, #d4a574 0%, #c4694a 100%);
    color: #f4ede0;
    text-decoration: none;
    border-radius: 30px;
    font-weight: 600;
    font-size: 16px;
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="logo">🪔</div>
    <div class="title">心灯周报</div>
    <div class="subtitle">你读过的字, 在陌生人那里被看见</div>
    <div class="week-num">第 #{safe_week} 期 · {today}</div>
  </div>

  <div class="reader">
    <div>
      <div class="reader-label">本周的你</div>
      <div class="reader-info">
        <span class="accent">{safe_mbti}</span> ·
        <span class="accent">{safe_zodiac}</span> ·
        {safe_level}
      </div>
    </div>
    <div class="date">📅 {today}</div>
  </div>

  <div class="ai-comment">
    <h3>🪔 心灯精灵 这周想跟你说</h3>
    <p>{safe_ai}</p>
  </div>

  <div class="section">
    <h2>📚 你本周点亮的 {len(weekly_refs)} 段</h2>
    <p class="section-sub">这些字, 在陌生人那里被看见了</p>
    {excerpt_cards}
  </div>

  {poster_section}

  <div class="footer">
    <div class="footer-logo">🪔</div>
    <div class="footer-text">心灯 · reading-fl</div>
    <div class="footer-text">你读过的字, 在陌生人那里被看见</div>
    <a class="cta" href="https://reading-fl.streamlit.app/">继续阅读 →</a>
    <div class="footer-sub">
      本周报由 AMAX 评语 + 心灯历史摘录生成
    </div>
  </div>
</div>
</body>
</html>"""


def get_week_number() -> int:
    """取今年第几周 (ISO 周编号)"""
    now = datetime.datetime.now()
    return now.isocalendar()[1]


def get_weekly_summary() -> dict:
    """周报摘要 (供周报页用)"""
    refs = _get_weekly_reflections()
    posters = _get_weekly_posters()
    week = get_week_number()

    return {
        "week": week,
        "ref_count": len(refs),
        "poster_count": len(posters),
        "emotion_breakdown": _emotion_breakdown(refs),
        "book_breakdown": _book_breakdown(refs),
    }


def _emotion_breakdown(refs: list[dict]) -> dict:
    """本周情绪分布"""
    breakdown = {}
    for r in refs:
        em = r.get("emotion_label", "unknown")
        breakdown[em] = breakdown.get(em, 0) + 1
    return breakdown


def _book_breakdown(refs: list[dict]) -> dict:
    """本周书分布"""
    breakdown = {}
    for r in refs:
        book = r.get("book_title", "未命名")
        breakdown[book] = breakdown.get(book, 0) + 1
    return breakdown
