# Roundtable Discussion Script

## Forum on AI & BioTech for Agriculture, Food, Drug, and Healthcare 2026

**Session:** Roundtable — Ethical & Regulatory Challenges of AI & BioTech

**Date:** May 9, 2026 · 3:40–5:00 PM

**Venue:** Rongchuang College, XJTLU

---

## Panelists

| Role | Name | Affiliation | Expertise |
|------|------|-------------|-----------|
| **Moderator** | Prof. David Chen | Rongchuang College, XJTLU | AI Ethics & Governance |
| **Panelist A** | Dr. Sarah Mitchell | John Innes Centre | Precision Agriculture & Remote Sensing |
| **Panelist B** | Prof. Hiroshi Tanaka | University of Tokyo | Food Safety & Nutritional Science |
| **Panelist C** | Dr. Elena Vasquez | Recursion Pharmaceuticals | AI-Driven Drug Discovery |
| **Panelist D** | Prof. Kwame Asante | University of Cape Town | Digital Health & Telemedicine |

---

## Opening Remarks (3 min)

**Prof. Chen (Moderator):**

Good afternoon, everyone. Welcome to the roundtable session of today's forum. I'm David Chen from Rongchuang College at XJTLU, and I'll be moderating this discussion.

Our topic today is one that sits at the intersection of technology and humanity: *Ethical and Regulatory Challenges of AI and BioTech*. This is not a theoretical exercise. Every breakthrough we've heard about today — from AI-designed crops to accelerated drug discovery — carries with it questions that society must answer: Who owns the data? Who is accountable when an algorithm makes a wrong decision? How do we ensure that the benefits of these technologies reach everyone, not just the privileged few?

We have four distinguished panelists with us, each representing a critical domain. Let me briefly introduce them before we dive in.

Dr. Sarah Mitchell leads the AI-driven crop phenotyping program at the John Innes Centre. Her work on satellite-based disease prediction has been deployed across Sub-Saharan Africa.

Prof. Hiroshi Tanaka from the University of Tokyo is a leading voice in AI-powered food safety. His lab developed one of the first real-time contaminant detection systems used in Japanese food processing.

Dr. Elena Vasquez heads the computational biology team at Recursion Pharmaceuticals, where she has overseen the progression of three AI-discovered drug candidates into clinical trials.

Prof. Kwame Asante directs the Digital Health Initiative at the University of Cape Town. He has been instrumental in deploying telemedicine platforms across rural South Africa and advising the WHO on AI governance in low-resource settings.

Welcome, all. Let's begin.

---

## Part 1: Data Privacy and Ownership (15 min)

**Prof. Chen:**

Let me start with a question that cuts across all four of your domains. Data is the fuel of AI. But in agriculture, food, pharma, and healthcare, that data is deeply personal, commercially sensitive, or both. Dr. Mitchell, let me begin with you. When a farmer's field data — soil composition, yield history, pest patterns — is collected by an AI platform, who does that data belong to?

**Dr. Mitchell:**

Thank you, David. This is perhaps the most contentious issue in agricultural AI right now. Farmers generate enormous amounts of data through IoT sensors, drones, and satellite imagery. The problem is that most data collection agreements are buried in terms of service that farmers don't read and can't negotiate.

In the EU, the proposed EU Data Act attempts to give farmers some rights over their machine-generated data. But in practice, the power asymmetry is enormous. A smallholder farmer in Kenya using a free pest-prediction app may not even realize that their location data, crop choices, and spraying schedules are being aggregated and sold to commodity traders.

I think we need a fundamental rethinking. Data generated on a farmer's land, about that farmer's crops, should belong to the farmer — full stop. The AI company can have a license to use it, but only with informed, ongoing consent.

**Prof. Tanaka:**

I'd push this even further. In food safety, the data chain is incredibly complex. Consider a simple contamination alert: it involves data from the farm, the processor, the distributor, the retailer, and the consumer. Each entity has different incentives and different legal obligations.

In Japan, we've seen cases where AI-powered inspection systems detected contamination that the manufacturer chose not to report, because the data was considered "internal quality control information" rather than a regulatory obligation. The algorithm was doing its job, but the governance framework around it was inadequate.

The question isn't just "who owns the data" — it's "who has the obligation to act on what the data reveals." That's a regulatory gap that current food safety laws in most countries don't adequately address.

**Prof. Chen:**

Dr. Vasquez, in pharma, the stakes are even higher. Clinical trial data involves human subjects.

**Dr. Vasquez:**

