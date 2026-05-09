# PAI — Philanthropic Asset Intelligence
## Gates Foundation Grand Challenges 2026 · Project 3: AI to Accelerate Charitable Giving
### Proposal Draft v1.0

---

## PART A: APPLICANT PROFILE (via SurveyMonkey Apply Portal)

### A1. Organization Information

| Field | Entry |
|-------|-------|
| **Organization Name** | [Consortium Lead: TBD — 需要非营利组织作为Primary Applicant] |
| **Organization Type** | Nonprofit Organization / Mission-Driven For-Profit |
| **Country of Registration** | [Primary Applicant所在国] |
| **U.S. Tax Status** | [Primary Applicant的税务状态] |
| **Organization Website** | https://github.com/dechang64/PAI |
| **Annual Revenue (most recent audited year)** | [Primary Applicant填写] |

### A2. Primary Contact / Authorized Official

| Field | Entry |
|-------|-------|
| **Name** | [Primary Applicant的授权官员] |
| **Title** | [Title] |
| **Email** | [Email] |
| **Phone** | [Phone] |
| **Address** | [Address] |

### A3. Principal Investigator / Project Director

| Field | Entry |
|-------|-------|
| **Name** | Prof. [TA的真实姓名] |
| **Title** | Professor of [专业方向] |
| **Organization** | Xi'an Jiaotong-Liverpool University (XJTLU) |
| **Email** | [XJTLU邮箱] |
| **Phone** | [Phone] |
| **Address** | Xi'an Jiaotong-Liverpool University, Suzhou, Jiangsu, China |

### A4. Project Overview

| Field | Entry |
|-------|-------|
| **Project Name** | PAI — Philanthropic Asset Intelligence: AI-Powered Charitable Investment Optimization, Giving Strategy & Impact Measurement |
| **Amount Requested** | USD $150,000 |
| **Project Duration** | 12 months |
| **Geographic Location(s) of Work** | China (Suzhou), United States (virtual), Global (open-source deployment) |
| **Geographic Areas Served** | Global — with initial focus on rare disease philanthropy |

---

## PART B: PROPOSAL NARRATIVE (uploaded as Word/PDF)

---

### Section 1: Executive Summary (250 words)

Charitable ecosystems suffer from three interconnected but isolated efficiency losses: **investment waste** (charity endowments systematically underperform market benchmarks — NBER 2025), **information waste** (only 33% of adults donate globally, with 4 of 5 first-time donors never returning — CAF 2024), and **impact waste** (cost-effectiveness evaluation remains fragmented and unscalable). We propose **PAI (Philanthropic Asset Intelligence)**, an open-source AI system that addresses all three simultaneously by treating charitable assets as an integrated pipeline: **invest → donate → measure**.

PAI comprises three modules: (1) **InvestOpt** — AI-powered portfolio optimization for Donor-Advised Funds (DAFs) and charity endowments, leveraging proven risk-adjusted performance metrics (Sharpe, Sortino, Jensen Alpha, VaR/CVaR) from our existing FundFL platform; (2) **GiveSmart** — an LLM-based charitable giving advisor that provides personalized donation strategies, tax optimization (appreciated securities, bunching, DAF vs. CRT), and behavioral nudges grounded in warm-glow giving theory (Andreoni 1990); and (3) **ImpactLens** — a QALY/DALY-based impact scoring system inspired by GiveWell's methodology, enabling donors to evaluate charitable projects with the rigor of health economics.

Our initial application domain is **rare disease philanthropy** — a sector where 300 million patients, 7,000+ diseases, and 95% without approved treatments (Lancet Global Health 2024) create acute need for intelligent capital allocation. PAI's federated learning architecture (built on our organoid-fl framework, 99.17% accuracy in medical imaging) ensures patient data privacy across institutional boundaries — a critical requirement for rare disease patient registries.

**Requested: $150,000 | Duration: 12 months | Open-source (MIT License)**

---

### Section 2: Problem Statement (500 words)

#### 2.1 The Three Wastes of Philanthropy

The global charitable ecosystem processes approximately $1 trillion annually, yet suffers from systemic inefficiencies at three critical junctures that are typically treated in isolation.

**Investment Waste.** Over $326 billion sits in U.S. Donor-Advised Funds (DAFs) alone (DAFgiving360, 2025), with Forbes reporting that over $250 billion is "parked" — growing faster than it is distributed. A landmark NBER study (Lo, Matveyev & Zeume, 2025) demonstrated that nonprofit endowments "badly underperform market benchmarks," finding that a zero-investment strategy (shorting charity portfolios against a simple 60/40 stock-bond mix) would have generated positive returns. This means billions in donor funds are destroyed annually through excessive fees, poor asset allocation, and governance failures — money that could have been granted to charitable causes.

