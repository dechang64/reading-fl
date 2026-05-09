# TOOLS.md - Local Notes

## VLM 设计审查
- **工具**：`z-ai vision -p "prompt" -i screenshot.png -o output.json`
- **用途**：截图审查 UI/网站设计质量，驱动迭代
- **注意**：429 限流，每次最多 2 个并发，间隔 8s
- **Playwright 截图**：用 `/home/z/.venv/bin/python3`（不是系统 python3）

## LLM 翻译 Python 代码
- **永远不要让 LLM 翻译含转义字符的字符串字面量**（`\n`、`\"`）
- **正确做法**：提取内容 → 解码转义 → 翻译 → 重新编码 → 写回原位置
- **Substring 替换适合短文本**，LLM 适合长文本，两者结合

## 事实核实

- **DOI 不可信**：LLM 编造的 DOI 看起来真实但 404，必须 `curl -s -o /dev/null -w "%{http_code}"` 验证
- **百分比/参数量**：必须对照代码和日志，不能直接用 LLM 生成的数字
- **NBER WP vs 正式发表**：很多顶刊论文先以 NBER Working Paper 发布，后续正式发表。引用时应核实是否已发表，引用正式版本。典型：Vayanos & Vila (2009 NBER → 2021 RFS)、Rey (2015 NBER → 2015 IJCB)
- **DOI 404 不一定意味着引用错误**：部分 DOI 解析服务不稳定，需结合网络搜索交叉验证
- **学术评审流程**：全文通读 → 逐条验证引用（DOI+搜索）→ 结构分析 → 内容深度评估 → 格式检查 → 写评审报告

## 文件下载/分享
- **GoFile 是临时链接**：TA 不喜欢，文件应 base64 内嵌或用 GitHub
- **base64 内嵌**：适合 <1MB 的文件（PDF/DOCX），直接嵌入 HTML 的 `<a href="data:...">` 下载

## 记忆系统：反从众原则

- **daily notes 是 ground truth**：写入后不修改，是原始记录
- **long-term memory 是有损摘要**：由 LLM 生成，受当前 session 语境影响
- **归档时优先保留原始措辞**，不要"合理化"或"润色"——合理化方向 ≠ 真实方向
- **检索-更新反馈环**：每次 read_memory → 行为 → edit_memory → 下次读取被上次生成影响，类似人类记忆的 reconsolidation
- **多源归并时的多数暴政**：连续多天 daily notes 对同一事件的微小偏差，归档时折中会抹杀最准确的记录
- **原则**：不确定的信息宁可不写进 long-term memory，也不要写一个"听起来合理"的版本

## 执行节奏：先想后做

- **TA 说"思考一下"时，停下来**：不要急于执行，先理解 TA 的真实意图
- **典型案例**：TA 说"streamlit cloud 跑模拟数据没问题啊，不需要删除，再加上真实数据就好了呀"——我直接删了模拟实验重写 app.py，TA 要的是**叠加**不是**替换**
- **原则**：修改前先问自己"TA 是要替换还是叠加？是要简化还是扩展？"

## Streamlit vs 纯 HTML
- **Streamlit 适合**：交互式 Demo、数据可视化、快速原型
- **纯 HTML 适合**：正式网站、学术会议页面、需要完全控制视觉的场景
- **Streamlit 部署**：Streamlit Cloud（免费）
- **静态站部署**：GitHub Pages（免费）

## Streamlit Cloud API 兼容性（血泪教训）

- **`st.metric` 的 `delta` 只接受数字或 None**：传字符串（如 `f"± 1.0%"`）会 TypeError。解决方案：用自定义 CSS stat cards 替代 `st.metric`。
- **`components.html()` 不支持 `use_container_width`**：新版 Streamlit Cloud 会报 `IFrameMixin._html() got an unexpected keyword argument`。解决方案：用 CSS `iframe { width: 100% !important }` 实现自适应。
- **`st.tabs()` 内异常传播**：一个 tab 崩溃会中断整个脚本。每个 tab 的 render() 必须 try/except。
- **`st.stop()` 在 tabs 里会终止整个脚本**：用 `return` 代替。
- **tab 内元素必须加唯一 key=**：否则 DuplicateElementId。
- **原则**：Streamlit Cloud 的 Python 版本和 Streamlit 版本可能比本地新，API 可能不兼容。写代码时查官方文档确认参数类型，不要凭印象。

