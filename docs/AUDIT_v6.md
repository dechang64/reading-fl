# Reading-FL v6 代码审计报告 (2026-06-11)

> **审计方法**: spawn `general` agent 深度审计 12 个核心文件 (app.py + 8 pages + core/amax_chat.py + core/points.py + .streamlit/config.toml + data/reflection.py), 辅以 30+ 处的 grep + Python 反射验证 API 签名.
> **审计触发**: 用户在 iPhone 看 app 主体内容整片黑屏, 我先瞎猜 3 次错 (夸克浏览器 / webview CSS / sidebar 颜色), 用户说"好好审计代码定能发现问题"点醒.
> **审计员视角**: 资深 Python + Streamlit + 移动 Web 开发者.

---

## 总评

| 维度 | 分数 | 说明 |
|------|------|------|
| **mobile 适配** | 5/10 | 首页 + 摘录页 + 精灵页做了 16px/44px, 其他 5 页缺失; 夸克/UC/微信 fallback 实测无效; 没有 viewport meta 自检; 没有 `-webkit-tap-highlight-color` |
| **安全性** | 3/10 → 7/10 (修完 5 P0) | 至少 4 处用户输入直接进 `st.html(...)` f-string (XSS P0); CSRF/XSRF 显式关闭 (`config.toml:14-15`); mock 响应含 raw LLM 输出泄漏 |
| **性能** | 6/10 | 9 个页面 8 套 CSS 重复注入; subprocess 60s + `@st.cache_data` 命中率低; `st.rerun()` 在 chip toggle 高频触发 |
| **可维护性** | 5/10 | 每个 page 写 `set_page_config` (DRY 违反); 共用 CSS 复制 8 份; `st.html(..., unsafe_allow_html=True)` 是 silent bug; `EMOTION_LABELS_CN` dict 在 5 个文件里重复定义 |
| **设计哲学执行** | 8/10 | 暗色 + 暖金统一; `privacy-strip` 视觉强; federation 叙事清晰; `scripts/demo.py` 单文件 E2E 跑通; `audit/chain.py` 实现简洁 |
| **总体** | 5.5/10 → 7.5/10 (修完 P0) | 视觉/产品思路 8/10, 工程实现 4/10. P0 修了可以到 7/10, P1 修了可以到 8.5/10 |

---

## P0 紧急 (5 项, **已全部修复** by `c637310`)

### #1 + #10 XSS — 用户输入直接渲染为 HTML 🔴

**Evidence**:
- `app.py:728-731` — `st.html(f"""<div class="archive-quote">「{r.excerpt.text}」</div>...《{r.excerpt.book_title}》""")`
- `pages/1_excerpt.py:307` — `r.reflection_text` 拼 f-string
- `pages/3_archive.py:174` — 同样模式
- **`pages/4_genie.py:144,146` — 最危险** `st.html(f'<div class="user-msg">{msg["content"]}</div>')` 精灵对话用户输入直接渲染, 攻击者写一段 `<img src=x onerror=alert(document.cookie)>` 就能偷所有用户 session

**修法** (`c637310`):
```python
import html as _html  # XSS defense
safe_text = _html.escape(r.excerpt.text)
safe_title = _html.escape(r.excerpt.book_title)
st.markdown(f"""<div class="archive-quote">「{safe_text}」</div>""", unsafe_allow_html=True)
```

修改文件: `app.py`, `pages/1_excerpt.py`, `pages/3_archive.py`, `pages/4_genie.py`, `pages/2_resonance.py` (兜底).

---

### #2 浏览器检测脚本静默失效 🔴

**Evidence**: `app.py:576-605`
```python
st.html(r"""
<div id="browser-warn" ...>...</div>
<script>
(function() {
    var ua = navigator.userAgent;
    ...
})();
</script>
""")
```

**真实原因**: `st.html` 默认 `unsafe_allow_javascript=False` → Streamlit **服务端剥 `<script>` 标签**. 验证方法:
```python
import streamlit
import inspect
print(inspect.signature(streamlit.html))
# (body, *, width='stretch', unsafe_allow_javascript=False) -> DeltaGenerator
```

