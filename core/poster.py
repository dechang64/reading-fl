"""金句海报生成 — HTML 模板 + 截图

User 写完摘录, 一键生成可分享海报
- 顶: 📖《{book}》{chapter}
- 中: 「{text}」 (大字号, 行高 1.6)
- 底: 你的心灯画像 (MBTI + 等级)
- 角标: 🪔 心灯 · reading-fl

依赖:
- html2image: pip install html2image (需要 Chrome/Chromium)
- 或 weasyprint: pip install weasyprint (更稳, 但 Linux 编译麻烦)
- 退回: 直接显示 HTML (st.html), 不截图
"""
import html
import base64
import os
from typing import Optional


def render_poster_html(
    book_title: str,
    author: str = "",
    chapter: str = "",
    text: str = "",
    reader_mbti: str = "",
    reader_zodiac: str = "",
    reader_level: str = "L1 初见者",
    emotion: str = "共鸣",
    poster_id: str = "",
    is_ai_generated: bool = False,
) -> str:
    """渲染金句海报 HTML (750 x 1334 px, 适配朋友圈 3:4)

    Args:
        book_title: 书名
        author: 作者
        chapter: 章节 (可选)
        text: 摘录文字
        reader_mbti: 读者 MBTI (e.g. "INFJ")
        reader_zodiac: 读者星座 (e.g. "处女座")
        reader_level: 等级 (e.g. "L1 初见者")
        emotion: 情绪标签
        poster_id: 海报 ID (用于追踪分享)

    Returns:
        HTML 字符串
    """
    # XSS 防御: 转义所有用户输入
    safe_book = html.escape(book_title) or "未命名"
    safe_author = html.escape(author) or "未知"
    safe_chapter = html.escape(chapter) or ""
    safe_text = html.escape(text) or "此刻, 我读到了你"
    safe_mbti = html.escape(reader_mbti) or "—"
    safe_zodiac = html.escape(reader_zodiac) or "—"
    safe_level = html.escape(reader_level) or "L1 初见者"
    safe_emotion = html.escape(emotion) or "共鸣"

    chapter_html = f'<div class="chapter">· {safe_chapter} ·</div>' if safe_chapter else ""

    # v6.3.1 修: 动态字号 (防溢出)
    text_len = len(safe_text)
    if text_len <= 50:
        len_class = "len-short"
    elif text_len <= 100:
        len_class = "len-mid"
    elif text_len <= 180:
        len_class = "len-long"
    else:
        len_class = "len-xlong"

    # v6.3.1 修: AI 生成水印 (防误发假内容到朋友圈)
    ai_watermark_html = (
        '<div class="ai-watermark">🤖 AI 生成 — 请确认后再分享</div>'
        if is_ai_generated else ""
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>心灯 · {safe_book}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Noto Serif SC', 'Songti SC', 'STSong', serif;
    background: #f4ede0;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
  }}
  .poster {{
    width: 750px;
    height: 1334px;
    background: linear-gradient(165deg, #f7f1e3 0%, #e8d9b8 60%, #d4a574 100%);
    position: relative;
    overflow: hidden;
    box-shadow: 0 30px 80px rgba(0, 0, 0, 0.2);
  }}
  .poster::before {{
    content: '';
    position: absolute;
    top: -150px;
    right: -150px;
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(212, 165, 116, 0.3) 0%, transparent 70%);
    border-radius: 50%;
  }}
  .poster::after {{
    content: '';
    position: absolute;
    bottom: -200px;
    left: -100px;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(196, 105, 74, 0.2) 0%, transparent 70%);
    border-radius: 50%;
  }}
  .header {{
    padding: 80px 70px 50px;
    position: relative;
    z-index: 2;
  }}
  .book-title {{
    font-size: 38px;
    font-weight: 700;
    color: #2a1f1a;
    margin-bottom: 12px;
    letter-spacing: 0.04em;
  }}
  .book-meta {{
    font-size: 22px;
    color: #6b5d4f;
    letter-spacing: 0.05em;
  }}
  .chapter {{
    font-size: 20px;
    color: #8b7355;
    margin-top: 8px;
    font-style: italic;
  }}
  .quote-wrap {{
    padding: 60px 70px;
    position: relative;
    z-index: 2;
  }}
  .quote-mark {{
    font-size: 200px;
    color: rgba(196, 105, 74, 0.15);
    line-height: 0.8;
    position: absolute;
    top: -20px;
    left: 30px;
    font-family: serif;
  }}
  /* 动态字号: 文本越长字号越小, 防溢出 (v6.3.1 修) */
  .quote-text {{
    font-size: 56px;
    line-height: 1.7;
    color: #1a1410;
    font-weight: 500;
    letter-spacing: 0.02em;
    text-indent: 0;
    position: relative;
    z-index: 1;
    word-break: break-word;       /* 中文不切, 长句自动换行 */
    overflow-wrap: anywhere;      /* 强制换行, 防溢出 */
    max-width: 100%;
  }}
  .quote-text.len-short {{ font-size: 56px; }}    /* ≤ 50 字 */
  .quote-text.len-mid {{ font-size: 38px; }}      /* 51-100 字 */
  .quote-text.len-long {{ font-size: 26px; }}     /* 101-180 字 */
  .quote-text.len-xlong {{ font-size: 20px; line-height: 1.5; }}  /* > 180 字 */
  /* AI 水印 (v6.3.1 修: 防误发 AI 假内容) */
  .ai-watermark {{
    display: inline-block;
    margin-top: 24px;
    padding: 6px 14px;
    background: rgba(196, 105, 74, 0.85);
    color: #fff;
    font-size: 16px;
    font-weight: 600;
    border-radius: 16px;
    letter-spacing: 0.05em;
  }}
  .quote-text {{
    font-size: 56px;
    line-height: 1.7;
    color: #1a1410;
    font-weight: 500;
    letter-spacing: 0.02em;
    text-indent: 0;
    position: relative;
    z-index: 1;
  }}
  .quote-text {{
    /* v6.3.1 fix: 移到上面, 改为动态 class (len-short/mid/long/xlong) */
  }}
  .quote-text {{
    /* v6.3.1 fix: 移到上面, 改为动态 class (len-short/mid/long/xlong) */
  }}
  .emotion-tag {{
    display: inline-block;
    padding: 10px 24px;
    background: linear-gradient(135deg, #d4a574 0%, #c4694a 100%);
    color: #fff;
    font-size: 22px;
    border-radius: 30px;
    margin-top: 40px;
    font-weight: 600;
  }}
  .divider {{
    margin: 30px 70px;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(196, 105, 74, 0.3), transparent);
  }}
  .footer {{
    padding: 30px 70px 80px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    position: relative;
    z-index: 2;
  }}
  .reader {{
    flex: 1;
  }}
  .reader-label {{
    font-size: 18px;
    color: #8b7355;
    margin-bottom: 8px;
    letter-spacing: 0.1em;
  }}
  .reader-info {{
    font-size: 28px;
    color: #2a1f1a;
    font-weight: 600;
  }}
  .reader-info .mbti {{
    color: #c4694a;
    margin-right: 12px;
  }}
  .reader-info .zodiac {{
    color: #6b5d4f;
    margin-right: 12px;
  }}
  .reader-info .level {{
    color: #8b7355;
    font-size: 22px;
  }}
  .brand {{
    text-align: right;
  }}
  .brand-logo {{
    font-size: 40px;
    margin-bottom: 4px;
  }}
  .brand-text {{
    font-size: 18px;
    color: #6b5d4f;
    letter-spacing: 0.1em;
  }}
  .brand-url {{
    font-size: 14px;
    color: #8b7355;
    margin-top: 4px;
  }}
  .brand-cta {{
    font-size: 12px;
    color: #c4694a;
    margin-top: 6px;
    font-weight: 600;
    letter-spacing: 0.05em;
  }}
  .qr-placeholder {{
    width: 100px;
    height: 100px;
    background: #2a1f1a;
    border-radius: 8px;
    display: inline-block;
    margin-top: 8px;
    position: relative;
  }}
  .qr-placeholder::after {{
    content: '🪔';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: #d4a574;
    font-size: 36px;
  }}
  .poster-id {{
    position: absolute;
    bottom: 20px;
    left: 70px;
    font-size: 12px;
    color: #8b7355;
    opacity: 0.5;
    z-index: 2;
  }}