## Streamlit 多页面项目最佳实践（dgy-treehole v2 经验）

- **CSS 必须抽到共享模块**：`st.switch_page()` 跳转后，app.py 的 CSS 不会传递到子页面。每个子页面必须独立注入 CSS。做法：`core/styles.py` 定义所有 CSS + `inject_css()` 函数，每个子页面 `set_page_config()` 后调用
- **import 必须在文件顶部**：函数体内/条件块内的 import 虽然能跑（Python 缓存），但每次渲染都执行查找，且违反 PEP8
- **`init_db()` 放在 db.py 模块末尾**：`import db` 时自动建表，不依赖 app.py 显式调用。内存数据库没有持久化文件，模块加载时必须自动建表
- **`st.session_state` 变量每个页面独立初始化**：用户可能直接访问子页面，不能假设其他页面已初始化 session 变量
- **`unsafe_allow_html=True` + 用户输入 = XSS 风险**：匿名社交场景中 `post['content']` 直接嵌入 HTML，需 `html.escape()` 转义
- **`download_button` 的 `data=open().read()`**：文件句柄未 close，用 `with open() as f: data=f.read()` 后传 `data` 变量
- **Streamlit 每次执行是独立脚本**：表单局部变量在 rerun 后不存在，必须存 `st.session_state`
- **CSS grid 优于 st.columns**：`st.columns()` 每行独立计算高度，卡片大小不一致。用 `display:grid; grid-template-columns:1fr 1fr` 保证等宽等高

## MiniMax API（2026-05-05 更新，对照官方 CLI 源码）

- **域名**：`api.minimaxi.com`（国内），`api.minimax.io`（国际）
- **聊天 API**：`POST /v1/chat/completions`（OpenAI 兼容格式），模型 `MiniMax-Text-01`
- **音乐 API**：`POST /v1/music_generation`，模型 `music-2.6-free`（限免）或 `music-2.6`（Token Plan）
- **音乐 payload 必须包含 `audio_setting`**：`{"format": "mp3", "sample_rate": 44100, "bitrate": 256000}`，否则报错
- **音乐 payload 不要传 `duration`**：API 不接受此参数，官方 CLI 也没有
- **音乐 payload 需要 `stream: false`**：非流式模式
- **音乐响应格式**：JSON，`data.audio` 字段为 hex 编码的音频数据，需 `bytes.fromhex()` 解码
- **音乐参数**：`is_instrumental: true`（纯音乐），`output_format: 'hex'`
- **响应检查**：`data.base_resp.status_code` 必须为 0，否则失败
- **认证**：`Authorization: Bearer <API_KEY>`，Key 在 platform.minimaxi.com 的「账户管理 > API Keys」创建
- **海螺AI年度套餐 ≠ API 额度**：两套独立计费，API 需在开放平台单独订阅 Token Plan
- **官方 CLI 源码**：https://github.com/MiniMax-AI/cli（TypeScript），payload 格式以 CLI 源码为准
- **旧 API 已弃用**：`chatbase_v2`、`abab6.5s-chat`、`text_to_music`、`music-02` 均不可用

## 小红书「朱雀」AIGC检测（2026-05-13）
- **现状**：小红书已上线「朱雀」AIGC检测系统，未主动标识AI生成内容会被自动检测并限流
- **影响**：有博主AI率从85%降到12%才恢复流量；真人手写内容也被误判为AI后遭限流/封号
- **七件套发布规则**：①务必主动标识AIGC ②增加人味（口语化、个人经历、不完美表达）③避免模板化结构 ④小红书内容要比其他平台更"活"

## 代码审计：FedAvg 加权（2026-05-06/07 教训）