**Information Waste.** The 2024 CAF World Giving Index reports that only 33% of adults globally donated money to charity, down 4 percentage points year-over-year. Of those who do give, only 5% of individual donations from high-income countries reach international causes (Gates Foundation RFP, 2026). The Fundraising Effectiveness Project (2025) reveals a first-time donor retention rate of just 19.4% — meaning 4 out of 5 new donors never return. Null (2009, cited 211 times) demonstrated that information asymmetry is a primary driver of this inefficiency: donors cannot identify causes aligned with their values, nor can they navigate the cross-border compliance barriers that block effective international giving.

**Impact Waste.** Despite the growth of effective altruism (EA) — with organizations like GiveWell providing rigorous cost-effectiveness analysis — EA-related giving represents only ~1% of global philanthropy ($10 billion of $1 trillion). GiveWell evaluates only a handful of organizations annually. The remaining 99% of charitable giving operates with minimal evidence of impact. This is particularly acute in rare disease philanthropy, where 300 million patients across 7,000+ conditions have no scalable framework for evaluating which research investments yield the greatest health returns.

#### 2.2 Why These Three Wastes Are Connected

These are not three separate problems — they are three symptoms of a single structural failure: **the absence of an integrated intelligence layer** that connects how charitable money is invested, how it is donated, and what impact it achieves. A donor who optimizes their DAF investment returns has more to give. A donor who receives personalized, evidence-based project recommendations gives more effectively. A donor who sees measurable impact returns. Currently, no system connects these three stages.

---

### Section 3: Proposed Solution (750 words)

#### 3.1 PAI System Architecture

PAI (Philanthropic Asset Intelligence) is an open-source, modular AI system that creates an integrated intelligence layer across the three stages of charitable asset management. It is built on proven open-source components from our existing research platforms.

**Module 1: InvestOpt — Charitable Investment Optimization**

InvestOpt applies AI-driven portfolio optimization to DAF and charity endowment investments. It is directly built on our **FundFL platform** (github.com/dechang64/FundFL), an open-source mutual fund analysis system that computes comprehensive risk-adjusted performance metrics including Sharpe ratio, Sortino ratio, Treynor ratio, Jensen's Alpha, Information Ratio, Calmar ratio, Value-at-Risk (VaR), Conditional VaR, and M² measure across 63 funds with 60 months of historical data.

For this project, we will extend FundFL to:
- Ingest DAF investment option data from major providers (Fidelity Charitable, Vanguard Charitable, Schwab Charitable)
- Generate personalized portfolio recommendations based on the donor's giving timeline (when they plan to grant funds)
- Optimize for risk-adjusted returns within the tax-free DAF environment
- Provide benchmarking against the NBER-documented underperformance of charity endowments

**Module 2: GiveSmart — AI Charitable Giving Advisor**

GiveSmart is an LLM-powered conversational advisor that helps donors make smarter giving decisions. It is grounded in two decades of behavioral economics research:

- **Warm-Glow Giving Theory** (Andreoni, 1990): Donors derive private utility from the act of giving itself. AI can amplify this "warm glow" through personalized storytelling and impact visualization. White et al. (2026) demonstrated that LLM dialogues increase effective charitable donations by 45.9% (N=1,949, pre-registered experiment).

- **Nudge Theory** (Thaler & Sunstein): AI can deliver personalized behavioral nudges — social proof, anchoring, default options — calibrated to individual donor psychology, avoiding the "hidden costs of nudging" identified by scientific literature (reminders that increase avoidance behavior).

GiveSmart will provide:
- Personalized donation strategy recommendations based on donor profile (risk tolerance, values alignment, tax situation)
- Tax optimization: identifying appreciated securities for donation, calculating optimal bunching amounts, comparing DAF vs. Charitable Remainder Trust (CRT) strategies
- Behavioral nudges calibrated to individual donor psychology
- Impact visualization: translating donation amounts into concrete outcomes ("Your $5,000 donation ≈ 1.7 lives saved through malaria prevention")

**Module 3: ImpactLens — Evidence-Based Impact Measurement**

ImpactLens brings health economics rigor to charitable impact assessment. It implements:
- **QALY/DALY-based scoring**: Adapting the quality-adjusted life year (QALY) and disability-adjusted life year (DALY) frameworks from health economics to evaluate charitable project cost-effectiveness
- **Morningstar-style rating system**: A 5-star rating for charitable projects based on cost per unit of impact, evidence quality, and scalability potential
- **Impact tracking dashboard**: Real-time monitoring of donation outcomes against projected impact

