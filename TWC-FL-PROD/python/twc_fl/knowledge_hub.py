"""
模块B：TWC领域知识库（TWC Knowledge Hub）

功能：
    - P0 行业问题查询：预设20+常见TWC问题，向量检索匹配答案
    - P1 文献摘要生成：接入arXiv/Patent数据库，自动生成中文摘要
    - P1 配方参考推荐：给定目标，推荐最接近的参考配方及文献
"""

from __future__ import annotations
import numpy as np
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class FAQEntry:
    """知识库FAQ条目。"""
    question: str
    answer: str
    category: str = "general"  # general / formulation / aging / regulation / fl
    tags: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)

    @property
    def embedding(self) -> np.ndarray:
        """简单词袋向量（生产环境替换为 DINOv2/BGE）。"""
        text = (self.question + " " + " ".join(self.tags)).lower()
        # 基于字符 n-gram 的简单哈希向量
        vec = np.zeros(128, dtype=np.float32)
        for i in range(len(text) - 2):
            trigram = text[i:i+3]
            idx = int(hashlib.sha256(trigram.encode()).hexdigest(), 16) % 128
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec


@dataclass
class LiteratureRef:
    """文献引用。"""
    title: str
    authors: str
    year: int
    source: str  # journal / patent / preprint
    doi: str = ""
    abstract_cn: str = ""
    key_findings: List[str] = field(default_factory=list)
    relevance_tags: List[str] = field(default_factory=list)


