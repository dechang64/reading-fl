---
name: code-audit
description: 对Python项目执行自动化代码审计，包括编译检查、pytest、静态分析（裸except/硬编码路径/FedAvg加权/除零防护/import链/类型注解导入/gitignore完整性）、自动修复和回归验证。适用于FL/ML项目的日常巡检。
---

## 执行步骤

### 1. 确认项目清单
- 从长期记忆读取当前审计项目清单
- 用 `ls -d` 逐个验证目录存在性，标记已不存在的项目
- 当前已知不存在的项目：organoid-fl-upgrade、mural-restoration（非upgrade版）、download/PAI

### 2. 编译检查
```bash
find <projects> -name "*.py" -not -path "*__pycache__*" -not -path "*.egg-info*" | xargs python3 -m py_compile
```
- 必须全部通过，否则先修语法错误

### 3. pytest
- 从项目根目录运行（避免 import 路径问题）
- fundfl-upgrade/python、mural-restoration-upgrade/python、dgy-treehole-v2 三个可运行
- 其余因缺 torch/pyembroidery 无法运行（已知限制）
- mural-restoration 需 `--ignore=tests/test_fl_engine.py`（依赖 torch）

### 4. 静态分析（按优先级）

#### 4a. 裸except
```bash
find <projects> -name "*.py" ... -exec grep -Hn 'except:' {} +
```

#### 4b. 硬编码路径
```bash
find <projects> -name "*.py" ... -exec grep -Hn '/home/' {} +
```
- 实验脚本中的硬编码路径可接受，生产代码不可

#### 4c. FedAvg加权
```bash
find <projects> -name "*.py" ... -exec grep -Hn '\.mean(' {} + | grep -i 'fedavg\|aggregate'
```
- FedAvg必须用sample-weighted，不能用`.mean(dim=0)`

#### 4d. 除零防护
- AST扫描聚合函数中的 `/ len(` 模式
- 检查是否有guard（`if not params_list`、`if total == 0`等）
- 重点文件：fl_engine.py、aggregation.py、federated.py
- **同一项目不同文件的同名函数修复进度可能不同，需逐一验证**

#### 4e. import链完整性
- AST解析：收集每个模块定义的符号 vs import语句引用的符号
- 只检查项目内部模块的from X import Y

#### 4f. 类型注解导入缺失（5/30新增）
- AST扫描所有类型注解中引用的符号
- 与文件实际import对比，找出缺失
- **关键区分**：有`from __future__ import annotations`的文件注解是字符串，不会触发运行时NameError
- **修复方式**：添加`from __future__ import annotations`（比逐个import更安全、更简洁）
- 已有该import的文件不重复添加

#### 4g. gitignore完整性+重复
- 检查6项必备条目：`__pycache__/`、`*.pyc`、`*.egg-info/`、`dist/`、`build/`、`.env`、`.venv/`
- `sort file | uniq -d` 检查重复行

#### 4h. 梯度裁剪
- PyTorch训练循环应有`clip_grad_norm_`
- numpy训练循环不需要

#### 4i. Streamlit兼容性（6/8新增）
- `st.metric`的`delta`只接受数字或None，传字符串会TypeError
- `components.html`不支持`use_container_width`参数
- 用rg搜索这两种模式

#### 4j. 可变默认参数（6/8新增）
- AST扫描函数定义中的`List`/`Dict`/`Set`默认值
- Python经典陷阱，运行时共享状态导致bug

#### 4k. 未使用导入（6/8新增，低优先级）
- AST收集import名称，再检查后续代码是否使用
- 仅在核心模块（非tests/experiments/pages）中检查
- 不自动修复，仅记录

#### 4l. 缺失docstring（6/8新增，低优先级）
- AST扫描公共函数（非_开头）是否有docstring
- 不自动修复，仅记录数量

### 5. 自动修复
- 直接修复，不通知用户
- 修复后重新编译检查+pytest确认

### 6. 报告
- 仅在有需用户决策事项时才发送消息
- 否则静默完成，结果写入当日日记

## 质量标准
- 编译检查必须100%通过
- pytest必须全部通过（可用项目）
- 静态分析0项新发现才算完成
- 修复后必须回归验证

## 踩坑记录
- **pytest需从项目子目录运行**：mural-restoration-upgrade/python、fundfl-upgrade/python，否则import路径错误
- **TWC-FL-PROD有4份副本**：python/twc_fl、python/twc_fl_en、deploy-cn、deploy-en，修一个要改四个
- **embodied-fl yolo_fed有3个独立聚合函数文件**：utils/federated.py、run_detection.py、run_yolo_federated.py
- **`from __future__ import annotations`批量修复**：5/30一次性修复61个文件，6/4追加34个（含streamlit-cloud 24个），6/6又追加31个（streamlit-cloud），累计126个。比逐个import更安全
- **streamlit-cloud是反复出现的盲区**：6/4修24个→6/6又发现31个。根因：手动列文件清单不完整。**正确做法**：用AST扫描所有.py文件（排除`__init__.py`和已有`from __future__ import annotations`的文件），而非手动列清单
- **除零防护AST扫描需人工审查**：AST扫描`/ sum()` `/ len()`模式会产生大量误报（softmax归一化、已有guard的聚合函数等），需逐一审查上下文确认是否真正需要修复
- **gitignore验证用grep不用rg**：rg的glob模式会转义`*`，导致`*.pyc`等模式误报
- **6/8审计新增3个检查项**：Streamlit兼容性（st.metric delta/ components.html use_container_width）、可变默认参数、未使用导入。均为0项发现，代码库稳定
- **twc_core未安装是已知限制**：embodied-fl-upgrade和defect-fl-upgrade的analysis/模块引用twc_core，但twc_core未pip install -e且依赖torch。这些import在有torch环境才用，不算bug