**Privacy Layer: Federated Learning**

All modules are built on a federated learning architecture derived from our **organoid-fl** platform (github.com/dechang64/organoid-fl), which achieves 99.17% accuracy in medical image segmentation. This ensures:
- Patient data in rare disease registries never leaves institutional servers
- Multiple hospitals and research institutions can collaboratively train models without sharing raw data
- Blockchain-based audit trail ensures training process transparency and reproducibility

#### 3.2 Why This Approach Works

PAI does not require building new AI models — it applies existing, proven AI tools (LLMs, portfolio optimization, federated learning) to a domain that lacks integrated intelligence. The Gates Foundation FAQ explicitly states: "Most successful proposals are expected to apply existing AI tools rather than build new models." PAI is precisely this.

---

### Section 4: Challenge Area Alignment (300 words)

PAI directly advances all three challenge areas specified in the RFP:

**Challenge Area 1 — Donor Discovery & Connection:** ImpactLens provides AI-powered recommendation engines that match donors to causes based on their values, risk preferences, and desired impact. GiveSmart's personalized learning tools adapt content to each donor's knowledge level and interests. Impact visualization translates abstract metrics into emotionally resonant outcomes.

**Challenge Area 2 — Convert Intent to Action:** GiveSmart reduces barriers between motivation and donation through: (a) tax optimization that increases the net value of each donation dollar, (b) streamlined giving process recommendations (DAF setup, appreciated stock donation), and (c) behavioral nudges that address the intention-action gap. The 45.9% donation increase demonstrated by White et al. (2026) validates this approach.

**Challenge Area 3 — Foundational Infrastructure:** PAI's open-source architecture provides: (a) standardized data pipelines for charitable impact metrics, (b) interoperability standards for nonprofit organizations to integrate with AI tools, and (c) federated learning infrastructure that enables privacy-preserving cross-institutional collaboration — particularly critical for rare disease patient registries where data sharing is restricted by privacy regulations.

**Relevance to Global Health & Development:** Our initial application domain is rare disease — a global health challenge affecting 300 million people, 70% of whom are children (WHO, 2025). The WEF (2026) identifies rare disease data infrastructure as a "trillion-dollar opportunity." PAI's federated learning layer directly addresses the data sharing barriers that have historically fragmented rare disease research.

---

### Section 5: Innovation & Differentiation (300 words)

PAI is differentiated from existing solutions in three fundamental ways:

**1. Integrated Pipeline vs. Point Solutions.** Existing tools address single points: GiveWell evaluates impact, Fidelity Charitable manages DAF investments, and various AI chatbots provide donation advice. PAI is the first system to connect investment optimization → donation strategy → impact measurement into a single pipeline. This integration creates network effects: better investment returns mean more to donate; better impact data motivates larger donations; more donations generate more impact data.

**2. Open-Source with Proven Components.** Unlike proprietary solutions, PAI is built on three battle-tested open-source platforms: FundFL (mutual fund analysis), organoid-fl (federated learning, 99.17% accuracy), and defect-fl (federated continual learning). This means: (a) the core technology is already validated, (b) the community can audit and extend it, and (c) deployment cost approaches zero for nonprofit organizations.

**3. Federated Learning for Philanthropy.** While federated learning has been applied to medical imaging (our own work) and tuberculosis diagnosis in Africa (arXiv 2505.14217, cited 7 times), it has never been applied to charitable giving infrastructure. PAI's federated layer enables nonprofit organizations to collaboratively build AI models without sharing sensitive donor or patient data — a capability that becomes critical as privacy regulations (GDPR, China's PIPL) increasingly restrict cross-institutional data sharing.

**Evidence of Feasibility:** White et al. (2026) have already demonstrated that LLM-based tools can increase charitable donations by 45.9%. PAI extends this proven approach with investment optimization and impact measurement — two capabilities that no existing solution integrates.

---

### Section 6: Implementation Plan & Milestones (500 words)

#### Phase 1: Foundation (Months 1-3)

| Milestone | Deliverable | Success Metric |
|-----------|-------------|----------------|
| M1.1 | InvestOpt core engine | FundFL extended with DAF portfolio optimization; 63-fund risk profiling operational |
| M1.2 | GiveSmart prototype | LLM-based donation advisor with tax optimization for appreciated securities |
| M1.3 | ImpactLens v0.1 | QALY/DALY scoring for 20+ GiveWell-evaluated charities |
| M1.4 | Federated learning layer | organoid-fl adapted for cross-institutional model training |
| M1.5 | User research | Interview 15+ DAF holders and charitable foundation managers |

