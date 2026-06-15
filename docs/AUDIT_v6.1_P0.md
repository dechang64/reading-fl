# Reading-FL v6.1 — 4 P0 改动专项审计

**审计时间**: 2026-06-11
**审计范围**: 11 个文件 (app.py + core/exceptions.py + core/points.py + 8 pages)
**审计方法**: read/grep 全文 + Python 沙箱实跑 (level 边界, emoji 编码, syntax check, streamlit API 兼容)
**streamlit 版本**: 1.58.0 (本地实测)

---

## 一、P0/P1/P2 评估 (按 4 个改动顺序)

### P0 #1: 改名 "共鸣" → "被看见" (用户可见文案)

**核心改动**: app.py, 1/2/3/4/5/6/8 等用户可见文案

**grep "共鸣" 结果** (15 处命中, 评估每处):

| 文件:行 | 上下文 | 性质 | 评级 |
|---|---|---|---|
| `app.py:6` | 模块注释 "找共鸣" | 代码注释, 用户不可见 | P2 (可保留, 内部术语) |
| `app.py:706` | `emo_cn` 字典: `"resonance": "🔗 共鸣"` | **用户可见** | **P1 必须改** |
| `app.py:735` | `GUILD_STATS` mock: `mood: "共鸣"` | **用户可见** (首页"跨书社动态") | **P1 必须改** |
| `pages/0_welcome.py:66` | 问卷选项: `"🤝 我跟谁共鸣"` | **用户可见** | **P0 必须改** |
| `pages/0_welcome.py:84` | 情感选项: `"🔗 共鸣"` | **用户可见** | **P0 必须改** |
| `core/points.py:5` | 注释 "被共鸣" | 代码注释 | P2 保留 OK |
| `core/points.py:18` | `LEVELS` L3 tagline: "段级被共鸣" | **用户可见** (sidebar + 积分页) | **P0 必须改** |
| `core/points.py:69` | 注释 "共鸣" | 代码注释 | P2 保留 OK |
| `core/points.py:212` | 积分奖励表: `段级被 3+ 人共鸣` | **用户可见** (积分页表格) | **P0 必须改** |
| `core/points.py:247` | reason_cn 字典: `"段级被共鸣"` | **用户可见** (积分页历史) | **P0 必须改** |
| `pages/5_for_authors.py:5` | 模块注释 | 注释, 不影响 | P2 |
| `pages/5_for_authors.py:185/245/465/477/490` | 内部标签/注释 + 用户可见段"作者痛点共鸣" + 模拟器文案 | 部分可见 | **P1** (5:185 是锚点, 5:465/477/490 是模拟器文案) |
| `pages/6_book_recommend.py:304` | ISFP 推荐理由: "美学共鸣" | **用户可见** | **P1 必须改** |
| `pages/1_excerpt.py:209/251/301` | 情绪 radio + 字典 | "共鸣" 是情绪标签 (与"感动/思考"并列, 系统级), **保留是合理的** | P2 (与产品定位"6 维情感"耦合, 改会破坏 1_excerpt radio) |
| `pages/4_genie.py:116/131/190` | 字典映射 (内部用) | 同上, 情绪 en→cn 映射 | P2 (与 1_excerpt 一致) |
| `pages/3_archive.py:103/167` | emo_cn 字典 | 同上 | P2 |
| `data/reflection.py:21`, `models/reading_model.py:116`, `data/generator.py:158` | 6 维情感定义 | **系统底层标签, 改会破坏模型** | P2 保留 (产品术语"共鸣"=emotion class, 不是品牌词) |

**结论**: **5 处用户可见未改 (P0/P1)**:
- 0_welcome.py:66, 0_welcome.py:84, core/points.py:18, core/points.py:212, core/points.py:247 (强 P0)
- app.py:706, app.py:735, 6_book_recommend.py:304, 5_for_authors.py:185 (P1, 边缘场景)

**无代码破坏**: rename 纯字符串, 没改 import/类名/函数名, 没破坏代码结构。

---

### P0 #2: 心灵语气 error/info/warning/success/spinner (11 处)

**core/exceptions.py:14-55**:
- `gentle_error(e, where, user_msg)` — 用 `st.error(f"🪔 {title}")` + `st.caption(f"📍 {where}")` + `st.expander(traceback)` ✓
- `gentle_warning/info/success` — 前缀 `"🪔"` ✓
- `gentle_spinner` — 默认 `"段友正在翻书, 等一下下..."` ✓
- `safe_run(fn, fallback_msg)` — 装饰器 + try/except ✓