`unsafe_allow_html` 参数**根本不存在**, 但被 `**kwargs` 默默丢弃. 这 30 行 UA 检测是死代码.

**修法** (`c637310`): 删 30 行, 改用 1 行 `st.markdown` 静态提示. 简单, 不假装"在检测".

```python
st.markdown("""
<div style="background: linear-gradient(135deg, #c4694a 0%, #d4a574 100%);
    color: #0d0d0f; padding: 0.6rem 0.9rem; border-radius: 8px; margin: 0 0 1rem 0;
    font-size: 0.85rem; font-weight: 500; text-align: center;">
    🪔 <b>建议用 Safari / Chrome 打开</b> — 其他浏览器可能有渲染问题
</div>
""", unsafe_allow_html=True)
```

---

### #3 Streamlit Cloud 上 `subprocess.run` 大概率不可用 🔴

**Evidence**: `pages/2_resonance.py:65-72`
```python
@st.cache_data(show_spinner=False)
def get_resonance():
    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/demo.py", "--quick"],
        capture_output=True, text=True, timeout=60,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
```

- share.streamlit.io 在容器内跑, subprocess **可能被 seccomp/sandbox 阻止**
- 即使能跑, `timeout=60` + 8 个 widget 触发 8 次 cache miss = 8 次重 fork Python
- `with st.spinner("")` 空消息让用户对着 60 秒空转

**修法** (`c637310`):
1. 改 `scripts/demo.py` 让 `run_demo(quick=True)` **return top_resonant 数据列表** (含 score, text, n_refs, n_readers, n_guilds)
2. `2_resonance.py` 改:
```python
@st.cache_data(show_spinner=False)
def get_resonance():
    from scripts.demo import run_demo
    rows = run_demo(quick=True) or []
    rows.sort(key=lambda x: -x["score"])
    return rows

with st.spinner("段友正在找共鸣..."):
    rows = get_resonance()
```

顺带修 #16 `with st.spinner("")` 空消息.

---

### #26 XSRF/CORS 显式关闭 🔴

**Evidence**: `.streamlit/config.toml:14-15`
```toml
[server]
maxUploadSize =5
enableXsrfProtection = false
enableCORS = false
```

**真实原因**: share.streamlit.io 默认 `enableXsrfProtection=true` + `enableCORS=true`, 自己写出来覆盖默认**等于显式声明关掉**. XSRF 关闭意味着表单提交无 token 验证. 配合 #1 的 XSS, 可形成 CSRF 链.

**修法** (`c637310`): 删两行, 用 streamlit cloud 默认.

```toml
[server]
maxUploadSize =5
```

---

### #9 `st.html(..., unsafe_allow_html=True)` silent bug 🟡 (P1 误标 P0)

**Evidence**: 24 处 `st.html(...)` 调用中, 部分带 `unsafe_allow_html=True` (没作用, 签名是 `(body, *, width, unsafe_allow_javascript)`).

**修法** (`c637310` 已覆盖): #1/#2/#3 修复时已经把那 5 处 `st.html` 改成 `st.markdown(..., unsafe_allow_html=True)`. 剩余 24 处 st.html 调用本身是合法的 (st.html 本来就渲染 HTML), 但**风格上**应该统一成 st.markdown.

---

## P1 重要 (未修, 列为 backlog)

### #4 重复 `set_page_config` — 已知 Streamlit 行为陷阱

**Evidence**:
- `app.py:29` — `st.set_page_config(...)`
- `pages/1_excerpt.py:13-18`、`pages/2_resonance.py:8`、`pages/3_archive.py:10`、`pages/4_genie.py:10`、`pages/5_for_authors.py:17`、`pages/6_book_recommend.py:17`、`pages/7_architecture.py:6`、`pages/8_points.py:10` — 每个 page 都调一次