</style>
</head>
<body>
<div class="poster">
  <div class="header">
    <div class="book-title">📖 {safe_book}</div>
    <div class="book-meta">{safe_author}</div>
    {chapter_html}
  </div>
  <div class="quote-wrap">
    <div class="quote-mark">"</div>
    {ai_watermark_html}
    <div class="quote-text {len_class}">{safe_text}</div>
    <div class="emotion-tag">🪔 {safe_emotion}</div>
  </div>
  <div class="divider"></div>
  <div class="footer">
    <div class="reader">
      <div class="reader-label">点亮这段的人</div>
      <div class="reader-info">
        <span class="mbti">{safe_mbti}</span>
        <span class="zodiac">{safe_zodiac}</span>
        <span class="level">{safe_level}</span>
      </div>
    </div>
    <div class="brand">
      <div class="brand-logo">🪔</div>
      <div class="brand-text">心灯</div>
      <div class="brand-url">reading-fl</div>
      <div class="brand-cta">扫码加入 · 会员 ¥199/年</div>
      <div class="qr-placeholder"></div>
    </div>
  </div>
  <div class="poster-id">#{poster_id[:8] if poster_id else '0000'}</div>
</div>
</body>
</html>"""


def render_poster_preview_html(
    book_title: str,
    author: str = "",
    chapter: str = "",
    text: str = "",
    reader_mbti: str = "",
    reader_zodiac: str = "",
    reader_level: str = "L1 初见者",
    emotion: str = "共鸣",
    poster_id: str = "",
    is_ai_generated: bool = False,
) -> str:
    """在 streamlit 页面里渲染 (尺寸缩小到 375 x 667, 移动友好)

    跟 render_poster_html 唯一区别: width/height 减半, 适配手机预览
    """
    return render_poster_html(
        book_title=book_title,
        author=author,
        chapter=chapter,
        text=text,
        reader_mbti=reader_mbti,
        reader_zodiac=reader_zodiac,
        reader_level=reader_level,
        emotion=emotion,
        poster_id=poster_id,
        is_ai_generated=is_ai_generated,
    ).replace(
        "width: 750px;",
        "width: 375px;"
    ).replace(
        "height: 1334px;",
        "height: 667px;"
    ).replace(
        "font-size: 38px;",
        "font-size: 19px;"
    ).replace(
        "font-size: 22px;",
        "font-size: 11px;"
    ).replace(
        "font-size: 20px;",
        "font-size: 10px;"
    ).replace(
        "font-size: 56px;",
        "font-size: 28px;"
    ).replace(
        "font-size: 200px;",
        "font-size: 100px;"
    ).replace(
        "font-size: 18px;",
        "font-size: 9px;"
    ).replace(
        "font-size: 28px;",
        "font-size: 14px;"
    ).replace(
        "font-size: 40px;",
        "font-size: 20px;"
    ).replace(
        "font-size: 12px;",
        "font-size: 6px;"
    ).replace(
        "font-size: 16px;",
        "font-size: 8px;"
    )


def poster_to_data_url(html_content: str) -> str:
    """HTML 转 data URL (用于 st.html 嵌入或分享)"""
    b64 = base64.b64encode(html_content.encode("utf-8")).decode("ascii")
    return f"data:text/html;base64,{b64}"


def save_poster_to_file(
    html_content: str,
    output_path: str = "/tmp/poster.png",
    width: int = 750,
    height: int = 1334,
) -> Optional[str]:
    """HTML 转 PNG (需要 html2image + Chrome)

    Returns:
        PNG 文件路径, 失败返回 None
    """
    try:
        from html2image import Html2Image

        hti = Html2Image(
            output_path=os.path.dirname(output_path) or "/tmp",
            size=(width, height),
            custom_flags=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        filename = os.path.basename(output_path)
        hti.screenshot(
            html_str=html_content,
            save_as=filename,
        )
        full_path = os.path.join(os.path.dirname(output_path) or "/tmp", filename)
        if os.path.exists(full_path):
            return full_path
    except ImportError:
        pass
    except Exception:
        pass
    return None