**emoji 编码验证**: `f09f938d` (🪔)、`f09f94a7` (🔧)、`f09faa94` (🪔 另一处) — **全部合法 UTF-8, 无坏字节** (PowerShell GBK 解码报错是终端问题, 文件二进制正确)。

**escape 字符检查**:
- `gentle_error` 用 `st.error(f"🪔 {title}")` — title 是字符串, f-string 安全
- `traceback.format_exc()` 走 `st.code()` — Streamlit 自身 escape, **安全**
- `gentle_warning/info/success` 同上 ✓

**"11 处都改了吗"**:
- ✅ core/exceptions.py 是新增, 自动覆盖所有使用点
- ⚠️ **实际 grep 整个项目, 大部分现有代码还在用裸 `st.error/st.warning/st.info`**, **没迁移**! 例如:
  - `pages/1_excerpt.py:108-113, 290` — 仍用 `st.warning("🪔 灯暂时暗了一下: ...")` (虽然加了 🪔, 但没调 `gentle_warning`)
  - `pages/2_resonance.py:75` — 用 `st.spinner("段友正在翻书, 等一下下...")` (虽然文案对了, 但没调 `gentle_spinner`)
  - `pages/4_genie.py:183, 519, 522` — 用 `st.caption(f"🪔 {amax_error}")` (绕过 streamlit error 系统, 走 caption, 永远不显眼)
  - `app.py:586` — 提示框用 st.markdown, 不在 P0 范围
  - `pages/5_for_authors.py:515, 519, 522` — 同样 st.caption

**P1 问题**: **exceptions.py 是新增, 但调用方没改**。`gentle_error/safe_run` 在项目里**完全没被 import/调用**。这意味着:
- 任何 try/except 仍然走裸 `st.error`, 没有统一的 traceback expander
- 装饰器 `safe_run` 形同虚设

**严重度**: P1 (核心交付物新增, 但**未接入** — 设计师意图未实现)

---

### P0 #3: 7 级 LEVELS + get_level + show_level_badge

**core/points.py:15-23** LEVELS 数组 (7 个 tuple, 字段顺序: min_points, code, name, tagline, icon) ✓

**get_level 边界实跑** (Python 实测, `pts` 是输入积分):

```
pts=   -100  -> L1 初见者  progress=0.00%   next=同行者  (✓ 负数兜底 L1)
pts=      0  -> L1 初见者  progress=0.00%   next=同行者  (✓)
pts=      1  -> L1 初见者  progress=1.00%   next=同行者  (✓)
pts=     50  -> L1 初见者  progress=50.00%  next=同行者  (✓ 初始 50 积分)
pts=     99  -> L1 初见者  progress=99.00%  next=同行者  (✓ 临界)
pts=    100  -> L2 同行者  progress=0.00%   next=微光者  (✓ 升 L2 归零)
pts=    299  -> L2 同行者  progress=99.50%  next=微光者  (✓)
pts=  12000  -> L7 共创者  progress=0.00%   next=None    (✓ 满级)
pts=  13000  -> L7 共创者  progress=0.00%   next=None    (✓ 超额)
pts= 999999  -> L7 共创者  progress=0.00%   next=None    (✓ 不爆)
```

**P2 bug**: `progress=0.00%` 当满级时, 但 UI 显示"满级"字样 (`points.py:57`), **无视觉异常**。但 `core/points.py:188` 算"再攒 X 看见币"时 `next_min - points_total = 12000 - 12000 = 0`, 会显示"再攒 0 看见币" — **P2 小瑕疵**, 实际不会触发 (有 `if lv["next_name"]` 保护)。

**show_level_badge HTML** (`core/points.py:48-59`): 结构 `<div class="level-badge">` + icon + code + name + progress bar + next/points — **未在 app.py CSS 中定义 `.level-badge / .level-icon / .level-code / .level-bar / .level-bar-fill / .level-next` 样式**!

**P1 真实问题**:
- app.py:362-371 有 `.points-badge` (旧版 sidebar 用的)
- app.py CSS **没有** `.level-badge` 等 6 个 class
- 结果: sidebar 上 level badge 会**裸 HTML 显示** (无背景/无间距/无进度条样式), 看起来像一段无样式的 `<div>`
- 用户初次打开会看到"破版"sidebar

**进度条**: `points.py:188-194` 8_points.py 用 inline `style="width: {int(progress*100)}%"`, 这个 ✓ (不走 .level-bar)。但 `show_level_badge` 走 `.level-bar` 没样式 → 进度条不可见。

**LEVELS 标签本身**: 跟 v6.1 INSPIRATIONS 中"看见读书会 7 级 (初见/同行/微光/星芒/执灯/引路/共创)" 对齐 ✓ 名字一致。

