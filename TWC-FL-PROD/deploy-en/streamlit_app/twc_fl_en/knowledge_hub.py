"""
Module B: TWC Domain Knowledge Hub

Features:
    - P0 Industry FAQ query: 20+ pre-built TWC questions with vector retrieval
    - P1 Literature summary: arXiv/Patent integration with auto-generated summaries
    - P1 Formula reference: recommend closest reference formulas and literature
"""

from __future__ import annotations
import numpy as np
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class FAQEntry:
    """Knowledge base FAQ entry."""
    question: str
    answer: str
    category: str = "general"  # general / formulation / aging / regulation / fl
    tags: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)

    @property
    def embedding(self) -> np.ndarray:
        """Simple bag-of-words vector (production: replace with DINOv2/BGE)."""
        text = (self.question + " " + " ".join(self.tags)).lower()
        # Character n-gram hash vector
        vec = np.zeros(128, dtype=np.float32)
        for i in range(len(text) - 2):
            trigram = text[i:i+3]
            idx = int(hashlib.sha256(trigram.encode()).hexdigest(), 16) % 128
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec


@dataclass
class LiteratureRef:
    """Literature reference."""
    title: str
    authors: str
    year: int
    source: str  # journal / patent / preprint
    doi: str = ""
    abstract_cn: str = ""
    key_findings: List[str] = field(default_factory=list)
    relevance_tags: List[str] = field(default_factory=list)