Absolutely. And here we face a paradox. On one hand, we desperately need more data sharing to train better drug discovery models. The reason AlphaFold was so successful is that it had access to the entire Protein Data Bank — decades of publicly funded structural biology. On the other hand, patient data in clinical trials is protected by some of the strictest privacy regulations in the world: HIPAA in the US, GDPR in Europe.

At Recursion, we've invested heavily in synthetic data generation — creating artificial patient profiles that preserve the statistical properties of real clinical data without containing any actual patient information. It's a promising approach, but it's not a silver bullet. Synthetic data can inherit and even amplify biases present in the original dataset. If your training data underrepresents certain ethnic groups, your synthetic data will too, and any drug discovered using that data may have differential efficacy across populations.

**Prof. Asante:**

I want to bring this back to the global equity dimension. When we talk about data privacy, we're usually talking about regulations designed in and for wealthy countries. GDPR, HIPAA — these are excellent frameworks, but they assume a certain level of digital literacy and regulatory infrastructure that doesn't exist in most of the world.

In my work deploying telemedicine in rural South Africa, I've seen patients who can't read, signing consent forms for AI-powered diagnostic tools with a thumbprint. Is that informed consent? Legally, maybe. Ethically, absolutely not.

And here's the other side: if we impose such strict data requirements that AI health tools can't be deployed in low-resource settings, we're denying those populations access to potentially life-saving technology. There's a cruel irony in applying privacy protections so rigidly that they become a barrier to healthcare access.

**Prof. Chen:**

That's a powerful point. So we're caught between two risks: the risk of exploiting vulnerable populations through inadequate consent, and the risk of denying them access through over-regulation. How do we navigate that?

**Prof. Asante:**

I think the answer is proportional governance. Not all AI health tools carry the same risk. A chatbot that provides general health information should not be subject to the same regulatory burden as an AI system that makes treatment recommendations for cancer patients. We need a tiered framework that matches regulatory requirements to the actual risk and impact of the technology.

**Dr. Mitchell:**

I agree. In agriculture, we've been advocating for something similar. An AI tool that recommends when to water your tomatoes doesn't need the same oversight as an AI system that controls automated pesticide spraying. Risk-proportionate regulation is the only scalable approach.

---

## Part 2: Algorithm Transparency and Accountability (15 min)

**Prof. Chen:**

Let's move to our second major theme: transparency. AI models, especially deep learning models, are often described as "black boxes." When an AI system makes a decision that affects human health or livelihood, how much does it need to explain itself? Dr. Vasquez, let's stay with you.

**Dr. Vasquez:**

This is the single biggest challenge in AI drug discovery. When our model identifies a molecule as a promising drug candidate, it's making that prediction based on patterns learned from millions of data points across hundreds of dimensions. We can't always articulate *why* it chose that particular molecular structure.

Regulators like the FDA are increasingly asking for mechanistic explanations — not just "this molecule works" but "here's the biological pathway through which it works." That's entirely reasonable. But it creates a tension: some of the most powerful AI models are the least interpretable.

I think the solution lies in a two-track approach. First, invest in explainability research — techniques like attention visualization, feature importance analysis, and mechanistic interpretability. Second, accept that for some applications, empirical validation matters more than theoretical explanation. If a drug candidate shows efficacy in preclinical models and early-stage trials, the fact that we can't fully explain the AI's reasoning shouldn't necessarily block its progression.

**Prof. Tanaka:**

In food safety, transparency is both a technical and a consumer trust issue. We've developed AI systems that can detect adulteration in olive oil with 98% accuracy using near-infrared spectroscopy. But when we tried to deploy this in Italian markets, producers rejected it — not because the technology didn't work, but because they didn't trust a system they couldn't understand.

We learned that transparency isn't just about opening the black box. It's about building trust through engagement. We started holding workshops with producers, showing them how the system works in plain language, letting them test it with their own samples. Trust came not from understanding the algorithm, but from seeing it work reliably in practice.

**Dr. Mitchell:**

In agriculture, we face a different transparency challenge. Many of the AI models used in precision agriculture are proprietary — developed by companies like John Deere, Bayer, and Climate Corporation. Farmers are asked to trust recommendations without being able to examine the underlying model.

This creates a dependency problem. If a farmer doesn't understand *why* the AI recommends a particular planting schedule or fertilizer application, they lose the ability to make independent agronomic judgments. Over time, this erodes farming expertise and creates lock-in to specific platforms.