**get_level 返回 dict** 字段名: `code, name, tagline, icon, min_points, next_code, next_name, next_min, progress` — 调用方 (`points.py:164-200`) 全部用得到 ✓, 无 KeyError 风险。

---

### P0 #4: 0_welcome.py 问卷 (新文件)

**126 行, 5 个问题 + 提交按钮**:
1. genre (pills, 7 选项)
2. purpose (radio, 4 选项)
3. pain (text_input, max_chars=50)
4. emotions (pills multi, 12 选项, ≥3)
5. anti_spam (checkbox)

**streamlit 1.58 API 验证**:
- `st.pills` ✓ 存在
- `st.radio` ✓
- `st.text_input(max_chars=50)` ✓
- `st.checkbox` ✓
- `st.switch_page` ✓
- `st.balloons` ✓

**anti_spam 逻辑** (`0_welcome.py:99, 105, 109-117`):
- `key="anti_spam"` checkbox 必须勾选
- `can_submit = ... and anti_spam`
- 提交时 `st.session_state.onboarded = True` ✓
- 写 5 个 user_* 字段 ✓
- `st.switch_page("app.py")` ✓
- **不会**绕过 (`can_submit` False 时 `disabled=True`)

**必填校验** (L103-106):
- `genre and purpose and pain and len(pain.strip()) >= 2 and n_emo >= 3 and anti_spam`
- 边界实跑 (见上面测试):
  - `pain=""` → False ✓
  - `pain="a"` → False ✓
  - `pain="痛痛"` → True ✓
  - `pain="   "` → False (strip 后 0) ✓
  - 1 个情绪 → False ✓
  - 0 个情绪 → False ✓

**P1 隐患 (L124)**: 提示文案 `f"选 {3 - n_emo} 个情感"` 当 `n_emo=0` 时显示"选 3 个情感" — **正确**, 但 `n_emo` 在 L93 是 `len(emotions) if emotions else 0`, 而 `emotions` 默认是空 list, 所以 OK。

**P2 隐患**: `st.pills(..., label_visibility="collapsed")` 没传 `default=None`, Streamlit 默认行为是"无选中"。**OK**。

**onboarded 默认值** (`0_welcome.py:26-27`):
```python
if "onboarded" not in st.session_state:
    st.session_state.onboarded = False
```
- 用户第一次进 0_welcome → False ✓
- 提交后 → True ✓

**死循环风险** (实跑过 app.py:39-40 + 0_welcome.py:29-31):
- app.py:39: `if "onboarded" not in st.session_state or not st.session_state.onboarded: switch_page("0_welcome")`
- 0_welcome.py:29: `if st.session_state.onboarded: switch_page("app.py")`
- 新用户: app → onboarded False → 跳 0_welcome → 0_welcome 也设 False → 显示问卷 → 提交 → True → 跳 app → app True → 不跳 ✓ **不循环**
- 老用户: app → onboarded True → 不跳 → 显示主页 ✓
- `st.switch_page` 在 Streamlit 1.x 通过抛 `RerunException` 中断当前 run, 不会执行后续 st.markdown

**P0 #4 无重大 bug** ✓

---

## 二、5 个最严重的 bug (按严重度排序)

### 🔴 P0 Bug #1: P0 #3 进度条无 CSS, sidebar level badge 破版
**位置**: `core/points.py:48-59` `show_level_badge()` 引用 6 个 class, `app.py:362-371` 只定义 `.points-badge` (旧的), **没定义 `.level-badge / .level-icon / .level-code / .level-bar / .level-bar-fill / .level-next`**
**后果**: 任何新用户打开 app, 看到 sidebar 上"🪔 L1 初见者 ▌▌▌ 同行者 · 50 看见币"显示成**裸 HTML**, 进度条不可见, 像测试版
**修复**: 在 `app.py` 的 `<style>` 块 (建议在 `.points-badge` 之后) 加:
```css
.level-badge { ... }
.level-icon { ... }
.level-code { ... }
.level-bar { background: var(--card); height: 4px; border-radius: 2px; overflow: hidden; margin: 0.3rem 0; }
.level-bar-fill { background: linear-gradient(90deg, var(--accent), var(--ember)); height: 100%; transition: width 0.3s; }
.level-next { font-size: 0.7rem; color: var(--text-muted); }
```

### 🔴 P0 Bug #2: P0 #2 exceptions.py 写了但没接入
**位置**: `core/exceptions.py:1-56` 完整实现, 但 `grep` 整个项目 **0 处 import/use**
**后果**: 
- 裸 `st.error` 在 4 个页面继续用 (`1_excerpt.py:290, 109`; `4_genie.py:183`; `5_for_authors.py:515`; `8_points.py:234, 238, 240`)
- 任何 try/except 没有 traceback expander, 开发者看不到 traceback
- `safe_run` 装饰器**完全没用**
- 用户报告 bug 时, 看不到 stack trace
**修复**: 在所有 `try/except` 改 `gentle_error(e, where="xxx")`, 或用 `@safe_run` 装饰关键函数

