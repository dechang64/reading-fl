"""
Reading-FL End-to-End Demo

Simulates the full pipeline:
  1. Generate synthetic reading data for 3 campuses
  2. Train federated emotion/quality/matching model
  3. Build HNSW reader matching index
  4. Detect high-resonance excerpts (coffee sleeve candidates)
  5. Run quality prototype bank
  6. Audit chain verification

Usage:
    cd reading-fl && python scripts/demo.py              # Full demo (~30s on CPU)
    cd reading-fl && python scripts/demo.py --quick      # Quick mode (~10s)
"""

import sys
import os
import json
import time
import argparse
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from core.config import Config
from core.server import FLServer
from core.client import FLClient
from data.dataset import build_campus_datasets, TextTokenizer
from data.reflection import Reflection, BookExcerpt, EMOTION_LABELS, EMOTION_LABEL_CN
from models.reading_model import ReadingFLModel
from models.prototype_bank import QualityPrototypeBank
from matching.hnsw_index import HNSWIndex
from matching.reader_matcher import ReaderMatcher
from matching.resonance_detector import ResonanceDetector
from audit.chain import AuditChain
from audit.provenance import DataProvenance


def print_section(title: str):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ============================================================
# Synthetic data generation
# ============================================================

BOOKS = {
    "百年孤独": {
        "domain": "文学",
        "excerpts": [
            "多年以后，面对行刑队，奥雷里亚诺·布恩迪亚上校将会回想起父亲带他去见识冰块的那个遥远的下午。",
            "过去都是假的，回忆是一条没有归途的路，以往的一切春天都无法复原。",
            "生命中真正重要的不是你遭遇了什么，而是你记住了哪些事，又是如何铭记的。",
            "父母是隔在我们和死亡之间的帘子。",
            "买下一张永久车票，登上一列必然晚点的火车。",
        ],
    },
    "人类简史": {
        "domain": "历史",
        "excerpts": [
            "人类以为自己驯化了植物，实际上是植物驯化了人类。",
            "金钱是有史以来最成功的虚构故事。",
            "想象的秩序并非个人主观的想象，而是存在于千千万万人共同的想象之中。",
            "历史的铁则就是：事后看来无可避免的事，在当时看来总是毫不明显。",
            "人类和黑猩猩之间真正不同的地方就在于那些虚构的故事。",
        ],
    },
    "小王子": {
        "domain": "哲学",
        "excerpts": [
            "所有的大人都曾经是小孩，虽然，只有少数的人记得。",
            "真正重要的东西，用眼睛是看不见的。",
            "如果你驯服了我，我们就互相不可缺少了。",
            "你在你的玫瑰花身上耗费的时间使得你的玫瑰花变得如此重要。",
            "沙漠之所以美丽，是因为在它的某个角落隐藏着一口井。",
        ],
    },
    "三体": {
        "domain": "科幻",
        "excerpts": [
            "给岁月以文明，而不是给文明以岁月。",
            "弱小和无知不是生存的障碍，傲慢才是。",
            "宇宙就是一座黑暗森林，每个文明都是带枪的猎人。",
            "失去人性，失去很多；失去兽性，失去一切。",
            "死亡是一座永恒的灯塔，不管你驶向何方，最终都会朝它转向。",
        ],
    },
    "被讨厌的勇气": {
        "domain": "心理",
        "excerpts": [
            "决定我们自身的不是过去的经历，而是我们自己赋予经历的意义。",
            "一切烦恼都来自人际关系。",
            "不要害怕被别人讨厌，因为那是你自由生活的证明。",
            "人生不是与他人的比赛，而是与昨天的自己比较。",
            "所谓的自由，就是被别人讨厌。",
        ],
    },
}