I've been advocating for mandatory model documentation — something like a "nutrition label" for AI models in agriculture. It wouldn't reveal proprietary algorithms, but it would disclose: What data was the model trained on? What are its known limitations? In what conditions has it been validated? What is its accuracy across different crop types and climates?

**Prof. Asante:**

In healthcare, transparency intersects with liability in uncomfortable ways. If an AI diagnostic tool misdiagnoses a patient, who is responsible? The doctor who relied on it? The company that built it? The hospital that deployed it?

Right now, the legal framework is completely inadequate. Most AI health tools are classified as "clinical decision support" software, which carries lower regulatory requirements than medical devices. But in practice, these tools are making decisions that directly affect patient care.

I think we need to establish clear liability frameworks before, not after, these tools cause harm. The aviation industry did this brilliantly — every component has a traceable chain of responsibility. We need the same for AI in healthcare.

**Prof. Chen:**

That's an excellent analogy. The aviation industry also has a culture of incident reporting — near-misses are studied and learned from, not hidden. Do you think a similar culture could work for AI in health and biotech?

**Prof. Asante:**

Absolutely. But it requires legal safe harbors. Right now, if a hospital reports that an AI tool made an error, they risk litigation. So errors get quietly corrected or, worse, not reported at all. We need mandatory adverse event reporting for AI in healthcare, combined with legal protections for good-faith reporting.

**Dr. Vasquez:**

The same applies in pharma. If an AI model generates a toxic compound that passes initial screening, we need to know about it — not to punish anyone, but to improve the models. A shared database of AI failures in drug discovery would be enormously valuable, but no company wants to be the first to contribute to it.

---

## Part 3: Equity, Access, and the Global Divide (12 min)

**Prof. Chen:**

Our third theme is one that I think doesn't get enough attention in these discussions: who benefits? AI and biotech are expensive. The compute power, the data infrastructure, the talent — it's all concentrated in a handful of countries and companies. Prof. Asante, you've been vocal about this.

**Prof. Asante:**

I have, because I see the consequences every day. Let me give you a concrete example. There are over 2,000 AI-powered health applications approved or in development globally. How many of those have been validated on African populations? Fewer than 5 percent.

This isn't just an equity issue — it's a scientific one. AI models trained predominantly on data from European and East Asian populations may perform poorly on African genetic diversity, which is greater than all other populations combined. An AI diagnostic tool that works brilliantly in London may be dangerously inaccurate in Lagos.

The same pattern repeats in agriculture. Most crop prediction models are trained on data from temperate climates. When deployed in tropical regions, their accuracy drops significantly. Smallholder farmers in developing countries are being asked to adopt AI tools that weren't designed for their conditions.

**Dr. Mitchell:**

And it's not just about validation — it's about who sets the research agenda. The vast majority of AI-agriculture research focuses on commodity crops: wheat, corn, soy. These are the crops that generate data and profits. But the crops that matter most for food security in developing countries — cassava, millet, sorghum, cowpea — receive a fraction of the attention.

I've been working on a cassava disease detection system using smartphone cameras. The technology works well, but getting funding for it is incredibly difficult compared to, say, a wheat yield prediction model. The market incentives are misaligned with the humanitarian need.

**Prof. Tanaka:**

In food technology, we see a similar pattern. Personalized nutrition is a hot topic — AI systems that analyze your microbiome and recommend tailored diets. But these systems cost hundreds of dollars and require sophisticated lab analysis. They're accessible to affluent consumers in developed countries and completely out of reach for the 2 billion people who are food-insecure.

There's something deeply uncomfortable about deploying AI to optimize the diet of someone who already eats well, while ignoring the basic nutritional needs of those who don't.

**Dr. Vasquez:**

In drug discovery, the inequity is perhaps most stark. The diseases that cause the most suffering globally — malaria, tuberculosis, neglected tropical diseases — receive a tiny fraction of AI-driven drug discovery investment compared to oncology and rare diseases that affect wealthy markets.

AI could be a powerful equalizer here — it could dramatically reduce the cost of drug discovery, making it feasible to develop treatments for diseases that aren't commercially attractive. But that will only happen if we deliberately direct AI capabilities toward these problems, rather than letting market forces alone determine the research agenda.

**Prof. Chen:**

So the question becomes: is this a problem that the technology itself can solve, or does it require policy intervention?

**Prof. Asante:**

Both. On the technology side, we need initiatives like federated learning — which allows models to be trained on distributed datasets without centralizing sensitive data. This could enable AI models to learn from diverse global populations while respecting data sovereignty.