Streamlit 1.40+ 的 multipage app 实际**只认 app.py 的 `set_page_config`** (page 里的会被忽略或抛 warning). 每个 page 都调一次虽然不致命, 但:
- 启动顺序依赖 — app.py 必须先 import
- 维护噩梦 — 改 page title 要改 9 处
- 已知 issue: Streamlit ≥1.28 在某些 race 下会 warning `set_page_config() is called more than once`

**修法**:
- 把 `set_page_config` 只放在 `app.py`
- 子 page 顶部加 `if __name__ == "__main__":` 风格保护, 或干脆删掉子 page 的调用

---

### #5 `<div>` 拆分到 `st.markdown` + `st.html` 边界 → DOM 嵌套错乱

**Evidence**: `pages/3_archive.py:163, 171-179, 181`
```python
st.markdown(f'<div class="timeline-day"><div class="timeline-date">{date_text} · {day}</div>', unsafe_allow_html=True)
# ... loop ...
st.html(f"""
<div class="excerpt-card">  <!-- 这里会被 Streamlit 嵌入自己的 wrapper -->
    ...
</div>
""")
st.markdown('</div>', unsafe_allow_html=True)  # 这个 </div> 可能匹配错地方
```
Streamlit 在每个 component 之间插入自己的 wrapper div, 导致:
- 嵌套结构错乱 (浏览器自动修复 → layout 飘)
- 用户嵌入 HTML 的 XSS 防御被弱化 (因 `</div>` 闭合不严, 可能让攻击者注入块级元素)

**修法**: 整个 timeline block 用单次 `st.html` 调用, 或在 CSS 层用 `>` 直接子选择器, 不依赖嵌套.

---

### #6 16px / 44px tap-area 移动适配在 5/8 个页面缺失

**Evidence**:
- `app.py:531-533` 设了 `min-height: 44px` + 16px textarea — 仅首页
- `pages/1_excerpt.py:72-74` + `pages/4_genie.py:77-78` 设了
- `pages/2_resonance.py` / `pages/3_archive.py` / `pages/5_for_authors.py` / `pages/6_book_recommend.py` / `pages/7_architecture.py` / `pages/8_points.py` — **没有** `@media (max-width: 640px) { button min-height: 44px }`

后果: 用户在共鸣墙/书灯/作者页点 button, 命中区域 < 44px, 容易误触. Apple HIG / Material Design 都要求 44px.

**修法**: 抽公共 CSS 到 `assets/mobile.css`, 所有页面 `st.html` 引用; 或在 `app.py` 加载一次.

---

### #7 CSS 重复 — ~30 行 fallback 块 × 8 文件 = 240 行 boilerplate

**Evidence**: 8 个 page 文件 (1_excerpt:81, 2_resonance:52, 3_archive:75, 4_genie:85, 5_for_authors:178, 6_book_recommend:160, 7_architecture:55, 8_points:35) 各自复制了
```python
st.markdown('<style>\n/* 兼容老 webview 的深 fallback */\nhtml, body, .stApp, ...\n</style>', unsafe_allow_html=True)
```

**修法**:
- 抽到 `assets/webview_fallback.css`, 所有 page `st.markdown(open(f).read(), unsafe_allow_html=True)`
- 或注入到 `app.py` 一次 (Streamlit 会持久化 CSS 到 SPA 内)

---

### #8 主题/暗色 fallback 双重定义

**Evidence**:
- `app.py:38-85` (深 fallback) + `app.py:87-104` (重复一次, 几乎是 copy-paste) + `app.py:109-540` (主主题)
- 子 page 又有自己的 `:root { --bg: ... }` (例如 `pages/1_excerpt.py:23-24`), 且子 page 的 fallback 又重新定义所有变量

`app.py:38-85` 和 `app.py:87-104` 几乎是完全重复的 sidebar 按钮高亮 CSS.

**修法**: 删除 `app.py:87-104` (整块), 或在 `app.py:38-85` 之后加注释 "this block needed on every page" 抽公共.

---

### #11 积分刷新清零