REFLECTION_TEMPLATES = {
    "moved": [
        "读到这段的时候眼眶湿润了，{reason}",
        "这段话让我想起了{memory}，心里很不是滋味",
        "不知道为什么，看到这里突然很感动，也许是因为{reason}",
        "每次重读这段都有不同的感受，今天特别触动我的是{reason}",
    ],
    "thinking": [
        "作者的观点让我重新思考了{topic}这个问题",
        "这段话的逻辑很有意思，{analysis}",
        "我不同意作者的部分观点，{reason}，但整体思路值得深思",
        "这让我想到了{topic}，两者之间有微妙的联系",
    ],
    "resonance": [
        "这就是我一直在想但说不出来的感觉！{reason}",
        "完全就是我的人生写照，{reason}",
        "看到这段的时候感觉被理解了，{reason}",
        "终于有人把这种感觉写出来了，{reason}",
    ],
    "confused": [
        "这段话我没太看懂，{question}",
        "作者在这里想表达什么？{question}",
        "前后的逻辑好像有点跳跃，{question}",
        "这个比喻不太恰当吧，{reason}",
    ],
    "disagree": [
        "不同意这个观点，{reason}",
        "作者可能忽略了{factor}这个因素",
        "这种说法太绝对了，{reason}",
        "从{perspective}的角度来看，这个结论站不住脚",
    ],
    "calm": [
        "读到这里心里很平静，像被温柔地触碰了一下",
        "这段文字有一种安静的力量",
        "简单的几句话，却让人感到安宁",
        "读完这段，突然觉得很多事情没那么重要了",
    ],
}

FILLERS = {
    "reason": ["文字太真实了", "写得太好了", "感同身受", "说到了心坎里",
               "让我想起了很多事", "这种感觉很微妙", "无法用语言形容",
               "好像有人在替我说话", "每一个字都像在写我", "太戳心了"],
    "memory": ["小时候的事", "曾经的一段经历", "一个很久没见的朋友",
               "某次深夜的思考", "一段已经结束的关系", "故乡的某个场景"],
    "topic": ["人生的意义", "自由与责任", "个人与社会", "过去与未来",
              "理想与现实", "孤独与连接"],
    "analysis": ["论证方式很独特", "视角很新颖", "逻辑链条很清晰",
                 "用了一个很巧妙的类比", "层层递进很有说服力"],
    "question": ["是隐喻还是字面意思？", "这里的上下文是什么？",
                 "有没有其他可能的解释？", "这个概念在前文有定义吗？"],
    "factor": ["时代背景", "文化差异", "个体差异", "阶级因素"],
    "perspective": ["经济学", "心理学", "社会学", "历史学"],
}


def generate_campus_data(
    campus_id: str,
    campus_type: str,
    n_readers: int = 30,
    reflections_per_reader: int = 3,
    seed: int = 42,
):
    """Generate synthetic reading data for one campus."""
    rng = np.random.RandomState(seed + hash(campus_id) % 1000)

    # Campus-specific emotion bias
    bias = {
        "理工科": [0.10, 0.30, 0.15, 0.25, 0.15, 0.05],
        "文科":   [0.25, 0.15, 0.30, 0.10, 0.05, 0.15],
        "综合":   [0.18, 0.22, 0.25, 0.15, 0.08, 0.12],
    }.get(campus_type, [1/6]*6)

    reflections = []
    book_list = list(BOOKS.items())

    for reader_idx in range(n_readers):
        reader_id = hashlib.sha256(f"{campus_id}_reader_{reader_idx}".encode()).hexdigest()[:12]

        for _ in range(reflections_per_reader):
            # Pick book and excerpt
            book_title, book_info = book_list[rng.randint(0, len(book_list))]
            excerpt_text = book_info["excerpts"][rng.randint(0, len(book_info["excerpts"]))]

            # Pick emotion based on campus bias
            emotion_idx = rng.choice(6, p=bias)
            emotion_label = EMOTION_LABELS[emotion_idx]

            # Generate reflection text
            templates = REFLECTION_TEMPLATES[emotion_label]
            template = templates[rng.randint(0, len(templates))]

            # Fill in placeholders
            reflection_text = template
            for placeholder, options in FILLERS.items():
                if f"{{{placeholder}}}" in reflection_text:
                    reflection_text = reflection_text.replace(
                        f"{{{placeholder}}}", options[rng.randint(0, len(options))]
                    )

            # Reading duration (10-600 seconds)
            duration = rng.uniform(10, 600)

            excerpt = BookExcerpt(
                book_id=hashlib.md5(book_title.encode()).hexdigest()[:8],
                book_title=book_title,
                author="佚名",
                paragraph_id=str(rng.randint(1, 50)),
                text=excerpt_text,
                domain=book_info["domain"],
            )

            reflections.append(Reflection(
                reader_id=reader_id,
                campus_id=campus_id,
                excerpt=excerpt,
                reflection_text=reflection_text,
                emotion_label=emotion_label,
                reading_duration_sec=round(duration, 1),
                lamp_id=f"LAMP-{campus_id[:4].upper()}-{rng.randint(1, 99):03d}",
            ))

    return {
        "reflections": reflections,
        "campus_type": campus_type,
    }