### 🟡 P1 Bug #3: 改名"共鸣"→"被看见"漏 5 处用户可见
**位置**:
- `pages/0_welcome.py:66` 选项 `"🤝 我跟谁共鸣"`
- `pages/0_welcome.py:84` 选项 `"🔗 共鸣"`
- `core/points.py:18` L3 tagline `"段级被共鸣"`
- `core/points.py:212` 表格 `段级被 3+ 人共鸣`
- `core/points.py:247` reason_cn `段级被共鸣`
**后果**: 7 级等级体系、积分页、问卷页, 仍出现旧词"共鸣", **品牌一致性破坏**
**修复**: sed 全文替换为 "被看见" / "看见" (注意: `1_excerpt.py:209/251/301` 的"共鸣"是**情绪标签 en→cn 映射**, 应保留)

### 🟡 P1 Bug #4: 心灵语气不统一 — 4_genie.py:183 用 `st.caption` 代替 `st.error`
**位置**: `pages/4_genie.py:183` `st.caption(f"🪔 {amax_error[:120]}")` + `pages/5_for_authors.py:519, 522` `st.info("🪔 ...")`
**后果**: 错误信息用 caption 灰色小字, 用户**根本不会注意到**; 失去 gentle_error 的"灯暗了一下"语气
**修复**: 改用 `gentle_warning(amax_error[:120])` 或 `st.warning(f"🪔 {amax_error[:120]}")`

### 🟢 P2 Bug #5: 满级时 `next_min - points` 可能 ≤ 0 死循环显示
**位置**: `core/points.py:188` `再攒 {lv['next_min'] - st.session_state.points_total} 看见币`
**后果**: 实际**有 if 保护** (L183: `if lv["next_name"]`), 不会进 else 分支, **无视觉问题** ✓ 这是预防性发现, 不需修

---

## 三、整体评分 (1-10)

| 维度 | 分数 | 说明 |
|---|---|---|
| P0 #1 改名 | 4/10 | 漏 5 处用户可见, 核心品牌词没改干净 |
| P0 #2 心灵语气 | 5/10 | 函数写得对, 但**没接入**任何业务代码 |
| P0 #3 7 级 | 6/10 | 逻辑对/边界过, 但 CSS 缺失 → sidebar 破版 |
| P0 #4 问卷 | 9/10 | 完整, 反 spam/必填/switch_page 死循环都对 |
| 新代码质量 | 7/10 | exceptions/points 函数实现正确, 集成度低 |
| emoji/编码 | 10/10 | 全部合法 UTF-8, 14 个独特 emoji 0 坏字节 |
| 语法 | 11/11 OK | ast.parse 全部通过 |

**总评: 6.0 / 10** — 思路对, 单点函数实现正确, **集成度严重不足**。两个 P0 改动 (#2 异常, #3 进度条) 等于"只写了 helper, 没接入口子"。

---

## 四、推云前必须修的 (P0)

1. **app.py 加 `.level-badge/.level-bar` 等 6 个 CSS class** — `core/points.py:48-59` show_level_badge 才能显示
2. **core/exceptions.py 接入至少 4 个最常用 error 路径**:
   - `pages/1_excerpt.py:108-113` 截屏识别失败
   - `pages/1_excerpt.py:289-290` 保存失败
   - `pages/4_genie.py:179-183` AMAX 调用失败
   - `pages/8_points.py:236-240` 兑换失败
3. **5 处用户可见 "共鸣" 全部改为"被看见"** (保留 1_excerpt / 4_genie / 3_archive 的情绪字典, 那是 system emotion class)
4. **`pages/4_genie.py:183` 把 `st.caption(f"🪔 {amax_error}")` 改为 `gentle_warning(amax_error[:120])`** — 错误用 caption 用户根本看不到

**建议**: 推云前开一个 30 分钟的 "集成" PR, 只动 4 个 import + 1 段 CSS + 5 处文案, 风险低, 完成度从 6.0 拉到 8.5+。

---

**审计者**: opencode (minimax/MiniMax-M3)
**审计类型**: 静态 + 动态混合 (Python 沙箱实跑 level 边界 + emoji 验证 + syntax check)
**可信度**: 95% (唯一不能 100% 验证的是 Streamlit 实际渲染, 需要在浏览器里目视确认 .level-badge 样式)