#### Phase 2: Integration & Testing (Months 4-8)

| Milestone | Deliverable | Success Metric |
|-----------|-------------|----------------|
| M2.1 | PAI integrated dashboard | Streamlit-based unified interface with all three modules |
| M2.2 | GiveSmart behavioral testing | A/B test with 200+ participants measuring donation intent vs. control |
| M2.3 | InvestOpt backtesting | Portfolio recommendations backtested against 5-year DAF performance data |
| M2.4 | ImpactLens expansion | Coverage expanded to 100+ charitable organizations across health, education, environment |
| M2.5 | Federated learning pilot | 3+ institutions participating in privacy-preserving model training |

#### Phase 3: Deployment & Evaluation (Months 9-12)

| Milestone | Deliverable | Success Metric |
|-----------|-------------|----------------|
| M3.1 | Open-source release | PAI v1.0 on GitHub with MIT License, documentation, and deployment guide |
| M3.2 | Rare disease pilot | Partnership with 1+ rare disease patient organization for real-world testing |
| M3.3 | Impact evaluation | Published evaluation of PAI's effect on donation amounts and decision speed |
| M3.4 | Scalability assessment | Technical assessment for deployment across 10+ nonprofit organizations |
| M3.5 | Final report | Comprehensive report to Gates Foundation with findings, data, and recommendations |

#### Team Composition

| Role | Person | Commitment |
|------|--------|------------|
| PI / Technical Lead | Prof. [TA] (XJTLU) | 30% |
| Research Engineer | PhD Student 1 | 100% |
| Research Engineer | PhD Student 2 | 100% |
| UX Researcher | Masters Student | 50% |
| Behavioral Economist | Collaborator (TBD) | 10% |
| Rare Disease Domain Expert | Collaborator (TBD) | 10% |

---

### Section 7: Budget Narrative ($150,000)

| Category | Amount | Justification |
|----------|--------|---------------|
| **Personnel** | | |
| PI (Professor) | $15,000 | 30% effort × 12 months — technical direction, project management |
| PhD Student 1 (Research Engineer) | $36,000 | 100% effort × 12 months — InvestOpt + federated learning development |
| PhD Student 2 (Research Engineer) | $36,000 | 100% effort × 12 months — GiveSmart + ImpactLens development |
| Masters Student (UX Research) | $12,000 | 50% effort × 12 months — user research, A/B testing |
| **Equipment & Computing** | | |
| Cloud computing (GPU instances) | $12,000 | LLM inference, model training, federated learning simulation |
| Software licenses & APIs | $5,000 | LLM API access, data subscriptions |
| **Travel & Meetings** | | |
| Gates Foundation convenings | $0 | Covered separately by Gates Foundation |
| Partner meetings & field research | $8,000 | 2-3 trips for rare disease organization partnerships |
| **Supplies & Services** | | |
| User testing incentives | $6,000 | 200+ participants × $30 incentive |
| Domain expert consultation | $5,000 | Behavioral economist + rare disease expert |
| **Indirect Costs** | | |
| Institutional overhead (15%) | $15,000 | Standard XJTLU indirect cost rate |
| **TOTAL** | **$150,000** | |

---

### Section 8: Risks & Mitigation (300 words)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Academic institution eligibility** | High | Critical | Partner with eligible nonprofit as consortium lead; XJTLU as technical partner |
| **LLM hallucination in donation advice** | Medium | High | Ground all recommendations in verified data (FundFL metrics, GiveWell data, tax code); human review layer for high-stakes advice |
| **Low user adoption** | Medium | Medium | Partner with existing DAF providers or rare disease organizations for initial user base; open-source lowers adoption barrier |
| **Data availability for ImpactLens** | Medium | Medium | Start with GiveWell's publicly available data; progressively integrate charity transparency databases (Charity Navigator, GuideStar) |
| **Federated learning pilot recruitment** | Medium | Low | Leverage existing organoid-fl collaborations; rare disease community has strong motivation for privacy-preserving data sharing |
| **Scope creep** | Low | Medium | Strict milestone-based development; Phase 1 focuses on core functionality only |

---

### Section 9: Sustainability & Scalability (200 words)

**Post-Grant Sustainability:** PAI is open-source (MIT License), ensuring long-term availability regardless of continued funding. The modular architecture allows individual components (InvestOpt, GiveSmart, ImpactLens) to be adopted independently by different organizations.