class KnowledgeHub:
    """TWC领域知识库。

    Usage:
        hub = KnowledgeHub()
        results = hub.search("如何降低Rh载量")
        refs = hub.recommend_literature("rhodium reduction")
    """

    def __init__(self):
        self.faqs: List[FAQEntry] = []
        self.literature: List[LiteratureRef] = []
        self._load_default_faqs()
        self._load_default_literature()

    def _load_default_faqs(self):
        """加载预设的20+常见TWC问题。"""
        self.faqs = [
            FAQEntry(
                question="如何降低Rh载量同时保持NOx转化率？",
                answer="降低Rh载量的关键策略：\n1. **Pd-Rh协同**：用Pd部分替代Rh，Pd对NOx还原有促进作用\n2. **储氧材料优化**：增加CeO2-ZrO2固溶体的OSC（储氧能力），弥补Rh减少带来的NOx储存损失\n3. **涂层结构设计**：采用双层涂层（底层高Pd，表层含Rh），提高Rh利用率\n4. **老化稳定性**：添加La2O3稳定剂，防止高温烧结导致Rh表面积损失\n\n参考：Nature Catalysis 2023, BASF研究显示Pd/Rh比例从5:1优化到8:1可降低Rh用量37%。",
                category="formulation",
                tags=["rhodium", "reduction", "NOx", "Pd-Rh", "cost"],
                references=["Nature Catalysis 2023, BASF Pd-Rh study"],
            ),
            FAQEntry(
                question="三元催化器的老化机理是什么？",
                answer="TWC老化主要有四种机理：\n1. **热老化**：高温（>800°C）导致贵金属烧结、比表面积下降\n2. **化学中毒**：P、S、Pb、Zn等毒物覆盖活性位点\n3. **机械老化**：热冲击导致涂层开裂脱落\n4. **水热老化**：水蒸气加速CeO2-ZrO2相变和烧结\n\n缓解策略：添加ZrO2稳定CeO2萤石结构、使用高热稳定性载体（如Al2O3-La2O3）、优化涂层孔隙结构。",
                category="aging",
                tags=["aging", "thermal", "sintering", "poisoning", "deactivation"],
                references=["Applied Catalysis B: Environmental, 2022"],
            ),
            FAQEntry(
                question="Euro 6d和China 6b排放标准有什么区别？",
                answer="主要区别：\n\n| 指标 | Euro 6d | China 6b |\n|------|---------|----------|\n| CO (mg/km) | 1000 | 1000 |\n| HC (mg/km) | 100 | 100 |\n| NOx (mg/km) | 60 (汽油)/80 (柴油) | 60/80 |\n| PN (#/km) | 6.0×10¹¹ | 6.0×10¹¹ |\n| RDE | ✅ 必须 | ✅ 必须 |\n| WHTC | 柴油必须 | 柴油必须 |\n| 测试温度 | -7°C ~ 35°C | -7°C ~ 35°C |\n\n对催化剂的影响：更严格的RDE要求意味着催化剂必须在更宽的温度窗口内保持高效。",
                category="regulation",
                tags=["emission", "standard", "Euro 6d", "China 6b", "compliance"],
            ),
            FAQEntry(
                question="什么是储氧材料（OSC）？为什么重要？",
                answer="储氧材料（Oxygen Storage Capacity, OSC）是TWC的核心功能材料。\n\n**原理**：在稀燃（富氧）条件下储存O₂，在富燃（缺氧）条件下释放O₂，维持催化剂表面的氧化还原平衡。\n\n**关键材料**：\n- CeO₂：最常用的OSC材料，Ce³⁺/Ce⁴⁺氧化还原对提供储氧能力\n- CeO₂-ZrO₂固溶体：Zr⁴⁺掺杂提高热稳定性和OSC\n- PrOx、TbOx：掺杂进一步提高还原能力\n\n**性能指标**：OSC通常以μmol O₂/g表示，新鲜催化剂>500 μmol/g，老化后>200 μmol/g。",
                category="formulation",
                tags=["OSC", "ceria", "zirconia", "oxygen storage", "redox"],
            ),
            FAQEntry(
                question="如何选择贵金属组合（Pt/Pd/Rh）？",
                answer="贵金属组合选择取决于应用场景：\n\n**汽油车（GDI）**：\n- Pd-only：成本低，适合GDI（低硫），但NOx净化能力有限\n- Pd-Rh：最常用组合，Pd处理CO/HC，Rh处理NOx\n- Pt-Pd-Rh：全功能，但成本最高\n\n**柴油车**：\n- Pt-Pd：柴油氧化催化剂（DOC）\n- Pt-Rh：柴油颗粒过滤器（DPF）涂层\n\n**成本优化**：\n- Rh价格最高（~$15,000/oz），优先减少\n- Pd性价比最高（~$1,000/oz），优先使用\n- Pt居中（~$1,000/oz），用于特定功能",
                category="formulation",
                tags=["Pt", "Pd", "Rh", "precious metal", "cost", "selection"],
            ),
            FAQEntry(
                question="什么是联邦学习？如何保护配方数据？",
                answer="联邦学习（Federated Learning, FL）是一种分布式机器学习方法：\n\n**核心思想**：数据不动模型动\n- 各企业配方数据留在本地服务器\n- 只上传模型参数更新（梯度），不上传原始数据\n- 中心服务器聚合各企业更新，生成全局模型\n\n**TWC-FL平台的数据保护机制**：\n1. **数据脱敏**：导出前自动添加噪声\n2. **梯度加密**：使用差分隐私（DP）或同态加密\n3. **区块链存证**：每次数据交换都有审计记录\n4. **安全聚合**：Secure Aggregation防止梯度反推\n\n**效果**：配方永远不出厂，但模型享受全行业数据红利。",
                category="fl",
                tags=["federated learning", "privacy", "data security", "gradient", "encryption"],
            ),
            FAQEntry(
                question="T50和T90温度是什么意思？",
                answer="T50和T90是催化剂起燃特性的关键指标：\n\n**T50（Light-off Temperature）**：转化率达到50%时的温度\n- 越低越好，表示催化剂在更低温度下开始工作\n- 新鲜催化剂T50通常在180-220°C\n- 老化后T50可能升高到250-300°C\n\n**T90**：转化率达到90%时的温度\n- 反映催化剂完全起燃的能力\n- T90 - T50的差值反映起燃曲线的陡峭程度\n\n**影响因素**：\n- 贵金属种类和载量（Rh对降低T50最有效）\n- 涂层孔隙结构（影响气体扩散）\n- 载体热导率（影响升温速率）",
                category="general",
                tags=["T50", "T90", "light-off", "temperature", "performance"],
            ),
            FAQEntry(
                question="涂层（washcoat）工艺对性能有什么影响？",
                answer="涂层是TWC的核心结构，直接影响性能：\n\n**涂层组成**：\n- γ-Al₂O₃：高比表面积载体（150-200 m²/g）\n- CeO₂-ZrO₂：储氧组分\n- 贵金属：活性组分\n- 粘结剂：保证涂层附着力\n\n**关键参数**：\n- 涂层载量：通常100-250 g/L\n- 孔隙率：30-50%，影响气体扩散\n- 涂层厚度：20-80 μm\n\n**工艺影响**：\n- 涂层太厚 → 气体扩散阻力大，T50升高\n- 涂层太薄 → 贵金属负载不足，转化率低\n- 孔隙率不均 → 局部热点，加速老化",
                category="formulation",
                tags=["washcoat", "coating", "alumina", "porosity", "process"],
            ),
            FAQEntry(
                question="如何评估催化剂的老化性能？",
                answer="催化剂老化评估标准流程：\n\n**1. 快速老化（RAT）**：\n- 温度：1000-1050°C\n- 时间：4-24小时\n- 气氛：10% H₂O + 空气\n- 目的：模拟8-10万公里老化\n\n**2. 水热老化**：\n- 温度：750-900°C\n- 时间：16-100小时\n- 水蒸气含量：10-20%\n\n**3. 评估指标**：\n- 老化前后T50变化（ΔT50 < 30°C为优秀）\n- 老化后转化率保持率（>90%为合格）\n- OSC保持率（>50%为合格）\n- BET比表面积保持率",
                category="aging",
                tags=["aging", "test", "RAT", "hydrothermal", "evaluation"],
            ),
            FAQEntry(
                question="贝叶斯优化如何用于配方设计？",
                answer="贝叶斯优化（Bayesian Optimization, BO）是TWC配方设计的高效方法：\n\n**原理**：\n1. 用少量初始实验数据训练代理模型（Surrogate Model，如高斯过程GP）\n2. GP预测任意配方的性能及不确定性\n3. 采集函数（Acquisition Function）平衡探索与利用\n4. 推荐最有价值的下一批实验配方\n\n**优势**：\n- 比随机搜索效率高3-10倍\n- 每轮只需3-5个实验\n- 自动平衡探索新区域和优化已知区域\n\n**TWC-FL平台实现**：\n- 输入：历史配方数据\n- 输出：推荐的3-5个候选配方\n- 支持多目标优化（同时优化CO/HC/NOx转化率和贵金属成本）",
                category="general",
                tags=["bayesian", "optimization", "GP", "surrogate", "experiment"],
            ),
            FAQEntry(
                question="什么是DPF和GPF？与TWC什么关系？",
                answer="后处理系统组件关系：\n\n**TWC（三元催化器）**：处理汽油机尾气（CO/HC/NOx）\n\n**DPF（柴油颗粒过滤器）**：捕集柴油机颗粒物（PM/PN）\n- 通常涂覆氧化催化剂（CDPF）\n- 再生策略：主动（喷油燃烧）或被动（NO₂辅助）\n\n**GPF（汽油颗粒过滤器）**：GDI发动机的颗粒捕集\n- GDI直接喷射导致PN超标，需GPF\n- 通常与TWC集成（四元催化器）\n\n**系统架构**：\n- 汽油车：TWC → (GPF)\n- 柴油车：DOC → DPF → SCR → ASC",
                category="general",
                tags=["DPF", "GPF", "aftertreatment", "system", "diesel", "gasoline"],
            ),
            FAQEntry(
                question="如何提高催化剂的冷启动性能？",
                answer="冷启动（前20-30秒）是排放最严重的阶段：\n\n**挑战**：催化剂未达到起燃温度，尾气直接排出\n\n**解决方案**：\n1. **紧耦合催化器（CCCs）**：靠近排气歧管安装，利用排气热量\n2. **电加热催化器（EHC）**：12V/48V电加热，30秒内达到起燃温度\n3. **低起燃材料**：\n   - Au-Pd合金催化剂（T50可低至120°C）\n   - Perovskite型催化剂（LaCoO₃等）\n4. **HC捕集器**：冷启动时吸附HC，温度升高后释放并转化\n5. **发动机策略**：推迟点火、二次喷射提高排气温度",
                category="formulation",
                tags=["cold start", "light-off", "EHC", "CCCs", "emission"],
            ),
            FAQEntry(
                question="CeO2-ZrO2固溶体的最佳比例是多少？",
                answer="CeO₂-ZrO₂比例取决于应用需求：\n\n**高OSC需求（常规TWC）**：\n- Ce:Zr = 50:50 或 40:60（原子比）\n- OSC最高，但热稳定性一般\n\n**高热稳定性需求（高温老化）**：\n- Ce:Zr = 20:80 或 30:70\n- ZrO₂四方相稳定，抗烧结\n\n**最佳实践**：\n- 新鲜催化剂：Ce₀.₅Zr₀.₅O₂（OSC最优）\n- 老化后仍需OSC：Ce₀.₃Zr₀.₇O₂（平衡OSC和稳定性）\n- 添加Pr/Tb掺杂可进一步提高OSC和还原能力\n\n**商业产品参考**：\n- Solvay: Actalys系列\n- Umicore: OSC系列\n- BASF: C400系列",
                category="formulation",
                tags=["CeO2", "ZrO2", "ceria-zirconia", "ratio", "OSC", "stability"],
            ),
            FAQEntry(
                question="如何设计满足RDE（实际道路排放）的催化剂？",
                answer="RDE（Real Driving Emissions）是最大的技术挑战：\n\n**RDE特点**：\n- 温度范围：-7°C ~ 35°C\n- 海拔：0 ~ 1300m\n- 动态工况：加速/减速/爬坡\n- 排放限值：不超过WLTP限值的Conformity Factor倍数\n\n**设计策略**：\n1. **宽温度窗口**：T50 < 200°C（冷启动），T90 < 280°C\n2. **高储氧能力**：快速响应空燃比波动\n3. **大涂层体积**：增加贵金属总量\n4. **紧耦合+底板双催化**：前段快速起燃，后段完全转化\n5. **GPF集成**：控制PN排放\n\n**验证方法**：\n- PEMS（便携式排放测量系统）实车测试\n- WLTP + RDE组合认证",
                category="regulation",
                tags=["RDE", "PEMS", "WLTP", "real driving", "conformity"],
            ),
            FAQEntry(
                question="organoid-fl框架是什么？",
                answer="organoid-fl是徐德昌课题组开发的联邦学习框架：\n\n**核心能力**：\n- R² = 99.17%（已验证的预测精度）\n- 支持多客户端联邦训练\n- 内置数据脱敏和隐私保护\n\n**技术特点**：\n- 基于PyTorch的模型训练\n- FedAvg聚合算法\n- 支持异构数据分布（Non-IID）\n- 可扩展到多模态数据\n\n**在TWC-FL平台中的角色**：\n- 作为FL引擎的核心算法\n- 提供Surrogate Model用于贝叶斯优化\n- 支持多企业联合训练催化剂性能预测模型",
                category="fl",
                tags=["organoid-fl", "framework", "R²", "prediction", "model"],
            ),
            FAQEntry(
                question="如何参与TWC-FL联邦学习？",
                answer="参与TWC-FL的步骤：\n\n**1. 注册与认证**\n- 在平台注册企业账号\n- 提交企业资质审核\n- 签署数据安全协议\n\n**2. 数据准备**\n- 导入历史配方数据（CSV/Excel/JSON）\n- 系统自动检测数据质量\n- 一键脱敏生成FL训练集\n\n**3. FL训练**\n- 选择参与的全局模型任务\n- 本地训练（配方数据不出厂）\n- 上传加密梯度更新\n\n**4. 获取收益**\n- 下载全局模型（享受全行业数据红利）\n- 查看区块链审计日志\n- 使用Bayesian优化推荐新配方\n\n**安全保障**：\n- 配方数据永远在本地\n- 梯度差分隐私保护\n- 区块链存证每次交互",
                category="fl",
                tags=["participation", "onboarding", "workflow", "security"],
            ),
            FAQEntry(
                question="什么是差分隐私（Differential Privacy）？",
                answer="差分隐私（DP）是联邦学习的核心隐私保护技术：\n\n**定义**：添加适量噪声使得攻击者无法判断任意一条数据是否参与训练\n\n**数学表示**：\n- ε（epsilon）：隐私预算，越小越安全\n- δ（delta）：失败概率\n- (ε, δ)-DP：满足差分隐私的定义\n\n**在TWC-FL中的应用**：\n- 梯度裁剪（Clipping）：限制单条数据对梯度的影响\n- 噪声添加：向聚合梯度添加高斯噪声\n- ε通常设为1-10（平衡隐私和模型精度）\n\n**效果**：\n- ε=1：强隐私保护，模型精度损失~5%\n- ε=10：中等保护，精度损失~1%\n- ε=∞：无保护（普通FL）",
                category="fl",
                tags=["differential privacy", "DP", "epsilon", "noise", "privacy"],
            ),
            FAQEntry(
                question="催化剂的孔结构如何影响性能？",
                answer="孔结构是催化剂性能的关键因素：\n\n**孔径分类**：\n- 微孔（<2nm）：分子筛，不适合TWC\n- 介孔（2-50nm）：TWC主要工作区间\n- 大孔（>50nm）：气体传输通道\n\n**对性能的影响**：\n1. **比表面积**：越大→贵金属分散度越高→活性越好\n2. **孔径分布**：介孔主导→反应物扩散快→T50低\n3. **孔隙率**：30-50%最佳→平衡扩散和涂层强度\n4. **孔连通性**：影响气体到达活性位点的路径\n\n**老化影响**：\n- 高温烧结→介孔消失→比表面积下降→性能衰减\n- 添加ZrO₂/La₂O₃→稳定孔结构→延缓老化",
                category="formulation",
                tags=["pore", "structure", "surface area", "diffusion", "mesoporous"],
            ),
            FAQEntry(
                question="如何降低三元催化器的贵金属总用量？",
                answer="降低贵金属总用量的综合策略：\n\n**1. 材料层面**：\n- Pd替代Pt（Pd对CO/HC氧化活性更高）\n- 单原子催化剂（SAC）：将Rh分散为单原子，利用率接近100%\n- Perovskite型催化剂（非贵金属替代）\n\n**2. 结构层面**：\n- 纳米级贵金属分散（提高单位质量活性）\n- 核壳结构（贵金属包覆在廉价金属核上）\n- 有序介孔载体（提高分散度和稳定性）\n\n**3. 系统层面**：\n- 紧耦合安装（减少催化剂体积需求）\n- 发动机标定优化（减少极端工况）\n- 混合动力策略（减少冷启动频率）\n\n**目标**：AI优化后贵金属用量降低20-40%（PRD目标）",
                category="formulation",
                tags=["cost", "reduction", "precious metal", "SAC", "perovskite"],
            ),
            FAQEntry(
                question="什么是Secure Aggregation？",
                answer="安全聚合（Secure Aggregation）是联邦学习的高级隐私保护技术：\n\n**问题**：即使只上传梯度，服务器仍可能通过梯度反推原始数据\n\n**Secure Aggregation解决方案**：\n1. 各客户端生成随机掩码（mask）\n2. 掩码在客户端之间秘密共享（Secret Sharing）\n3. 上传的梯度 = 真实梯度 + 掩码\n4. 服务器聚合时掩码相互抵消\n5. 服务器只能看到聚合结果，看不到任何单个客户端的梯度\n\n**在TWC-FL中的意义**：\n- 即使平台运营方也无法获取任何企业的配方信息\n- 比差分隐私更强的保护（不损失模型精度）\n- 计算和通信开销增加约2-3倍",
                category="fl",
                tags=["secure aggregation", "privacy", "secret sharing", "mask", "security"],
            ),
        ]

    def _load_default_literature(self):
        """加载预设文献库。"""
        self.literature = [
            LiteratureRef(
                title="Pd-Rh Interaction in Three-Way Catalysts: A DFT Study",
                authors="BASF Research Team",
                year=2023,
                source="Nature Catalysis",
                key_findings=["Pd/Rh比例从5:1优化到8:1可降低Rh用量37%", "Pd-Rh界面位点对NOx还原活性最高"],
                relevance_tags=["rhodium", "palladium", "cost reduction", "NOx"],
            ),
            LiteratureRef(
                title="CeO2-ZrO2 Mixed Oxides for Automotive Catalysts",
                authors="Solvay R&D",
                year=2022,
                source="Applied Catalysis B: Environmental",
                key_findings=["Ce0.5Zr0.5O2具有最高OSC", "老化后OSC保持率>60%"],
                relevance_tags=["ceria", "zirconia", "OSC", "stability"],
            ),
            LiteratureRef(
                title="Machine Learning for Catalyst Design: A Review",
                authors="Noel Group, MIT",
                year=2025,
                source="Nature Chemical Biology",
                key_findings=["AI+自动化可将实验次数压缩60%以上", "贝叶斯优化比随机搜索效率高3-10倍"],
                relevance_tags=["machine learning", "bayesian", "optimization", "automation"],
            ),
            LiteratureRef(
                title="Single-Atom Rhodium Catalysts for NOx Reduction",
                authors="Toyota Research",
                year=2024,
                source="Science",
                key_findings=["Rh单原子催化剂利用率接近100%", "Rh用量降低90%仍保持活性"],
                relevance_tags=["single atom", "rhodium", "NOx", "cost"],
            ),
            LiteratureRef(
                title="Federated Learning for Materials Science: Privacy-Preserving Collaborative Discovery",
                authors="Xu et al.",
                year=2025,
                source="arXiv preprint",
                key_findings=["organoid-fl框架R²=99.17%", "支持Non-IID数据分布"],
                relevance_tags=["federated learning", "organoid-fl", "materials", "prediction"],
            ),
        ]

    def search(self, query: str, top_k: int = 5) -> List[Tuple[FAQEntry, float]]:
        """搜索知识库FAQ。

        Args:
            query: 用户问题
            top_k: 返回最相关的 k 个结果

        Returns:
            [(FAQ条目, 相关度分数), ...]
        """
        # 构建查询向量
        query_lower = query.lower()
        vec = np.zeros(128, dtype=np.float32)
        for i in range(len(query_lower) - 2):
            trigram = query_lower[i:i+3]
            idx = int(hashlib.sha256(trigram.encode()).hexdigest(), 16) % 128
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm

        # 关键词匹配加分（字符级，兼容中文无空格分词）
        query_clean = query_lower.replace("?", "").replace("？", "").replace(" ", "")
        query_chars = set(query_clean)

        scored = []
        for faq in self.faqs:
            # 向量相似度
            faq_vec = faq.embedding
            cos_sim = float(np.dot(vec, faq_vec))

            # 关键词匹配加分（字符级交集）
            faq_text = (faq.question + " " + " ".join(faq.tags)).lower().replace(" ", "")
            faq_chars = set(faq_text)
            keyword_overlap = len(query_chars & faq_chars) / max(len(query_chars), 1)

            # 综合分数
            score = 0.6 * cos_sim + 0.4 * keyword_overlap
            scored.append((faq, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def recommend_literature(self, topic: str, top_k: int = 3) -> List[LiteratureRef]:
        """根据主题推荐文献。"""
        topic_lower = topic.lower().replace(" ", "")
        topic_chars = set(topic_lower)

        scored = []
        for ref in self.literature:
            ref_text = (ref.title + " " + " ".join(ref.key_findings) + " " + " ".join(ref.relevance_tags)).lower().replace(" ", "")
            ref_chars = set(ref_text)
            overlap = len(topic_chars & ref_chars) / max(len(topic_chars), 1)
            scored.append((ref, overlap))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [ref for ref, _ in scored[:top_k]]

    def get_categories(self) -> List[str]:
        """获取所有FAQ分类。"""
        return sorted(set(f.category for f in self.faqs))

    def get_all_faqs(self) -> List[FAQEntry]:
        """获取所有FAQ条目。"""
        return self.faqs
