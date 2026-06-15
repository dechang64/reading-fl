"""
Reading-FL: Federated Emotion Learning for Reading Communities

坐忘·读的智能引擎 — 隐私保护的阅读情感联邦学习系统

Architecture:
    Shared Backbone (Text Encoder) ← FL聚合
        ├── Emotion Head    (6类情感分类)   ← 本地
        ├── Quality Head    (0-1质量评分)   ← 本地
        └── Matching Head   (读者画像向量)  ← 本地

核心创新:
    - 感悟数据不出域，只共享模型参数
    - 质量原型库自动学习"什么是好内容"
    - HNSW实现段落级书友匹配
    - 区块链审计链保证感悟真实性
"""

__version__ = "1.0.0"