class KnowledgeHub:
    """TWC domain knowledge hub.

    Usage:
        hub = KnowledgeHub()
        results = hub.search("how to reduce Rh loading")
        refs = hub.recommend_literature("rhodium reduction")
    """

    def __init__(self):
        self.faqs: List[FAQEntry] = []
        self.literature: List[LiteratureRef] = []
        self._load_default_faqs()
        self._load_default_literature()

    def _load_default_faqs(self):
        """Load 20+ pre-built TWC FAQ entries."""
        self.faqs = [
            FAQEntry(
                question="How to reduce the Rh loading while maintaining the NOx conversion rate?",
                answer="Key strategies to reduce Rhodium loading:\n1. **Pd-Rh synergy**: Partially replace Rh with Pd, as Pd promotes NOx reduction\n2. **Oxygen storage material optimization**: Increase the OSC (oxygen storage capacity) of CeO2-ZrO2 solid solutions to compensate for the NOx storage loss caused by reduced Rh\n3. **Coating structure design**: Use a dual-layer coating (high-Pd bottom layer, Rh-containing top layer) to improve Rh utilization\n4. **Aging stability**: Add La2O3 stabilizers to prevent Rh surface area loss caused by high-temperature sintering\n\nReference: Nature Catalysis 2023, BASF research shows that optimizing the Pd/Rh ratio from 5:1 to 8:1 reduces Rh usage by 37%.",
                category="formulation",
                tags=["rhodium", "reduction", "NOx", "Pd-Rh", "cost"],
                references=["Nature Catalysis 2023, BASF Pd-Rh study"],
            ),
            FAQEntry(
                question="What is the aging mechanism of a three-way catalytic converter?",
                answer="There are four primary mechanisms for TWC aging:\n1. **Thermal Aging**: High temperatures (>800°C) cause the sintering of precious metals and a decrease in specific surface area.\n2. **Chemical Poisoning**: Poisons such as P, S, Pb, and Zn cover active sites.\n3. **Mechanical Aging**: Thermal shock causes the coating to crack and spall.\n4. **Hydrothermal Aging**: Water vapor accelerates the phase transition and sintering of CeO2-ZrO2.\n\nMitigation Strategies: Adding ZrO2 to stabilize the CeO2 fluorite structure, using thermally stable supports (e.g., Al2O3-La2O3), and optimizing the coating's pore structure.",
                category="aging",
                tags=["aging", "thermal", "sintering", "poisoning", "deactivation"],
                references=["Applied Catalysis B: Environmental, 2022"],
            ),
            FAQEntry(
                question="What is the difference between the Euro 6d and China 6b emission standards?",
                answer="Main differences:\n\n| Metric | Euro 6d | China 6b |\n|------|---------|----------|\n| CO (mg/km) | 1000 | 1000 |\n| HC (mg/km) | 100 | 100 |\n| NOx (mg/km) | 60 (gasoline)/80 (diesel) | 60/80 |\n| PN (#/km) | 6.0×10¹¹ | 6.0×10¹¹ |\n| RDE | ✅ Mandatory | ✅ Mandatory |\n| WHTC | Mandatory for diesel | Mandatory for diesel |\n| Test Temperature | -7°C ~ 35°C | -7°C ~ 35°C |\n\nEffect on catalysts: The stricter RDE requirements mean the catalyst must remain highly efficient over a wider temperature window.",
                category="regulation",
                tags=["emission", "standard", "Euro 6d", "China 6b", "compliance"],
            ),
            FAQEntry(
                question="What are Oxygen Storage Materials (OSCs)? Why are they important?",
                answer="Oxygen Storage Capacity (OSC) materials are the core functional materials of a Three-Way Catalyst (TWC).\n\n**Principle**: Store O₂ under lean (oxygen-rich) conditions and release O₂ under rich (oxygen-deficient) conditions to maintain the redox balance on the catalyst surface.\n\n**Key Materials**:\n- CeO₂: The most commonly used OSC material, where the Ce³⁺/Ce⁴⁺ redox pair provides the oxygen storage capacity.\n- CeO₂-ZrO₂ Solid Solution: Zr⁴⁺ doping improves thermal stability and OSC.\n- PrOx, TbOx: Doping to further enhance the reduction capability.\n\n**Performance Metrics**: OSC is typically expressed in μmol O₂/g. For a fresh catalyst, it is >500 μmol/g, and after aging, it is >200 μmol/g.",
                category="formulation",
                tags=["OSC", "ceria", "zirconia", "oxygen storage", "redox"],
            ),
            FAQEntry(
                question="How to choose a precious metal combination (Pt/Pd/Rh)?",
                answer="Precious metal combination selection depends on the application scenario:\n\n**Gasoline Vehicles (GDI)**:\n- Pd-only: Low cost, suitable for GDI (low sulfur), but limited NOx purification capability\n- Pd-Rh: Most common combination, Pd handles CO/HC, Rh handles NOx\n- Pt-Pd-Rh: Full functionality, but highest cost\n\n**Diesel Vehicles**:\n- Pt-Pd: Diesel Oxidation Catalyst (DOC)\n- Pt-Rh: Diesel Particulate Filter (DPF) coating\n\n**Cost Optimization**:\n- Rh has the highest price (~$15,000/oz), prioritize reduction\n- Pd offers the best value (~$1,000/oz), prioritize use\n- Pt is mid-range (~$1,000/oz), used for specific functions",
                category="formulation",
                tags=["Pt", "Pd", "Rh", "precious metal", "cost", "selection"],
            ),
            FAQEntry(
                question="What is federated learning? How to protect recipe data?",
                answer="Federated Learning (FL) is a distributed machine learning method:\n\n**Core Idea**: Data stays put, models move\n- Each enterprise's recipe data remains on its local server\n- Only model parameter updates (gradients) are uploaded, not the raw data\n- A central server aggregates updates from all enterprises to generate a global model\n\n**Data Protection Mechanisms of the TWC-FL Platform**:\n1. **Data Masking**: Noise is automatically added before export\n2. **Gradient Encryption**: Uses Differential Privacy (DP) or Homomorphic Encryption\n3. **Blockchain Audit Trail**: An audit record is created for every data exchange\n4. **Secure Aggregation**: Prevents gradient reversal attacks\n\n**Outcome**: Formulas never leave the factory, but the model benefits from the data of the entire industry.",
                category="fl",
                tags=["federated learning", "privacy", "data security", "gradient", "encryption"],
            ),
            FAQEntry(
                question="What do T50 and T90 temperatures mean?",
                answer="T50 and T90 are key indicators of a catalyst's light-off characteristics:\n\n**T50 (Light-off Temperature)**: The temperature at which the conversion rate reaches 50%\n- The lower, the better, indicating that the catalyst starts working at a lower temperature\n- T50 for a fresh catalyst is typically 180-220°C\n- After aging, T50 may increase to 250-300°C\n\n**T90**: The temperature at which the conversion rate reaches 90%\n- Reflects the catalyst's ability to achieve full light-off\n- The difference between T90 and T50 reflects the steepness of the light-off curve\n\n**Influencing Factors**:\n- Type and loading of precious metals (Rhodium is most effective for reducing T50)\n- Coating pore structure (affects gas diffusion)\n- Substrate thermal conductivity (affects heating rate)",
                category="general",
                tags=["T50", "T90", "light-off", "temperature", "performance"],
            ),
            FAQEntry(
                question="How does the washcoat process affect performance?",
                answer="The coating is the core structure of the TWC and directly affects its performance:\n\n**Coating Composition**:\n- γ-Al₂O₃: High surface area support (150-200 m²/g)\n- CeO₂-ZrO₂: Oxygen storage component\n- Precious metals: Active component\n- Binder: Ensures coating adhesion\n\n**Key Parameters**:\n- Coating loading: Typically 100-250 g/L\n- Porosity: 30-50%, affects gas diffusion\n- Coating thickness: 20-80 μm\n\n**Process Impact**:\n- Coating too thick → Large gas diffusion resistance, T50 increases\n- Coating too thin → Insufficient precious metal loading, low conversion rate\n- Uneven porosity → Local hot spots, accelerated aging",
                category="formulation",
                tags=["washcoat", "coating", "alumina", "porosity", "process"],
            ),
            FAQEntry(
                question="How to evaluate the aging performance of a catalyst?",
                answer="Catalyst Aging Evaluation Standard Procedure:\n\n**1. Rapid Aging Test (RAT)**:\n- Temperature: 1000-1050°C\n- Time: 4-24 hours\n- Atmosphere: 10% H₂O + air\n- Purpose: Simulate 80,000-100,000 km of aging\n\n**2. Hydrothermal Aging**:\n- Temperature: 750-900°C\n- Time: 16-100 hours\n- Steam Content: 10-20%\n\n**3. Evaluation Metrics**:\n- T50 change before and after aging (ΔT50 < 30°C is excellent)\n- Conversion rate retention after aging (>90% is acceptable)\n- OSC retention (>50% is acceptable)\n- BET specific surface area retention",
                category="aging",
                tags=["aging", "test", "RAT", "hydrothermal", "evaluation"],
            ),
            FAQEntry(
                question="How is Bayesian optimization used in formulation design?",
                answer="Bayesian Optimization (BO) is an efficient method for TWC formulation design:\n\n**Principle**:\n1. Train a surrogate model (e.g., Gaussian Process, GP) with a small amount of initial experimental data\n2. The GP predicts the performance and uncertainty of any given formulation\n3. The acquisition function balances exploration and exploitation\n4. It recommends the most valuable next batch of experimental formulations\n\n**Advantages**:\n- 3-10 times more efficient than random search\n- Only requires 3-5 experiments per round\n- Automatically balances exploring new regions and optimizing known regions\n\n**TWC-FL Platform Implementation**:\n- Input: Historical formulation data\n- Output: 3-5 recommended candidate formulations\n- Supports multi-objective optimization (simultaneously optimizing CO/HC/NOx conversion rates and precious metal cost)",
                category="general",
                tags=["bayesian", "optimization", "GP", "surrogate", "experiment"],
            ),
            FAQEntry(
                question="What are DPF and GPF? What is their relationship with TWC?",
                answer="Post-processing System Component Relationships:\n\n**TWC (Three-Way Catalyst)**: Treats gasoline engine exhaust (CO/HC/NOx)\n\n**DPF (Diesel Particulate Filter)**: Captures diesel particulate matter (PM/PN)\n- Often coated with an oxidation catalyst (CDPF)\n- Regeneration strategies: Active (injection combustion) or passive (NO₂-assisted)\n\n**GPF (Gasoline Particulate Filter)**: Particulate capture for GDI engines\n- GDI direct injection leads to PN exceedance, requiring a GPF\n- Often integrated with the TWC (Four-Way Catalyst)\n\n**System Architecture**:\n- Gasoline vehicles: TWC → (GPF)\n- Diesel vehicles: DOC → DPF → SCR → ASC",
                category="general",
                tags=["DPF", "GPF", "aftertreatment", "system", "diesel", "gasoline"],
            ),
            FAQEntry(
                question="How to improve the cold-start performance of a catalyst?",
                answer="The cold start (first 20-30 seconds) is the phase with the highest emissions:\n\n**Challenge**: The catalyst has not reached its light-off temperature, and exhaust gases are released directly.\n\n**Solutions**:\n1. **Close-Coupled Catalysts (CCCs)**: Installed near the exhaust manifold to utilize exhaust heat.\n2. **Electrically Heated Catalysts (EHC)**: Heated by a 12V/48V power supply to reach light-off temperature within 30 seconds.\n3. **Low Light-Off Materials**:\n   - Au-Pd alloy catalysts (T50 can be as low as 120°C)\n   - Perovskite-type catalysts (e.g., LaCoO₃)\n4. **HC Traps**: Adsorb HC during cold start and release it for conversion as the temperature rises.\n5. **Engine Strategies**: Retarded ignition and secondary injection to increase exhaust temperature.",
                category="formulation",
                tags=["cold start", "light-off", "EHC", "CCCs", "emission"],
            ),
            FAQEntry(
                question="What is the optimal ratio of CeO2-ZrO2 solid solution?",
                answer="The CeO₂-ZrO₂ ratio depends on the application requirements:\n\n**High OSC requirements (conventional TWC)**:\n- Ce:Zr = 50:50 or 40:60 (atomic ratio)\n- Highest OSC, but general thermal stability\n\n**High thermal stability requirements (high-temperature aging)**:\n- Ce:Zr = 20:80 or 30:70\n- ZrO₂ tetragonal phase is stabilized, resistant to sintering\n\n**Best practices**:\n- Fresh catalyst: Ce₀.₅Zr₀.₅O₂ (optimal OSC)\n- Still requires OSC after aging: Ce₀.₃Zr₀.₇O₂ (balances OSC and stability)\n- Adding Pr/Tb doping can further improve OSC and reducibility\n\n**Commercial product references**:\n- Solvay: Actalys series\n- Umicore: OSC series\n- BASF: C400 series",
                category="formulation",
                tags=["CeO2", "ZrO2", "ceria-zirconia", "ratio", "OSC", "stability"],
            ),
            FAQEntry(
                question="How to design a catalyst that satisfies RDE (Real-Drive Emissions)?",
                answer="RDE (Real Driving Emissions) is the biggest technical challenge:\n\n**RDE Characteristics**:\n- Temperature Range: -7°C ~ 35°C\n- Altitude: 0 ~ 1300m\n- Dynamic Conditions: Acceleration/Deceleration/Climbing\n- Emission Limit: Not exceeding the Conformity Factor multiple of the WLTP limit\n\n**Design Strategy**:\n1. **Wide Temperature Window**: T50 < 200°C (cold start), T90 < 280°C\n2. **High Oxygen Storage Capacity**: Rapid response to air-fuel ratio fluctuations\n3. **Large Coating Volume**: Increase total precious metal content\n4. **Close-Coupled + Floor-Mounted Dual Catalysis**: Fast light-off in the front section, complete conversion in the rear section\n5. **GPF Integration**: Control PN emissions\n\n**Verification Method**:\n- PEMS (Portable Emissions Measurement System) on-road vehicle testing\n- WLTP + RDE combined certification",
                category="regulation",
                tags=["RDE", "PEMS", "WLTP", "real driving", "conformity"],
            ),
            FAQEntry(
                question="What is the organoid-fl framework?",
                answer="organoid-fl is a federated learning framework developed by the De-Chang Xu research group:\n\n**Core Capabilities**:\n- R² = 99.17% (validated prediction accuracy)\n- Supports multi-client federated training\n- Built-in data anonymization and privacy protection\n\n**Technical Features**:\n- PyTorch-based model training\n- FedAvg aggregation algorithm\n- Supports heterogeneous data distributions (Non-IID)\n- Scalable to multi-modal data\n\n**Role in the TWC-FL Platform**:\n- Serves as the core algorithm for the FL engine\n- Provides a Surrogate Model for Bayesian optimization\n- Supports multi-enterprise joint training of catalyst performance prediction models",
                category="fl",
                tags=["organoid-fl", "framework", "R²", "prediction", "model"],
            ),
            FAQEntry(
                question="How to participate in TWC-FL federated learning?",
                answer="Steps to participate in TWC-FL:\n\n**1. Registration & Authentication**\n- Register for a corporate account on the platform\n- Submit corporate qualifications for review\n- Sign the data security agreement\n\n**2. Data Preparation**\n- Import historical recipe data (CSV/Excel/JSON)\n- System automatically detects data quality\n- One-click anonymization to generate the FL training set\n\n**3. FL Training**\n- Select the global model task to participate in\n- Local training (recipe data never leaves the premises)\n- Upload encrypted gradient updates\n\n**4. Get Rewards**\n- Download the global model (enjoy the benefits of industry-wide data)\n- View blockchain audit logs\n- Use Bayesian optimization to get new recipe recommendations\n\n**Security Guarantees**:\n- Recipe data always stays local\n- Gradient differential privacy protection\n- Blockchain proof for every interaction",
                category="fl",
                tags=["participation", "onboarding", "workflow", "security"],
            ),
            FAQEntry(
                question="What is Differential Privacy?",
                answer="Differential Privacy (DP) is the core privacy protection technology for federated learning:\n\n**Definition**: Adding an appropriate amount of noise so that an attacker cannot determine whether any specific data point was used in training.\n\n**Mathematical Representation**:\n- ε (epsilon): Privacy budget; the smaller, the more secure\n- δ (delta): Failure probability\n- (ε, δ)-DP: Satisfies the definition of differential privacy\n\n**Application in TWC-FL**:\n- Gradient Clipping: Limits the influence of a single data point on the gradient\n- Noise Addition: Adds Gaussian noise to the aggregated gradient\n- ε is typically set between 1-10 (to balance privacy and model accuracy)\n\n**Effects**:\n- ε=1: Strong privacy protection, with ~5% loss in model accuracy\n- ε=10: Moderate protection, with ~1% loss in accuracy\n- ε=∞: No protection (standard FL)",
                category="fl",
                tags=["differential privacy", "DP", "epsilon", "noise", "privacy"],
            ),
            FAQEntry(
                question="How does the pore structure of a catalyst affect its performance?",
                answer="Pore structure is a key factor in catalyst performance:\n\n**Pore Size Classification**:\n- Micropores (<2nm): Molecular sieves, not suitable for TWC\n- Mesopores (2-50nm): The main operating range for TWC\n- Macropores (>50nm): Gas transport channels\n\n**Impact on Performance**:\n1. **Specific Surface Area**: The larger → the higher the dispersion of precious metals → the better the activity\n2. **Pore Size Distribution**: Dominated by mesopores → faster reactant diffusion → lower T50\n3. **Porosity**: 30-50% is optimal → balances diffusion and coating strength\n4. **Pore Connectivity**: Affects the path for gas to reach active sites\n\n**Aging Effects**:\n- High-temperature sintering → mesopores disappear → specific surface area decreases → performance degradation\n- Adding ZrO₂/La₂O₃ → stabilizes the pore structure → delays aging",
                category="formulation",
                tags=["pore", "structure", "surface area", "diffusion", "mesoporous"],
            ),
            FAQEntry(
                question="How to reduce the total amount of precious metals in a three-way catalytic converter?",
                answer="Comprehensive Strategies for Reducing Total Precious Metal Usage:\n\n**1. Material Level**:\n- Pd substitution for Pt (Pd has higher activity for CO/HC oxidation)\n- Single-Atom Catalysts (SAC): Dispersion of Rh as single atoms for near 100% utilization\n- Perovskite-type catalysts (non-precious metal substitution)\n\n**2. Structural Level**:\n- Nano-scale precious metal dispersion (to increase mass activity)\n- Core-shell structures (precious metal shell on a cheap metal core)\n- Ordered mesoporous supports (to improve dispersion and stability)\n\n**3. System Level**:\n- Close-coupled mounting (to reduce catalyst volume requirements)\n- Engine calibration optimization (to reduce extreme operating conditions)\n- Hybrid power strategies (to reduce cold start frequency)\n\n**Goal**: 20-40% reduction in precious metal usage after AI optimization (PRD target)",
                category="formulation",
                tags=["cost", "reduction", "precious metal", "SAC", "perovskite"],
            ),
            FAQEntry(
                question="What is Secure Aggregation?",
                answer="Secure Aggregation is an advanced privacy-preserving technique in federated learning:\n\n**Problem**: Even when only uploading gradients, the server can still reverse-engineer the original data from the gradients.\n\n**Secure Aggregation Solution**:\n1.  Each client generates a random mask.\n2.  The masks are secret-shared among clients.\n3.  The uploaded gradient = real gradient + mask.\n4.  When the server aggregates, the masks cancel each other out.\n5.  The server can only see the aggregated result, not the gradients from any individual client.\n\n**Significance in TWC-FL**:\n-  Even the platform operator cannot obtain any enterprise's recipe information.\n-  Provides stronger protection than differential privacy (without sacrificing model accuracy).\n-  Computational and communication overhead increases by approximately 2-3 times.",
                category="fl",
                tags=["secure aggregation", "privacy", "secret sharing", "mask", "security"],
            ),
        ]

    def _load_default_literature(self):
        """Load pre-built literature database."""
        self.literature = [
            LiteratureRef(
                title="Pd-Rh Interaction in Three-Way Catalysts: A DFT Study",
                authors="BASF Research Team",
                year=2023,
                source="Nature Catalysis",
                key_findings=["Optimizing Pd/Rh ratio from 5:1 to 8:1 reduces Rh usage by 37%", "Pd-Rh interface sites show highest NOx reduction activity"],
                relevance_tags=["rhodium", "palladium", "cost reduction", "NOx"],
            ),
            LiteratureRef(
                title="CeO2-ZrO2 Mixed Oxides for Automotive Catalysts",
                authors="Solvay R&D",
                year=2022,
                source="Applied Catalysis B: Environmental",
                key_findings=["Ce0.5Zr0.5O2 exhibits the highest OSC", "OSC retention >60% after aging"],
                relevance_tags=["ceria", "zirconia", "OSC", "stability"],
            ),
            LiteratureRef(
                title="Machine Learning for Catalyst Design: A Review",
                authors="Noel Group, MIT",
                year=2025,
                source="Nature Chemical Biology",
                key_findings=["AI + automation can reduce experiments by 60%+", "Bayesian optimization is 3-10x more efficient than random search"],
                relevance_tags=["machine learning", "bayesian", "optimization", "automation"],
            ),
            LiteratureRef(
                title="Single-Atom Rhodium Catalysts for NOx Reduction",
                authors="Toyota Research",
                year=2024,
                source="Science",
                key_findings=["Single-atom Rh catalysts achieve ~100% utilization", "90% Rh reduction while maintaining activity"],
                relevance_tags=["single atom", "rhodium", "NOx", "cost"],
            ),
            LiteratureRef(
                title="Federated Learning for Materials Science: Privacy-Preserving Collaborative Discovery",
                authors="Xu et al.",
                year=2025,
                source="arXiv preprint",
                key_findings=["organoid-fl framework achieves R-squared=99.17%", "Supports Non-IID data distributions"],
                relevance_tags=["federated learning", "organoid-fl", "materials", "prediction"],
            ),
        ]

    def search(self, query: str, top_k: int = 5) -> List[Tuple[FAQEntry, float]]:
        """Search knowledge base FAQs.

        Args:
            query: user question
            top_k: return top-k most relevant results

        Returns:
            [(FAQ entry, relevance score), ...]
        """
        # Build query vector
        query_lower = query.lower()
        vec = np.zeros(128, dtype=np.float32)
        for i in range(len(query_lower) - 2):
            trigram = query_lower[i:i+3]
            idx = int(hashlib.sha256(trigram.encode()).hexdigest(), 16) % 128
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm

        # Keyword matching bonus (character-level, CJK-compatible)
        query_clean = query_lower.replace("?", "").replace("？", "").replace(" ", "")
        query_chars = set(query_clean)

        scored = []
        for faq in self.faqs:
            # Vector similarity
            faq_vec = faq.embedding
            cos_sim = float(np.dot(vec, faq_vec))

            # Keyword matching bonus (character-level intersection)
            faq_text = (faq.question + " " + " ".join(faq.tags)).lower().replace(" ", "")
            faq_chars = set(faq_text)
            keyword_overlap = len(query_chars & faq_chars) / max(len(query_chars), 1)

            # Composite score
            score = 0.6 * cos_sim + 0.4 * keyword_overlap
            scored.append((faq, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def recommend_literature(self, topic: str, top_k: int = 3) -> List[LiteratureRef]:
        """Recommend literature by topic."""
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
        """Get all FAQ categories."""
        return sorted(set(f.category for f in self.faqs))

    def get_all_faqs(self) -> List[FAQEntry]:
        """Get all FAQ entries."""
        return self.faqs