**Scalability Pathway:**
- **Year 1 (this grant):** Prototype with 200+ users, 3+ institutional partners
- **Year 2:** Integration with 2-3 major DAF platforms via API partnerships
- **Year 3:** Deployment across 10+ nonprofit organizations; rare disease registry federation across 5+ countries

**Revenue Model (optional, post-grant):** While PAI itself is free, integration services, custom analytics, and enterprise deployments for large foundations could generate sustainable revenue to support continued development — without compromising the open-source core.

**Alignment with Rare Disease Foundation Vision:** PAI's architecture directly supports the long-term goal of establishing a rare disease foundation by providing: (a) investment optimization for foundation endowment, (b) donor engagement tools, and (c) evidence-based impact measurement for research funding decisions.

---

### Section 10: Organizational Capacity (200 words)

**Xi'an Jiaotong-Liverpool University (XJTLU)** is a Sino-foreign joint venture between Xi'an Jiaotong University (China's top-10 university, QS 2025) and the University of Liverpool (UK Russell Group). The PI leads a research group with demonstrated expertise in:

- **Federated Learning:** organoid-fl platform (99.17% accuracy in medical image segmentation), defect-fl (PCB defect detection), Embodied-FL (7 experimental configurations)
- **Financial AI:** FundFL (open-source mutual fund risk analysis with 63 funds, 7 risk metrics)
- **Software Engineering:** All platforms built in Rust + Python with production-grade architecture (gRPC, HNSW vector search, blockchain audit)

**Existing Infrastructure:**
- GitHub: github.com/dechang64 (organoid-fl, FundFL, defect-fl, PAI)
- Computational resources: University GPU cluster + cloud computing budget
- Student team: 2 PhD students + 1 Masters student with relevant expertise

**Consortium Partner (TBD):** We are actively seeking a nonprofit organization to serve as consortium lead and primary applicant. Candidates include rare disease patient advocacy organizations with existing donor bases and U.S. nonprofit status.

---

### Section 11: Key References

1. White, J.P., Allen, C., Caviola, L., Costello, T., & Rand, D.G. (2026). Increasing the effectiveness of charitable giving with AI-generated persuasion. *PsyArXiv*. https://osf.io/preprints/psyarxiv/6cyn4_v2
2. Andreoni, J. (1990). Impure altruism and donations to public goods: A theory of warm-glow giving. *The Economic Journal*, 100(401), 464-477.
3. Lo, A., Matveyev, A., & Zeume, S. (2025). The risk, reward, and asset allocation of nonprofit endowment funds. *NBER Working Paper*.
4. Dahiya, S. & Yermack, D. Investment returns and distribution policies of non-profit endowment funds. *ECGI Working Paper*.
5. Gates Foundation (2026). AI to Accelerate Charitable Giving. *Grand Challenges RFP*. https://gcgh.grandchallenges.org/challenge/artificial-intelligence-ai-accelerate-charitable-giving
6. WEF (2026). Making Rare Diseases Count: How Better Data Can Unlock a Trillion-Dollar Opportunity. https://reports.weforum.org/docs/WEF_Making_Rare_Diseases_Count_2026.pdf
7. Lancet Global Health (2024). The landscape for rare diseases in 2024.
8. GiveWell. Cost-Effectiveness Analysis. https://www.givewell.org/how-we-work/our-criteria/cost-effectiveness
9. CAF (2024). World Giving Index.
10. FEP (2025). Fundraising Effectiveness Project Report. afpglobal.org
11. Forbes (2025). Matching Gifts Key To Freeing Billions Stuck In Donor-Advised Funds.
12. ScienceDirect (2025). Philanthropic drug development: understanding its emerging role.
13. Peters, D. Economic Design for Effective Altruism.
14. arXiv:2505.14217. Federated learning in low-resource settings: A chest imaging study in Africa.

---

### Section 12: Supplementary Materials

| Material | Status | Link |
|----------|--------|------|
| PAI Prototype (Streamlit app) | ✅ Complete | https://github.com/dechang64/PAI |
| FundFL Platform | ✅ Complete | https://github.com/dechang64/FundFL |
| organoid-fl (Federated Learning) | ✅ Complete | https://github.com/dechang64/organoid-fl |
| defect-fl (PCB Detection) | ✅ Complete | https://github.com/dechang64/defect-fl |
| Budget Template | ✅ Attached | See Section 7 |
| PI CV | ⏳ To be prepared | — |
| Consortium Agreement | ⏳ Pending partner | — |
| Letters of Support | ⏳ To be obtained | — |

---

*Draft prepared: 2026-04-21*
*Author: PAI Research Team, XJTLU*
*Version: v1.0 — For internal review before submission*