**Evidence**: `core/points.py:43-50, 68`
- `init_points()` 在 `app.py:549` + `pages/8_points.py:39` 各调一次 (幂等, OK)
- `points_history` 每次 append 然后 `-50:` 截断 (OK)
- 但 `points_total` **只在 `st.session_state`**, 刷新页面就清零. **用户积累的 200 积分刷新即丢**

**修法**:
- 用 `st.session_state` 持久化 (用 cookie 或 query param)
- 或接 Streamlit `st.experimental_user` / `st.user` (新版) 持久化

---

### #12 截屏识别无 MIME/大小二次校验

**Evidence**: `pages/1_excerpt.py:93-98, 107`
- Streamlit `st.file_uploader` 自带 5MB server 限制 (config.toml:13) ✓
- 但 `shot.read()` 之后直接 `base64.b64encode` 进 AMAX payload — **没验证 magic bytes**
- 用户上传 `.svg` / `.html` (用 type=["png","jpg","jpeg","webp"] 过滤了扩展名, OK) 但可绕过
- `core/amax_chat.py:170` 直接 encode — 风险: 恶意大尺寸图 (5MB × 1.33 base64 = 6.6MB) 进 AMAX 请求体, 失败时 60s timeout 锁住 UI

**修法**:
- 加 `if len(image_bytes) > 2_000_000: return {"error": "图片太大"}` 二次校验
- 用 Pillow 验证 `Image.open(io.BytesIO(image_bytes)).verify()` (需加 requirements)

---

### #13 AMAX API key 鉴权错误信息暴露

**Evidence**: `core/amax_chat.py:108`
```python
return f"💭 *(AI 鉴权失败 HTTP {code} — 请检查 Secrets 里的 AMAX_API_KEY)*\n\n..."
```
返给用户的错误信息是 OK 的, 但**失败时调用了 `_mock_response` (line 109)**, 把 mock 数据和真错误一起 render 到 `st.caption` 或 `st.html`. 在 `pages/4_genie.py:181` 是 `st.caption(f"🪔 {amax_error[:120]}")` — OK, escape 过.

但在 AMAX 返回 JSON 解析失败时 (`core/amax_chat.py:246-249`), `raw_text: content[:500]` 也被返到 page → `pages/1_excerpt.py:111` `st.caption(result["hint"])` — 暴露 LLM 完整回复(含可能的 system prompt leak)给用户. **PII / IP 风险**.

**修法**: `raw_text` 写到 server log, 只返 `"AI 暂时无法理解这张图"` 给用户

---

### #14 AMAX 错误信息再渲染到 `st.html` (跨页 XSS 加深)

**Evidence**: `pages/1_excerpt.py:108-111`
```python
if "error" in result:
    st.warning(f"⚠️ {result['error']}")  # st.warning 内部 st.markdown + escape ✓
    if "hint" in result:
        st.caption(result["hint"])      # caption 是 st.markdown + escape ✓
    if "mock_paragraph" in result:
        st.info(f"**示例结果**(没真识别):{result.get('mock_book_title','')} — {result['mock_paragraph']}")
```
`st.warning` / `st.caption` / `st.info` 自动 escape, **目前安全**. 但 `result["error"]` 来自 AMAX 的 HTTP error body (line 252 `f"AMAX HTTP {code}"` — OK), 或 LLM 乱回 (line 248 `raw_text: content[:500]`) — 风险中等. **#1 的修复要包含这条**

---

### #15 `import` 在函数内 + Python 启动慢

**Evidence**:
- `app.py:226` — `from data.reflection import BookExcerpt, Reflection` 在 button 回调里
- `pages/1_excerpt.py:106, 226, 278` — 同样的 import-in-function 模式
- `pages/2_resonance.py:67, 451` — 同上

`import` 在 hot path 不影响性能 (Python 缓存), 但**增加冷启动延迟**. share.streamlit.io 冷启动 1-3 秒, 这些 import 加起来可能 500ms+.