def run_demo(quick: bool = False):
    """Run the complete Reading-FL demo."""
    np.random.seed(42)
    start_time = time.time()

    config = Config.default()
    n_readers = 20 if quick else 80
    n_rounds = 3 if quick else config.federated.num_rounds

    # ================================================================
    # Step 1: Generate Data
    # ================================================================
    print_section("Step 1: Generate Synthetic Data")
    campuses = {
        "campus_A": "理工科",
        "campus_B": "文科",
        "campus_C": "综合",
    }

    all_campus_data = {}
    total_reflections = 0
    for cid, ctype in campuses.items():
        data = generate_campus_data(cid, ctype, n_readers=n_readers, seed=42)
        all_campus_data[cid] = data
        n = len(data["reflections"])
        total_reflections += n
        print(f"  {cid} ({ctype}): {n} reflections from {n_readers} readers")
    print(f"  Total: {total_reflections} reflections")

    # ================================================================
    # Step 2: Build Datasets
    # ================================================================
    print_section("Step 2: Build FL Datasets")
    campus_datasets, tokenizer = build_campus_datasets(
        all_campus_data, max_length=128
    )
    input_dim = tokenizer.max_length * 2  # excerpt + reflection, each max_length
    print(f"  Vocabulary size: {tokenizer.actual_vocab_size}")
    print(f"  Model input dim: {input_dim}")
    for cid, ds in campus_datasets.items():
        print(f"  {cid}: {len(ds)} samples, input shape {ds.excerpt_tokens.shape}")

    # ================================================================
    # Step 3: Federated Training
    # ================================================================
    print_section("Step 3: Federated Training")
    server = FLServer(config.federated, config.model, input_dim)

    for cid, dataset in campus_datasets.items():
        ctype = all_campus_data[cid]["campus_type"]
        client = FLClient(cid, ctype, config.model, config.federated, input_dim)
        client.load_dataset(dataset)
        server.register_client(client)

    history = server.run_training(n_rounds=n_rounds)
    global_metrics = server.get_global_metrics()
    print(f"  Best emotion accuracy: {global_metrics['best_emotion_acc']:.1%}")

    # ================================================================
    # Step 4: HNSW Reader Matching
    # ================================================================
    print_section("Step 4: HNSW Reader Matching")
    matcher = ReaderMatcher(embedding_dim=config.model.embed_dim)

    # Build reader profiles from trained model embeddings
    for cid, client in server.clients.items():
        dataset = campus_datasets[cid]
        batch = dataset.get_batch(list(range(len(dataset))))
        x = np.concatenate([batch["input_ids"], batch["reflection_ids"]], axis=1)
        embeddings = client.model.predict(x)["matching"]
        reader_ids = [r.reader_id for r in all_campus_data[cid]["reflections"]]

        # Aggregate per reader (average their embeddings)
        reader_embs = {}
        for rid, emb in zip(reader_ids, embeddings):
            if rid not in reader_embs:
                reader_embs[rid] = []
            reader_embs[rid].append(emb)

        for rid, embs in reader_embs.items():
            avg_emb = np.mean(embs, axis=0)
            matcher.update_profile(rid, avg_emb)

    # Rebuild HNSW index from all profiles
    matcher.rebuild_index()

    # Test matching
    test_reader = list(matcher.profiles.keys())[0]
    similar = matcher.find_similar_readers(test_reader, k=5)
    print(f"  Indexed {len(matcher.profiles)} readers")
    print(f"  Similar to {test_reader[:8]}...:")
    for dist, rid, meta in similar:
        print(f"    {rid[:8]}... (campus={meta.get('campus','?')}, dist={dist:.3f})")

    # ================================================================
    # Step 5: Resonance Detection
    # ================================================================
    print_section("Step 5: Resonance Detection (Coffee Sleeve Candidates)")
    detector = ResonanceDetector()

    for cid, data in all_campus_data.items():
        for ref in data["reflections"]:
            detector.add_reflection(
                excerpt_id=ref.excerpt.text[:30],
                campus_id=cid,
                reader_id=ref.reader_id,
                depth_score=ref.reflection_depth,
                emotion_label=ref.emotion_label,
                quality_score=ref.reflection_depth,
            )

    top = detector.get_top_resonant(k=5)
    print(f"  Tracking {detector.get_stats()['n_excerpts_tracked']} excerpts")
    print(f"  Top 5 resonant excerpts:")
    # 审计 #3: 同时返回结构化数据, 供 2_resonance.py 直接 import 用
    top_resonant = []
    for eid, score, stats in top:
        print(f"    [{score:.3f}] \"{eid[:25]}...\" "
              f"({stats['n_reflections']} refs, {stats['n_readers']} readers, "
              f"{stats['n_campuses']} campuses)")
        top_resonant.append({
            "score": score,
            "text": eid,  # excerpt text 截断到 30 字符作为 key
            "n_refs": stats['n_reflections'],
            "n_readers": stats['n_readers'],
            "n_guilds": stats['n_campuses'],
        })

    coffee = detector.get_coffee_sleeve_candidates(k=3)
    if coffee:
        print(f"\n  ☕ Coffee sleeve candidates:")
        for eid, score, stats in coffee:
            print(f"    \"{eid[:25]}...\" score={score:.3f}")

    # ================================================================
    # Step 6: Quality Prototype Bank
    # ================================================================
    print_section("Step 6: Quality Prototype Bank")
    prototype_bank = QualityPrototypeBank(embedding_dim=config.model.embed_dim)

    # Use backbone embeddings as excerpt representations
    for cid, client in server.clients.items():
        dataset = campus_datasets[cid]
        batch = dataset.get_batch(list(range(len(dataset))))
        x = np.concatenate([batch["input_ids"], batch["reflection_ids"]], axis=1)
        embeddings = client.model.predict(x)["matching"]  # Use matching head output
        domains = [r.excerpt.domain for r in all_campus_data[cid]["reflections"]]
        qualities = dataset.quality_scores

        for i, (emb, dom, qual) in enumerate(zip(embeddings, domains, qualities)):
            prototype_bank.add_candidate(
                domain=dom,
                excerpt_id=f"{cid}_{i}",
                embedding=emb,
                quality_score=float(qual),
            )

    # Update prototypes from accumulated candidates
    prototype_bank.update_prototypes()

    print(f"  Domains: {prototype_bank.n_domains}")
    stats = prototype_bank.get_domain_stats()
    for domain, dstats in stats.items():
        print(f"    {domain}: {dstats['n_prototypes']} prototypes")

    # Score some excerpts
    sample_emb = embeddings[:5]
    sample_domains = domains[:5]
    scores = prototype_bank.score_batch(sample_emb, sample_domains)
    print(f"  Sample quality scores: {[f'{s:.3f}' for s in scores]}")

    # ================================================================
    # Step 7: Audit Chain
    # ================================================================
    print_section("Step 7: Audit Chain Verification")
    chain = AuditChain()
    provenance = DataProvenance(chain)

    # Register a lamp
    provenance.register_lamp("LAMP-CAMP-001", "campus_A")

    # Record a sample reflection
    sample_ref = all_campus_data["campus_A"]["reflections"][0]
    data_hash = chain.add_reflection({
        "text": sample_ref.reflection_text,
        "reader": sample_ref.reader_id,
    }, validator="campus_A")

    check = provenance.verify(
        reflection_text=sample_ref.reflection_text,
        reader_id=sample_ref.reader_id,
        lamp_id="LAMP-CAMP-001",
        reading_duration=sample_ref.reading_duration_sec,
        expected_chain_hash=data_hash,
    )

    print(f"  Chain: {chain.get_stats()}")
    print(f"  Verification: {check.is_authentic} (score: {check.score:.1%})")
    print(f"  Details: {check.details}")

    # ================================================================
    # Summary
    # ================================================================
    elapsed = time.time() - start_time
    print_section("✅ Summary")
    print(f"  Total time: {elapsed:.1f}s")
    print(f"  FL rounds: {len(history)}")
    print(f"  Best emotion accuracy: {global_metrics['best_emotion_acc']:.1%}")
    print(f"  Reader profiles indexed: {len(matcher.profiles)}")
    print(f"  Resonant excerpts: {detector.get_stats()['n_with_enough_data']}")
    print(f"  Quality prototypes: {prototype_bank.n_domains} domains")
    print(f"  Audit chain: {chain.get_stats()['chain_length']} blocks, valid: {chain.verify_chain()}")
    print(f"\n  All systems operational. Ready for campus deployment.")

    # 审计 #3: 返回结构化共鸣数据,供 pages/2_resonance.py 直接 import
    return top_resonant


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reading-FL Demo")
    parser.add_argument("--quick", action="store_true", help="Quick mode (fewer rounds/readers)")
    args = parser.parse_args()
    run_demo(quick=args.quick)