On the policy side, we need funding mechanisms that specifically support AI development for underserved populations and neglected diseases. Something like a Global AI Equity Fund, modeled on the Global Fund to Fight AIDS, Tuberculosis and Malaria.

**Dr. Mitchell:**

And we need capacity building. It's not enough to develop AI tools for developing countries — we need to train the next generation of AI researchers in those countries. Otherwise, we're perpetuating a neo-colonial model where the Global North develops the technology and the Global South merely consumes it.

---

## Part 4: Governance, Regulation, and the Path Forward (10 min)

**Prof. Chen:**

Let's turn to our final theme: what should be done? We've identified the problems — privacy gaps, transparency deficits, equity failures. Now let's talk solutions. If each of you could advocate for one specific policy change or governance mechanism, what would it be?

**Dr. Mitchell:**

For agriculture, I'd advocate for a global AI in Agriculture Code of Conduct, developed under the auspices of the FAO. It would establish minimum standards for data rights, model transparency, and farmer consent. Voluntary for now, but with a pathway toward becoming a condition of access to international agricultural markets.

**Prof. Tanaka:**

For food safety, I'd push for mandatory algorithmic auditing. Just as food processing plants undergo regular safety inspections, AI systems used in food production and safety should undergo periodic independent audits — checking for bias, accuracy, and compliance with safety standards. The audit results should be publicly available.

**Dr. Vasquez:**

In pharma, I'd advocate for a regulatory sandbox framework — a controlled environment where AI-discovered drug candidates can be tested with reduced regulatory burden, but with enhanced monitoring and data sharing requirements. This would accelerate innovation while maintaining safety. The UK's MHRA has been experimenting with this approach, and the early results are promising.

**Prof. Asante:**

For healthcare, my one ask is this: establish an international AI health safety reporting system, modeled on pharmacovigilance systems for pharmaceuticals. Every hospital, clinic, and health system that uses AI diagnostic or treatment tools should be required to report adverse events to a central database. This would create the evidence base we need for proportionate, evidence-based regulation.

**Prof. Chen:**

Those are four concrete, actionable proposals. Let me ask a follow-up: what role should universities play in this governance ecosystem?

**Dr. Vasquez:**

Universities are uniquely positioned because they combine technical expertise with relative independence from commercial pressures. They should be the ones developing the standards, conducting the audits, and training the regulators. But they need to be adequately funded for this role. Right now, most AI ethics research is underfunded compared to AI capability research.

**Prof. Tanaka:**

I'd add that universities should also be spaces for critical reflection — not just training students to build AI systems, but teaching them to question when and whether those systems should be built. Ethics can't be an afterthought or a standalone course. It needs to be embedded in every AI and biotech curriculum.

**Prof. Asante:**

And universities in the Global South need to be equal partners in this, not just recipients of Northern expertise. The challenges of AI governance in Africa, Southeast Asia, and Latin America are different, and the solutions need to be locally informed.

---

## Closing Remarks (5 min)

**Prof. Chen:**

Let me try to weave together the threads of our discussion.

We started with data — who owns it, who controls it, who benefits from it. We heard that current frameworks are inadequate, that consent is often illusory, and that the data divide mirrors and amplifies existing global inequalities.

We moved to transparency — the black box problem. We heard that transparency isn't just a technical challenge but a trust challenge, that model documentation should be as standard as nutrition labels, and that we need cultures of reporting rather than cultures of concealment.

We discussed equity — the uncomfortable reality that AI and biotech, for all their transformative potential, risk widening the gap between the haves and have-nots. We heard compelling arguments for deliberate, policy-driven efforts to direct these technologies toward the problems that matter most.

And finally, we talked about governance — concrete proposals for codes of conduct, algorithmic auditing, regulatory sandboxes, and safety reporting systems. Proposals that are ambitious but achievable.

I want to leave you with one thought. The technologies we've discussed today are not inevitable. They are choices — choices about what to build, how to deploy it, and who benefits. The ethical and regulatory frameworks we put in place today will shape those choices for decades to come. The question is not whether AI and biotech will transform agriculture, food, medicine, and healthcare — they will. The question is whether that transformation will be just, equitable, and accountable.

Thank you to our panelists for a rich and thought-provoking discussion. Thank you to our audience for your attention. I encourage you to continue these conversations beyond today's forum.

---

*End of Roundtable Discussion*

---

**Forum on AI & BioTech for Agriculture, Food, Drug, and Healthcare 2026**
*Rongchuang College, XJTLU · May 9, 2026*