**修法**: 顶部 `from core.amax_chat import detect_excerpt_from_image` 等

---

### #17 `st.rerun()` 高频触发

**Evidence**: `pages/6_book_recommend.py:254`
```python
if st.button(...):
    if is_active: ...
    else: st.session_state.user_emotions.append(name)
    st.rerun()  # 每次点击都全页重渲
```
8 个情绪 chip × 每次 rerun = 8 次 widget 重渲. 移动端体验卡顿.

**修法**:
- 用 `st.feedback` / `st.segmented_control` 替代 (Streamlit 1.40+)
- 或用 `on_click` callback (`st.button(..., on_click=toggle_emo, args=(name,))`) 避免 rerun

---

### #18 `scripts/demo.py` 输出的解析脆弱 (✅ `c637310` 已缓解)

**Evidence**: `pages/2_resonance.py:74-101` — 用 string matching 解析 `Step 5: Resonance` → `[0.XXX] "text" (n refs, n readers, n campuses)`
- 任何对 `scripts/demo.py:329, 347, 348-349` print 格式的微调都会让共鸣墙空白
- line 84: `line.split('"')[1]` 假设 text 用 `"` 包, 但 demo.py:347 确实用 `"..."`, OK
- 但 line 85 `stats = line[line.rfind("("):]` 用 `rfind` 抓括号, 如果有 nested parenthesis 就错了

**修法**: **已采用** — `c637310` 让 `run_demo()` return `top_resonant` 数据列表, page 直接用结构化数据. 不再 string parse.

---

## P2 可优化

### #19 `audit/chain.py` 缺幂等

**Evidence**: `audit/chain.py:60-68, 100` — 每次 `add_reflection` 都 `mine(difficulty=2)`, CPU 浪费. 如果 batch 100 条反射 → 100 次 PoW. 注释说是 "for demo purposes", **生产应该关掉或用真区块链**.

---

### #20 `data/reflection.py:96` `emotion_score` 二值

```python
emotion_score = 0.3 if self.emotion_label == "calm" else 0.7
```
"感动"和"愤怒"得同样分, 语义错. 应该用真实 `emotion_vector` 连续值.

---

### #21 `data/reflection.py:171` 排除整数的反作弊太脆

```python
if self.total_duration_sec == int(self.total_duration_sec):
    return False
```
只要 `120.0` vs `120.5` — 攻击者写 `120.5` 就过. **没用**. 改用 `duration % 1 < 0.1` 之类的统计分布检查.

---

### #22 `core/amax_chat.py:233-249` JSON 解析 regex 多层

```python
m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
...
m2 = re.search(r"\{[^{}]*\{.*?\}[^{}]*\}", content, re.DOTALL)
```
`\{.*?\}` 非贪婪在嵌套 JSON 上会错位. LLM 输出嵌套 `{"paragraph": "包含 {字}"}` 时必死.

**修法**: 用 `json_repair` 库 或 OpenAI tool calling / structured output

---

### #23 `pages/1_excerpt.py:230-231` `reader_id` 用时间戳

```python
st.session_state.reader_id = hashlib.sha256(
    f"reader_{datetime.datetime.now().isoformat()}".encode()
).hexdigest()[:12]
```
**每次刷新都给新 ID** — "我的书灯"页面永远空 (因为 session_state.reflections 也清). 这就是为什么 `pages/3_archive.py:84-87` 写了"还没有记录"的回退.

**修法**: 用 `st.query_params` 或 client-side cookie 持久化, 或 accept 现状(本地 demo)但在 README 写明

---

### #24 `pages/6_book_recommend.py:185-187` 装饰用 mbti-chip 不可点

```python
mbti_html += f'<span class="mbti-chip {active}" id="mbti-{mbti}" data-mbti="{mbti}">{mbti}</span>'
st.html(mbti_html)  # 纯展示
# 然后下面又来一个 st.selectbox 当真功能 ← UX 困惑
```
两个 UI 控件实现同一目的, 用户不知道哪个是真的.