- **`_fedavg` 必须按样本数加权**：标准 FedAvg 公式是 `w_global = Σ(n_k/N) * w_k`，不是 `.mean(dim=0)`。五个项目（defect-fl、embodied-fl、reading-fl、organoid-fl、mural-restoration）都犯了同样的错误——用简单平均代替加权平均
- **同一项目多实现盲区**：organoid-fl 有两个独立 FedAvg 实现（`fl_engine.py` 的 `fedavg_aggregate` 和 `multi_task_fl.py` 的 `_fedavg`），修了一个漏了另一个。**审计不能只看函数名，要看所有调用路径和所有同名/同功能函数**
- **修复模式**：`_fedavg(params_list, client_data_sizes=None)`，向后兼容（None 时退化为等权）
- **审计检查清单**：编译检查 → pytest → 裸except → 硬编码路径 → gitignore → FedAvg加权（所有同名函数）→ 梯度裁剪 → 模型加载错误处理 → import链 → 无用导入
- **审计项目清单需定期校验**：mural-restoration 和 download/PAI 已不存在，审计时先 LS 确认目录存在性，避免浪费时间
- **import 链检查要用 AST**：`rg` 搜 import 语句只能看到文本，不能验证 `from X import Y` 中 Y 是否真的存在于 X 模块。正确做法：用 `ast.parse()` 解析目标模块，遍历 `ClassDef`/`FunctionDef` 收集所有定义的符号，再与 import 语句比对。典型案例：embodied-fl-upgrade 的 `streamlit_app.py` 导入了 `Detection`，但 `detector.py` 中只定义了 `RobotSceneDetector`，`Detection` 是无用导入
- **无用导入检查**：用 AST 收集 import 名称，再检查后续代码是否使用。注意：`__init__.py` 中的重导出不算无用导入，experiments/ 和 tests/ 中的无用导入优先级低（不影响生产代码）
- **import链检查需同时验证"Y存在"和"Y被使用"**：6/2审计发现 `from utils.helpers import split_data_non_iid`，函数在helpers.py中不存在且未使用。这类bug比"Y存在但未使用"更危险——运行时直接 ImportError。AST检查流程：①解析目标模块收集定义符号 ②验证import的Y是否在定义中 ③验证Y是否在后续代码中使用
- **gitignore 标准化**：所有项目必须包含 `__pycache__/`、`*.pyc`、`*.egg-info/`、`dist/`、`build/`、`.env`、`.venv/`。6个项目已统一补充（2026-05-12）
- **gitignore 去重**：用 `sed` 批量追加 gitignore 条目时可能产生重复行（2026-05-17踩坑）。修复后需 `sort -u` 去重。审计时应检查 gitignore 是否有重复
- **gitignore 验证用 grep 不用 rg**：rg 的 glob 模式会转义 `*`，导致 `*.pyc` 等模式误报为"不存在"。验证 gitignore 内容时用 `grep -q '\.pyc'` 而非 `rg -q '\*.pyc'`（2026-05-19踩坑）
- **py_compile ≠ 运行时安全**：`python3 -m py_compile` 只检查语法，不检查运行时 NameError。典型案例：mural-restoration-upgrade/restoration_engine.py 用了 `Tuple` 类型注解但未 import，编译通过但 pytest 报 NameError。**类型注解中引用的符号必须在运行时可解析**
- **Streamlit demo 也要加权**：embodied-fl-upgrade/streamlit_app.py 的 FedAvg 用了 `.mean(dim=0)`，虽然是 demo（等权），但为了一致性和教学正确性，应改为 sample-weighted
- **streamlit-cloud 是 FedAvg 加权盲区**：5/31 审计发现 streamlit-cloud 下5个文件仍用 `.mean(dim=0)`。之前审计只覆盖了 upgrade 版本，漏了 streamlit-cloud 部署版本。**审计范围必须包含所有部署路径，不只是开发目录**
- **streamlit-cloud 也是 annotations 修复盲区**：6/4修24个→6/6又发现31个，同一个模式重复出现第三次。**根因**：批量修复时用 `rg` 搜文件清单不完整（漏了子目录或新增文件）。**正确做法**：用 AST 扫描所有 .py 文件（排除 `__init__.py` 和已有 `from __future__ import annotations` 的文件），而非手动列清单
- **审计项目清单持续校验**：5/22 审计确认 organoid-fl-upgrade、mural-restoration、download/PAI 三个目录已不存在，实际审计6个项目（embodied-fl-upgrade、defect-fl-upgrade、fundfl-upgrade、reading-fl-upgrade、embroidery-agent、mural-restoration-upgrade）
- **twc_core 未安装导致 pytest 不可用**：5/22 审计发现 twc_core 未 pip install -e，导致 embodied-fl-upgrade 测试无法 import。`pip install -e .` 因 PEP 668 和超时失败。临时方案：`PYTHONPATH` 加入 twc-core 路径，但 twc_core 内部依赖 torch，仍无法运行。**结论：5/6 项目 pytest 因 torch/pyembroidery 依赖缺失无法在当前环境运行，仅 fundfl-upgrade（6/6 passed）可完整测试**
- **load_state_dict 无 try/except**：5/22 审计发现11处 `load_state_dict` 调用无 try/except 包裹，均在 FL 训练循环中加载同架构模型 state_dict，失败概率极低，暂不修复
- **vla_collector.py 除零风险**：`embodied-fl-upgrade/python/analysis/vla_collector.py:776-777` 的 `total_steps / len(episodes)` 和 `successes / len(episodes)` 缺少空列表防护。**5/23已修复**：加 `if n > 0 else 0.0` 保护
- **FedAvg 除零防护模式**：5/24-5/29 审计发现并修复30+处 FedAvg 聚合函数缺少空列表/零样本防护。模式：①检查 `params_list`/`client_models`/`updates` 非空 ②检查 `total = sum(weights)`/`total_samples` 不为零 ③否则 raise ValueError。涉及所有6核心项目+ewa-fed+twc-core+TWC-FL-PROD+embodied-fl实验脚本。**5/28新增**：TWC-FL-PROD 4份副本需同步修复；embodied-fl yolo_fed 有3个独立聚合函数也需逐一修复。**5/29新增**：①`aggregate_task_aware`比`aggregate_fedavg`有更多除零点（sim_sum/perf_sum/w_sum），需逐一防护 ②`_split_data(n_clients)`也需`n_clients<=0`防护 ③同一项目不同文件的同名函数（federated.py vs run_yolo_federated.py vs run_detection.py）修复进度可能不同，需逐一验证
- **TWC-FL-PROD 副本同步**：6/3审计修复data_vault.py除零防护时，只修了2/4份（python/twc_fl + deploy-cn），deploy-en和twc_fl_en未同步。**教训**：TWC-FL-PROD有4份完整副本（python/twc_fl、python/twc_fl_en、deploy-cn/.../twc_fl、deploy-en/.../twc_fl_en），任何修复必须4份全改
- **缺失类型注解导入**：5/25 审计发现7处 `List`/`Dict`/`Optional` 在类型注解中使用但未从 `typing` 导入。`py_compile` 不检查运行时 NameError，只有 pytest 或实际运行才能发现。**审计检查清单需增加：AST 扫描类型注解中引用的符号是否已导入**
- **`from __future__ import annotations` 批量修复**：5/30 审计发现61个文件存在类型注解引用未导入符号的问题（如 `AuditEntry`、`AggregationResult` 等）。最安全的修复方式是在文件头部添加 `from __future__ import annotations`，将所有注解变为字符串字面量，避免运行时 NameError。**注意**：已有 `from __future__ import annotations` 的文件不需要重复添加；`__init__.py` 和空文件不需要
- **z-ai web_search 429 限流**：并行调用 `z-ai function -n web_search` 超过2个会触发429。必须串行搜索，每次间隔几秒。早报搜索7个关键词组需要逐个执行

## 前端调试：agent-browser + VLM 审查

- **流程**：agent-browser 打开页面 → set viewport 390×844（iPhone）→ screenshot → VLM 审查设计质量
- **VLM 审查 prompt 模板**：`"审查这个页面的设计质量。重点：1)布局 2)交互 3)风格统一 4)UI问题。中文简洁回答。"`
- **注意**：429 限流，每次最多 2 个并发，间隔 8s
- **Console 检查**：`agent-browser console` + `agent-browser errors`，无输出 = 无错误