**修法**: 只留 selectbox, 或用 `st.pills` (Streamlit 1.40+)

---

### #25 `pages/3_archive.py:163-181` 关闭 `</div>` 用 `st.markdown('</div>')`

最小问题但非常奇怪: 用 `st.markdown` 只为了闭合一个 `<div>`. 可以直接合并到 `st.html` 块开头或干脆 CSS 用 `::after` 伪元素.

---

### #26 XSRF/CORS 显式 false (✅ `c637310` 已修)

---

### #27 `core/amax_chat.py:25-33` 缺 `try/except` 包 `st.secrets.get`

```python
api_key = st.secrets.get("AMAX_API_KEY", "")
```
`st.secrets.get` 在没 secrets.toml 时**直接抛 FileNotFoundError**, 虽然有 `except Exception`, 但 **ImportError/AttributeError 都被吃**, debug 时找不到根因.

**修法**:
```python
try:
    api_key = st.secrets.get("AMAX_API_KEY", "") or ""
except (FileNotFoundError, Exception):
    api_key = os.environ.get("AMAX_API_KEY", "")
```

---

### #28 `pages/1_excerpt.py:62-66` `.archive-card` CSS class 与 `app.py:447-465` 重复

两个 `.archive-card` 定义, 在不同 page 上下文里表现可能微差(取决于 `:root` 变量解析顺序).

**修法**: 抽公共 CSS

---

### #29 性能: 每次 page render 都 re-inject 50+ 行 CSS

8 个 page × 每个 50 行 CSS × 每次 rerun = 大量重复 DOM 注入. 移动端 parser 时间.

**修法**: `app.py` 一次 inject, 或在 `.streamlit/config.toml` 配 `[theme] customCss = "..."`

---

### #30 `requirements.txt:2` `streamlit>=1.40.0`

没有 upper bound, Streamlit 2.0 出来时 `st.html` API 可能变. 钉死 `streamlit==1.58.0` 或 `>=1.40,<2.0`

---

### #31 `app.py:752-761` Guild stats 是硬编码 mock

```python
GUILD_STATS = {
    "guild_夜读派": {"readers": 60, ...},
    ...
}
```
不要紧, 但前面 `init_points()` + sidebar + resonance wall 都强调"真实数据", 这里硬编码会让用户怀疑整套系统.

---

## 推荐修复顺序

1. **✅ 立刻 (今天)**: #1 (XSS in 4_genie.py) — `c637310` 完成
2. **✅ 立刻**: #2 (browser-warn script dead) — `c637310` 完成
3. **✅ 今天**: #3 (subprocess → import) — `c637310` 完成
4. **✅ 今天**: #26 (XSRF) — `c637310` 完成
5. **✅ 今天**: #9 (st.html 误用 unsafe_allow_html) — `c637310` 完成
6. **本周**: #4 (重复 set_page_config) + #6 (5/8 页面缺 44px) + #5 (3_archive.py 嵌套错乱)
7. **本周**: #7 + #8 (CSS DRY) — 抽 `assets/mobile.css` + `assets/webview_fallback.css`
8. **下周**: #11 积分持久化 + #23 reader_id cookie 持久化 (需要后端)
9. **有空**: P2 全清单

---

## 经验教训 (Memory 已存)

1. **不要瞎猜 webview / browser bug** — 截图复现再修. 看到"黑屏"先截一张 iPhone UA 截图看看到底黑的是什么.
2. **Streamlit + 用户输入 XSS 必查** — `import html as _html; _html.escape(field)` 三件套.
3. **Streamlit `st.html` API 没有 `unsafe_allow_html` 参数** — silent bug, 传了被 `**kwargs` 默默丢弃.
4. **审计永远是写完代码后第一步** — 用户"好好审计代码"一句话点醒, 否则永远只盯着表面 bug 改.

---

**审计完成时间**: 2026-06-11 05:30 EDT
**审计员**: `general` agent
**审计结果**: P0 5 项已修 (commit `c637310`); P1 9 项 + P2 12 项待修.
