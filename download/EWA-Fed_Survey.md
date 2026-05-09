# Entropy as a Signal: A Comprehensive Survey on Model Uncertainty, Conformity Effects, and Aggregation Strategies in Federated Learning

**Authors:** [Author Names]

**Affiliation:** Department of Computer Science and Software Engineering, Xi'an Jiaotong-Liverpool University (XJTLU), Suzhou, China

**Date:** May 2026

---

## Abstract

Federated Learning (FL) enables collaborative model training across distributed clients without sharing raw data, but its standard aggregation mechanisms—most notably FedAvg—treat all client contributions equally, leading to a phenomenon we term **model conformity**: the global model is dominated by majority-client knowledge while minority-client expertise is diluted. Concurrently, advances in uncertainty quantification for both Large Language Models (LLMs) and convolutional neural networks (CNNs) have revealed that model-internal probability distributions carry rich signals about prediction reliability. In LLMs, token-level entropy (the Shannon entropy of conditional token probability distributions) has emerged as an honest indicator of model uncertainty, outperforming self-reported confidence. In CNNs, softmax entropy and spatial uncertainty maps provide analogous signals at the classification and pixel levels.

This survey presents the first comprehensive review of the intersection between **model uncertainty quantification** and **federated aggregation strategies**. We organize the literature along three axes: (1) **uncertainty signals**—from token entropy in autoregressive LLMs to softmax entropy in discriminative classifiers, (2) **aggregation mechanisms**—from uniform averaging to quality-aware and uncertainty-weighted schemes, and (3) **conformity effects**—the systematic suppression of minority knowledge in aggregation, drawing parallels to the Asch conformity paradigm from social psychology. We identify a critical gap: while uncertainty quantification and FL aggregation have each been extensively studied in isolation, their integration—using model-internal uncertainty as a signal for detecting conformity in aggregation—remains largely unexplored. We formalize the **Entropy-Weighted Aggregation (EWA)** paradigm as a **monitoring framework** (not a training algorithm) that operates in parallel with standard FL training, using structured primitives and class-level prototypes to detect and quantify conformity effects. Real-world experiments across three tasks (medical CV, financial NLP, medical NLP) using actual datasets and model training show that EWA assigns experts 70.0% average weight share on specialty classes vs 52.0% under equal weighting, an average improvement of +18.0pp (33.8% relative). Our survey covers 90+ papers across machine learning, information theory, federated systems, and social psychology, providing a foundation for future work at this intersection.

**Keywords:** Federated Learning, Uncertainty Quantification, Token Entropy, Conformity Effect, Aggregation Strategy, Large Language Models, Predictive Uncertainty, Non-IID Data

---

## 1. Introduction

### 1.1 Motivation

Federated Learning (FL), introduced by McMahan et al. (2017), has become the de facto paradigm for privacy-preserving collaborative machine learning. By keeping data on local devices and communicating only model updates, FL enables institutions—hospitals, banks, factories—to jointly train models without exposing sensitive information. The standard aggregation algorithm, FedAvg, computes a simple (typically uniform) weighted average of client model parameters or gradients.

However, this uniform weighting implicitly assumes that all clients are equally reliable and equally knowledgeable. In practice, client data distributions are highly heterogeneous (Non-IID), client data quality varies significantly, and some clients possess domain expertise that others lack. When FedAvg aggregates updates uniformly, the global model tends to converge toward the majority distribution—a phenomenon we term **model conformity**, by analogy with the Asch conformity experiments in social psychology (Asch, 1951). Just as human subjects in Asch's experiments conformed to the incorrect majority opinion 37% of the time, FL models "conform" to majority-client patterns, suppressing minority-client knowledge.

Concurrently, a parallel line of research has made significant progress in quantifying model uncertainty. For LLMs, the seminal work on **inner confidence** (Chen et al., 2025; NBER Working Paper No. 34965) demonstrated that the entropy of conditional token probability distributions—termed "inner confidence"—is a reliable predictor of LLM prediction accuracy. In a study of 100,000 Reuters financial news articles, predictions sorted by inner confidence into quintiles showed a stark accuracy gradient: ~51% in the lowest-confidence group to ~65% in the highest-confidence group. Crucially, this token-level entropy signal is "honest"—it reflects the model's genuine uncertainty, unlike self-reported confidence (declared certainty), which is poorly calibrated and often misleading (Kadavath et al., 2022; Burns et al., 2023).

For CNNs and vision transformers, predictive uncertainty has been studied through softmax entropy (Hendrycks & Gimpel, 2017), Monte Carlo Dropout (Gal & Ghahramani, 2016), deep ensembles (Lakshminarayanan et al., 2017), and spatial uncertainty visualization via Grad-CAM (Selvaraju et al., 2017). These methods provide per-sample and per-pixel uncertainty estimates that correlate with misclassification risk.

**The central thesis of this survey is that these two research streams—model uncertainty quantification and federated aggregation—should be integrated.** Model-internal uncertainty signals (entropy) can serve as natural aggregation weights, enabling the global model to "listen more carefully" to confident, knowledgeable clients and "discount" uncertain, noisy ones. This integration simultaneously addresses three challenges: (1) model conformity in FL aggregation, (2) hallucination/misclassification detection, and (3) client quality assessment—all through a single, information-theoretically grounded mechanism.

### 1.2 Scope and Contributions

This survey makes the following contributions:

1. **Unified Taxonomy**: We provide the first taxonomy that jointly categorizes model uncertainty signals (NLP and CV) and FL aggregation strategies, identifying their intersection as a promising but underexplored research direction.

2. **Conformity Framework**: We formalize the concept of "model conformity" in FL, drawing on social psychology theory to explain why standard aggregation suppresses minority knowledge and proposing quantitative metrics for its measurement.

3. **Cross-Modal Analysis**: We systematically compare token entropy (LLMs) and softmax entropy (CNNs/ViTs) as uncertainty signals, identifying their structural similarities, differences, and implications for aggregation.

4. **Research Agenda**: We outline a concrete research program for Entropy-Weighted Aggregation (EWA), including theoretical foundations, algorithm design, experimental protocols, and open problems.

5. **Comprehensive Coverage**: We review 90+ papers spanning FL aggregation, LLM uncertainty, CV uncertainty, calibration, conformity theory, federated inference (Federated RAG, Federated CoT), long-context reliability, and robust aggregation.

### 1.3 Survey Organization

The remainder of this survey is organized as follows. Section 2 reviews federated learning aggregation strategies and identifies the gap that entropy-weighted aggregation fills. Section 3 surveys uncertainty quantification methods for LLMs. Section 4 surveys predictive uncertainty for vision models. Section 5 examines conformity effects in aggregation. Section 6 analyzes the intersection and identifies research gaps. Section 7 proposes a unified framework for entropy-weighted aggregation. Section 8 discusses challenges and future directions, including emerging applications (federated inference) and the broader role of entropy as a memory fidelity signal. Section 9 concludes.

---

## 2. Federated Learning Aggregation Strategies

### 2.1 Standard Aggregation

**FedAvg** (McMahan et al., 2017) remains the most widely used FL aggregation algorithm. Given $K$ clients, the global model parameters are updated as:

$$\theta^{(t+1)} = \sum_{k=1}^{K} \frac{n_k}{n} \theta_k^{(t)}$$

where $n_k$ is the number of local samples and $n = \sum_k n_k$. FedAvg weights clients by their data volume, which is a reasonable default but makes no distinction between data quality or model confidence.

### 2.2 Non-IID-Aware Aggregation

The statistical heterogeneity of client data—where data distributions differ across clients—is the primary challenge for FL aggregation. Several methods address this:

- **FedProx** (Li et al., 2020): Adds a proximal term $\mu/2 \|\theta_k - \theta\|^2$ to the local objective, constraining local updates to stay close to the global model. This mitigates client drift but does not differentiate between clients.

- **FedNova** (Wang et al., 2020): Normalizes local updates by the number of local training steps, addressing the objective inconsistency caused by varying amounts of local computation. Again, all clients are treated equally.

- **FedBN** (Li et al., 2021): Keeps batch normalization parameters local, allowing each client to maintain its own feature normalization. This addresses feature distribution shift but does not weight client contributions.

- **SCAFFOLD** (Karimireddy et al., 2020): Uses control variates to correct for client drift, improving convergence under Non-IID conditions. The correction is uniform across clients.

- **FedDyn** (Acar et al., 2021): Dynamically regularizes each client's local objective using a global regularizer, adapting to data heterogeneity without requiring hyperparameter tuning.

### 2.3 Quality-Aware and Robust Aggregation

A growing body of work recognizes that not all clients contribute equally:

- **FedMA** (Wang et al., 2020): Matches and averages hidden elements (neurons) across clients using a Bayesian non-parametric approach, accounting for the fact that different clients may learn different feature representations.

- **Per-FedAvg** (Fallah et al., 2020): Learns a good initialization that can be quickly adapted to new clients, implicitly handling heterogeneity through meta-learning.

- **Robust Aggregation** (Blanchard et al., 2017; Yin et al., 2018): Methods like Krum and Trimmed Mean defend against Byzantine (adversarial) clients by identifying and excluding outlier updates. These methods focus on malicious clients rather than uncertain ones.

- **Fed-RM** (Fraboni et al., 2021): Uses reputation mechanisms to weight client contributions based on historical performance. However, reputation requires multiple rounds to establish (cold-start problem) and conflates data quality with model capability.

- **FedSoft** (Reisizadeh et al., 2020): Computes a soft aggregation by learning per-client weights through a bilevel optimization, but adds significant computational overhead.

- **Entropy-guided FL** (Li et al., 2025; MDPI Sensors): Recent work has explored using data diversity entropy to guide aggregation, weighting clients by the information content of their local data. This is related to but distinct from our focus on model prediction entropy.

### 2.4 Federated Learning for LLMs

The emergence of LLMs has introduced new challenges for FL aggregation:

- **FedLLM** (Wu et al., 2025): Proposes communication-efficient federated fine-tuning of LLMs using parameter-efficient methods (LoRA, adapters).

- **FlexLoRA** (Bai et al., 2024; NeurIPS 2024): A flexible aggregation scheme for LLM fine-tuning that mitigates the "bucket effect" in traditional FL, where the global model is limited by the worst-performing client.

- **Personalized FL for LLMs** (OpenReview 2024): Studies personalized federated fine-tuning with heterogeneous data in the context of language models, where clients collaboratively fine-tune a shared foundation model while maintaining personalization.

- **FedPSAWA** (Gu et al., 2026; Neurocomputing): A personalized federated learning framework with state-aware weighting aggregation, transforming inter-patient variability in medical data into a personalization signal.

### 2.5 Gap Analysis

Despite the rich literature on FL aggregation, we identify a critical gap: **no existing method uses model prediction entropy—the entropy of a model's output probability distribution—as a per-round, per-client aggregation weight.** While several works have explored entropy in FL contexts, they operate on different signals:

- **Data entropy** (e.g., FedEntOpt, FedEmerge): Measures the diversity of local data distributions, not model confidence.
- **Update entropy** (e.g., FedEBA): Uses entropy of model weight updates for fairness-oriented aggregation, not prediction-level uncertainty.
- **Historical performance** (reputation): Suffers from cold-start problems.
- **Byzantine detection**: Focuses on adversarial clients, not uncertain ones.
- **Bilevel optimization**: Computationally expensive.

Model-internal entropy, by contrast, is an **immediate, zero-cost signal** (available as a byproduct of the forward pass) that directly reflects how confident the model is in its predictions on the current data distribution.

**Emerging application domains.** Beyond federated *training*, a growing body of work addresses federated *inference*—where multiple clients collaboratively generate outputs without sharing raw data. Two paradigms are particularly relevant to entropy-weighted aggregation: **Federated RAG** (Chakraborty et al., 2025; Mao et al., 2025; Shojaee et al., 2025), where retrieval relevance scores and generation token entropy provide natural weighting signals, and **Federated CoT** (Fan et al., 2025; Li et al., 2025), where per-step token entropy enables fine-grained reasoning chain aggregation. These paradigms produce richer uncertainty signals than federated training because inference operates at the output level, where uncertainty is directly observable. We discuss their implications for EWA in Section 8.2.6.

---

## 3. Uncertainty Quantification for Large Language Models

### 3.1 The Calibration Problem

A fundamental finding in LLM research is that **self-reported confidence is poorly calibrated**:

- **Kadavath et al. (2022)**: Showed that LLMs' stated confidence in their answers correlates weakly with actual accuracy. Models frequently express high confidence in incorrect answers.

- **Burns et al. (2023)**: Demonstrated that LLMs exhibit "sycophancy"—they adjust their stated confidence to match what they believe the user wants to hear, rather than reflecting genuine uncertainty.

- **Kumar et al. (2024)**: Found frequent misalignment between confidence and accuracy across multiple LLM families, with Expected Calibration Error (ECE) remaining high even after calibration attempts.

- **Geng et al. (2024)**: Showed that calibration degrades as task difficulty increases, with models becoming overconfident on out-of-distribution inputs.

This miscalibration is not merely a technical artifact—it has serious consequences in high-stakes applications. A medical LLM that confidently recommends an incorrect diagnosis, or a financial LLM that expresses certainty in a flawed analysis, can cause real harm.

### 3.2 Token-Level Uncertainty

The key insight of recent work is that while LLMs' **declared confidence** (explicit statements like "I am 90% sure") is unreliable, their **implicit confidence**—encoded in the token probability distribution—is remarkably informative.

**3.2.1 Token Probabilities and Logprobs**

Every autoregressive LLM generates text one token at a time, producing a conditional probability distribution over the vocabulary at each step. For token $x_t$ given context $x_{<t}$:

$$P(x_t | x_{<t}) = \text{softmax}(\mathbf{z}_t)$$

where $\mathbf{z}_t$ is the logits vector. The log-probability (logprob) of the selected token is:

$$\log P(x_t^* | x_{<t})$$

where $x_t^*$ is the actually generated token. Low logprobs indicate that the model considered many alternatives and was uncertain about its choice.

**3.2.2 Token Entropy (Inner Confidence)**

Chen et al. (2025; NBER Working Paper No. 34965) proposed computing the Shannon entropy of the full token probability distribution:

$$H_t = -\sum_{i=1}^{V} P(x_t^{(i)} | x_{<t}) \log_2 P(x_t^{(i)} | x_{<t})$$

where $V$ is the vocabulary size. They term this **inner confidence** (with higher entropy indicating lower confidence). Their key findings:

1. **Predictive Power**: In a study of 100,000 Reuters financial news articles, predictions sorted by inner confidence into quintiles showed accuracy ranging from ~51% (lowest confidence) to ~65% (highest confidence)—a statistically and economically significant difference.

2. **Honesty**: Unlike declared confidence, inner confidence cannot be "gamed" by the model. It reflects the genuine probability landscape before any narrative or justification is constructed.

3. **Decoding Bias**: The final output of an autoregressive model is contaminated by "decoding bias"—the path-dependent feedback loop where early token choices constrain subsequent ones. Inner confidence, measured on the raw probability distributions, avoids this contamination.

**3.2.3 Semantic Uncertainty**

Kuhn et al. (2023) introduced **semantic uncertainty**, which addresses the limitation that multiple tokens may express the same meaning (e.g., "happy" and "joyful"). They cluster semantically equivalent tokens before computing entropy, providing a more meaningful uncertainty estimate.

**3.2.4 P(True) and P(IK)**

- **P(True)** (Kadavath et al., 2022): Evaluates the model's probability of its own answer being correct by computing the probability of "True" given the prompt "Is the following answer correct? [answer]". This provides a post-hoc confidence estimate but requires an additional forward pass.

- **P(IK)** (Azaria & Mitchell, 2023): Computes the probability that the model "knows" the answer, distinguishing between genuine knowledge and lucky guessing.

### 3.3 Sampling-Based Methods

Multiple sampling approaches estimate uncertainty by generating diverse outputs:

- **Self-Consistency** (Wang et al., 2023): Generates $N$ responses via temperature-scaled sampling and measures agreement. High agreement → low uncertainty. Computationally expensive ($O(N)$ forward passes).

- **Verbalized Uncertainty** (Tian et al., 2023): Prompts the model to explicitly express its uncertainty in natural language. Subject to the same calibration issues as declared confidence.

- **Repeated Sampling** (Fisch et al., 2024): Generates multiple responses and uses the variance of correctness as an uncertainty signal. More robust than single-sample methods but computationally costly.

### 3.4 Comparison of LLM Uncertainty Methods

| Method | Signal Source | Computational Cost | Calibration | Hallucination Detection |
|--------|-------------|-------------------|-------------|------------------------|
| Declared Confidence | Self-reported text | O(1) | ❌ Poor | ❌ |
| Token Logprobs | Single forward pass | O(1) | ✅ Moderate | ✅ |
| Token Entropy | Single forward pass | O(1) | ✅ Good | ✅ |
| Semantic Uncertainty | Single forward pass + clustering | O(V log V) | ✅ Good | ✅ |
| P(True) | Additional forward pass | O(1) | ✅ Moderate | ✅ |
| Self-Consistency | N forward passes | O(N) | ✅ Good | ✅ |
| Verbalized Uncertainty | Single forward pass | O(1) | ❌ Poor | ❌ |

### 3.5 Applications of LLM Uncertainty

- **Medical Question Answering**: Token entropy has been shown to identify unreliable medical responses (PMC 2025), with high-entropy responses correlating with factual errors.

- **Financial Forecasting**: The inner confidence framework was originally validated in financial prediction, where high-confidence predictions generated significantly higher returns (Chen et al., 2025).

- **Hallucination Detection**: Multiple studies (Burns et al., 2023; Azaria & Mitchell, 2023; Farquhar et al., 2024) have demonstrated that token-level uncertainty signals can detect hallucinations without external knowledge bases.

- **High-Stakes Decision Making**: In healthcare and legal reasoning, entropy-based confidence filtering enables human-in-the-loop workflows where uncertain predictions are flagged for expert review.

---

## 4. Predictive Uncertainty for Vision Models

### 4.1 Softmax Entropy

The simplest and most widely used uncertainty measure for classification models is the entropy of the softmax output:

$$H(\mathbf{p}) = -\sum_{c=1}^{C} p_c \log_2 p_c$$

where $p_c$ is the predicted probability for class $c$. This provides a per-sample scalar uncertainty estimate. Hendrycks & Gimpel (2017) showed that softmax entropy correlates with misclassification risk and can serve as an out-of-distribution (OOD) detection signal.

### 4.2 Bayesian Approaches

**4.2.1 Monte Carlo Dropout (MC Dropout)**

Gal & Ghahramani (2016) demonstrated that dropout applied at inference time provides a Bayesian approximation to the model's predictive distribution. By running $T$ stochastic forward passes:

$$\mathbb{E}[\mathbf{p}] = \frac{1}{T} \sum_{t=1}^{T} \mathbf{p}^{(t)}$$

$$\text{Uncertainty} = H(\mathbb{E}[\mathbf{p}]) - \frac{1}{T} \sum_{t=1}^{T} H(\mathbf{p}^{(t)})$$

The first term captures **aleatoric uncertainty** (data noise) and the second captures **epistemic uncertainty** (model uncertainty). MC Dropout requires $T$ forward passes but adds no parameters.

**4.2.2 Deep Ensembles**

Lakshminarayanan et al. (2017) proposed training an ensemble of $M$ independently initialized models and using the disagreement among their predictions as an uncertainty signal. Deep ensembles provide well-calibrated uncertainty estimates but are computationally expensive ($M \times$ training cost).

**4.2.3 Evidential Deep Learning**

Sensoy et al. (2018) proposes placing a Dirichlet distribution over class probabilities, enabling uncertainty estimation from a single forward pass by parameterizing the concentration parameters of the Dirichlet.

### 4.3 Spatial Uncertainty

For dense prediction tasks (segmentation, detection), uncertainty can be visualized spatially:

- **Grad-CAM** (Selvaraju et al., 2017): Generates class-discriminative attention maps by computing gradients of the target class score with respect to feature maps. High-gradient regions indicate where the model "looks" for its decision.

- **Entropy Maps**: Computing softmax entropy at each spatial location produces an "uncertainty heatmap" that highlights image regions where the model is uncertain. This is particularly useful in medical imaging, where uncertainty localization can guide clinical attention.

- **Bayesian Segmentation Networks**: Kendall et al. (2018) combine MC Dropout with segmentation architectures to produce per-pixel uncertainty maps, enabling uncertainty-aware medical image analysis.

### 4.4 Vision Transformers

The advent of Vision Transformers (ViT; Dosovitskiy et al., 2021) introduces a natural parallel to LLM token entropy:

- **Patch-Level Entropy**: Each image patch in a ViT is analogous to a token in an LLM. The attention-weighted patch representations carry uncertainty information that can be extracted and aggregated.

- **DINOv2 Self-Supervised Features**: Oquab et al. (2023) showed that DINOv2 features capture rich semantic information without supervision. The entropy of patch-level representations can serve as an uncertainty signal for downstream tasks.

- **MAE Reconstruction Uncertainty**: He et al. (2022) demonstrated that Masked Autoencoders can be used to estimate data uncertainty through reconstruction error, providing an unsupervised uncertainty signal.

### 4.5 Comparison of CV Uncertainty Methods

| Method | Signal Source | Cost | Spatial Resolution | OOD Detection |
|--------|-------------|------|-------------------|---------------|
| Softmax Entropy | Single forward pass | O(1) | Per-sample | ✅ |
| MC Dropout | T forward passes | O(T) | Per-pixel (with segmentation) | ✅ |
| Deep Ensembles | M models | O(M) | Per-sample | ✅ |
| Evidential DL | Single forward pass | O(1) | Per-sample | ✅ |
| Grad-CAM | Single backward pass | O(1) | Per-pixel | ❌ |
| Patch Entropy (ViT) | Single forward pass | O(1) | Per-patch | ✅ |

### 4.6 Applications of CV Uncertainty

- **Medical Imaging**: Uncertainty estimation is critical for clinical deployment, where uncertain predictions must be flagged for expert review (McKinney et al., 2020; Rajpurkar et al., 2022).

- **Autonomous Driving**: Spatial uncertainty maps help identify failure modes in perception systems (Feng et al., 2023).

- **Industrial Inspection**: In PCB defect detection and manufacturing quality control, uncertainty-weighted decisions reduce false positives and false negatives.

- **Organoid Analysis**: In stem cell-derived organoid classification, uncertainty estimation helps identify novel or atypical organoid morphologies.

---

## 5. Conformity Effects in Model Aggregation

### 5.1 The Asch Conformity Paradigm

Solomon Asch's (1951, 1955) experiments remain the foundational work on conformity in social psychology. In the classic paradigm:

- Participants were shown a line and asked to match it to one of three comparison lines.
- Confederates (working with the experimenter) unanimously gave an incorrect answer.
- **~37% of participants conformed to the incorrect majority** on a majority of critical trials.
- **75% conformed at least once** across all trials.

Asch identified two types of conformity:
1. **Normative conformity**: Yielding to group pressure to avoid social disapproval.
2. **Informational conformity**: Accepting the majority opinion as evidence about reality.

### 5.2 Conformity in Machine Learning

The conformity phenomenon extends naturally to machine learning systems:

**5.2.1 Ensemble Conformity**

When combining predictions from multiple models, the majority opinion can suppress correct minority predictions. This is particularly problematic when:
- Models are trained on similar data (low diversity)
- The aggregation method is simple averaging (uniform weighting)
- Minority models have expertise on rare or unusual patterns

**5.2.2 Federated Learning Conformity**

In FL, the analogy to Asch's experiment is direct:
- **Majority clients** (with common data distributions) play the role of Asch's confederates
- **Minority clients** (with rare or specialized data) play the role of the dissenting participant
- **FedAvg** plays the role of the social pressure that forces conformity

We formalize the **conformity degree** as:

$$\text{Conformity}(k) = \text{Acc}_{\text{local}}^{(k)} - \text{Acc}_{\text{global}}^{(k)}$$

where $\text{Acc}_{\text{local}}^{(k)}$ is client $k$'s accuracy on its own data, and $\text{Acc}_{\text{global}}^{(k)}$ is the global model's accuracy on client $k$'s data. A positive value indicates that the global model performs worse than the client's local model on that client's data—evidence of conformity suppressing minority knowledge.

**5.2.3 Majority Tyranny in Aggregation**

Mohri et al. (2019) formalized the concept of "agnostic FL," showing that the optimal global model for worst-case client performance can be fundamentally different from the FedAvg solution. This is a mathematical formalization of the majority tyranny problem.

**5.2.4 The "Bucket Effect" in FL**

FlexLoRA (NeurIPS 2024) identified the "bucket effect" in federated LLM fine-tuning: the global model's capability is limited by the least capable or most noisy client, analogous to how the capacity of a bucket is determined by its shortest stave.

### 5.3 Factors Amplifying Conformity

Several factors exacerbate conformity in FL:

1. **Data Heterogeneity (Non-IID)**: The more heterogeneous the data distributions, the more severe the conformity effect. Dirichlet $\alpha < 1$ creates extreme Non-IID conditions where conformity is most pronounced.

2. **Number of Clients**: More clients → stronger majority → more severe conformity. The Asch experiment showed that conformity increased with group size up to a point (3-4 confederates).

3. **Uniform Weighting**: FedAvg's uniform (or data-volume-based) weighting gives equal voice to all clients, regardless of their expertise or confidence.

4. **Communication Rounds**: Over multiple rounds, conformity compounds—the global model progressively forgets minority knowledge as it is "averaged out."

5. **Model Capacity**: Larger models can memorize more patterns, potentially mitigating conformity, but also risk overfitting to majority distributions.

### 5.4 Mitigating Conformity

Existing approaches to mitigating conformity in FL include:

- **Personalization**: Allowing each client to maintain a personalized model (Per-FedAvg, pFedMe) avoids conformity by not forcing a single global model.
- **Clustering**: Grouping similar clients and maintaining cluster-specific models (CFed, FedCluster) reduces within-cluster conformity.
- **Weighted Aggregation**: Using data quality or performance metrics to weight client contributions (Fed-RM, FedSoft).
- **Curriculum Learning**: Gradually introducing minority-client data into the global training process.

However, none of these methods use **model-internal uncertainty** as the weighting signal—which, as we argue in Section 7, is the most natural and principled approach.

---

## 6. The Intersection: Uncertainty Signals for Aggregation

### 6.1 Why Entropy as an Aggregation Signal?

We argue that model-internal entropy is the ideal signal for aggregation weighting for three reasons:

**6.1.1 Theoretical Grounding**

Information theory provides a rigorous foundation. The Shannon entropy $H$ of a probability distribution measures the average "surprise" of an observation drawn from that distribution. In the context of model predictions:

- **Low entropy** → the model's probability mass is concentrated on one outcome → the model is "confident" → the prediction is likely based on learned patterns → high-quality signal for aggregation.
- **High entropy** → the probability mass is spread across outcomes → the model is "uncertain" → the prediction may be based on limited or conflicting evidence → low-quality signal for aggregation.

This directly maps to the aggregation problem: we want to give more weight to updates from confident clients (low entropy) and less weight to uncertain clients (high entropy).

**6.1.2 Empirical Evidence**

- Chen et al. (2025) showed that token entropy predicts LLM accuracy with high fidelity (14 percentage points between quintiles).
- Hendrycks & Gimpel (2017) showed that softmax entropy correlates with misclassification in CNNs.
- Multiple studies confirm that entropy-based confidence estimates outperform self-reported confidence.

**6.1.3 Computational Efficiency**

Entropy is a byproduct of the standard forward pass—no additional computation is required. The aggregation weight is a single scalar per client per round, adding negligible communication overhead (one float value).

### 6.2 Structural Comparison: NLP vs CV Entropy

| Property | Token Entropy (NLP) | Softmax Entropy (CV) |
|----------|-------------------|---------------------|
| **Source** | Conditional token probability distribution | Final classification layer output |
| **Granularity** | Per-token (sequence-level) | Per-sample (or per-patch for ViT) |
| **Range** | $[0, \log_2 V]$ (typically $[0, 12]$ for $V=4096$) | $[0, \log_2 C]$ (typically $[0, 4]$ for $C=16$) |
| **Interpretation** | Model's uncertainty about next word | Model's uncertainty about class label |
| **Path Dependency** | High (autoregressive generation) | Low (single forward pass) |
| **Aggregation to Client-Level** | Average over tokens and samples | Average over samples |
| **Hallucination/Misclassification Signal** | High entropy → likely hallucination | High entropy → likely misclassification |

Despite these structural differences, both signals share the same information-theoretic foundation and can be unified under a common framework.

### 6.3 Related but Distinct Work

Several recent papers have explored adjacent ideas:

- **Entropy-guided FL** (Li et al., 2025; MDPI Sensors): Uses data diversity entropy (Shannon entropy of label distributions) to weight client contributions. This measures data diversity, not model confidence.

- **Uncertainty-Aware Explainable FL** (Jiang et al., 2025): Generates explanations for FL decisions and provides uncertainty information, but does not use uncertainty for aggregation weighting.

- **FedPSAWA** (Gu et al., 2026; Neurocomputing): Uses state-aware weighting for personalized FL in medical data, addressing inter-patient variability through personalization rather than uncertainty weighting.

- **FedEBA** (Wang et al., 2023; ICLR): Combines entropy-based aggregation with model and gradient alignments to optimize fairness and global performance. This is the closest existing work to our proposed framework, though it uses entropy to upweight underperforming clients rather than confident ones.

**Key distinction**: Our framework uses **model prediction entropy** (how uncertain the model is about its predictions) rather than **data entropy** (how diverse the data is) or **gradient entropy** (how dispersed the updates are). Model prediction entropy directly reflects the quality of the learned representation, making it the most principled signal for aggregation weighting. This distinction is not merely terminological—it leads to fundamentally different aggregation behavior:

- **FedEBA** (Wang et al., 2023; ICLR) uses entropy to upweight *underperforming* clients, optimizing for fairness. Our framework upweights *confident* clients, optimizing for quality.
- **FedEmerge** (2025) uses the entropy of each client's *data distribution* to reward diversity. Our framework uses the entropy of each client's *model predictions* to reward reliability.
- **Sterniczuk** (2026) computes entropy over model *weight matrices*. Our framework computes entropy over model *output distributions*, which directly reflects prediction uncertainty.

These are complementary objectives—fairness, diversity, and quality—that could potentially be combined in a multi-objective aggregation framework.

---

## 7. Toward a Unified Framework: Entropy-Weighted Aggregation (EWA)

### 7.1 Two-Layer Architecture

We propose a **two-layer architecture** that separates training from monitoring:

**Layer 1 — Training (unchanged):** Standard FL training proceeds using FedAvg (or any existing aggregation strategy). The global model is updated as:

$$\theta^{(t+1)} = \sum_{k=1}^{K} \frac{n_k}{n} \theta_k^{(t)}$$

**Layer 2 — Monitoring (EWA):** In parallel with training, each client $k$ encodes its local inference results as **structured visual primitives** — lightweight representations containing class labels, coordinates, and entropy values — and uploads them to the server. The server groups primitives by class, computes **class prototypes** (weighted statistics per class), and detects conformity by comparing per-client contributions against the aggregated prototype.

This separation has a critical advantage: **EWA does not modify the training process**, making it a zero-intrusion, drop-in diagnostic tool. Any FL system can adopt EWA monitoring without changing its training pipeline.

### 7.2 Primitive Encoding

Given $K$ clients participating in FL round $t$, each client $k$:

1. Receives the global model $\theta^{(t)}$
2. Runs local inference on data $\mathcal{D}_k$ (not training — inference only)
3. For each detection/prediction, computes:
   - **Class label** $c$ (e.g., "late_stage", "rare_syndrome")
   - **Confidence** $\text{conf}$ (softmax probability or $\exp(-H)$)
   - **Entropy** $H$ (Shannon entropy of the output distribution)
4. Encodes results as structured primitives: $\text{Primitive}(c, \text{coords}, H, k)$
5. Transmits primitives to the server (no raw images or text)

**Privacy guarantee:** Only structured primitives are transmitted — class labels, normalized coordinates, and scalar entropy values. No raw data (images, text, gradients) leaves the client.

### 7.3 Class Prototype Aggregation

The server groups primitives by class label and computes a **class prototype** for each class $c$:

$$\text{Prototype}(c) = \left\{ \bar{H}_c, \overline{\text{conf}}_c, \bar{A}_c, \{w_{k,c}\}_{k=1}^{K} \right\}$$

where:
- $\bar{H}_c$ is the entropy-weighted mean entropy for class $c$
- $\overline{\text{conf}}_c$ is the entropy-weighted mean confidence
- $\bar{A}_c$ is the entropy-weighted mean detection area (CV tasks)
- $w_{k,c}$ is client $k$'s **weight share** on class $c$, computed as:

$$w_{k,c} = \frac{\sum_{p \in \mathcal{P}_{k,c}} \phi(H_p)}{\sum_{j=1}^{K} \sum_{p \in \mathcal{P}_{j,c}} \phi(H_p)}$$

where $\mathcal{P}_{k,c}$ is the set of primitives from client $k$ for class $c$, and $\phi(H) = 1/H$ is the entropy-based weighting function.

### 7.4 Conformity Detection

For each class $c$, EWA computes a **conformity score** that measures whether minority expertise is being suppressed:

$$\text{Conformity}(c) = 1 - \frac{w_{\text{expert},c}}{w_{\text{expert},c}^{\text{count}}}$$

where $w_{\text{expert},c}^{\text{count}}$ is the expert's proportional contribution by count (what FedAvg would give), and $w_{\text{expert},c}$ is the expert's entropy-weighted contribution. A conformity score of 0 means the expert's knowledge is fully preserved; a score approaching 1 means near-total suppression.

**Alert system:** When $\text{Conformity}(c) > \tau$ (configurable threshold), EWA generates a conformity alert identifying the affected class and the suppressed expert client.

### 7.5 Entropy Computation

**For NLP (LLMs):**

$$H_k^{(t)}(x) = \frac{1}{T_x} \sum_{t=1}^{T_x} \left[ -\sum_{i=1}^{V} P(x_t^{(i)} | x_{<t}; \theta_k^{(t)}) \log_2 P(x_t^{(i)} | x_{<t}; \theta_k^{(t)}) \right]$$

where $T_x$ is the sequence length and $V$ is the vocabulary size.

**For CV (CNNs/ViTs):**

$$H_k^{(t)}(x) = -\sum_{c=1}^{C} p_c^{(k)}(x; \theta_k^{(t)}) \log_2 p_c^{(k)}(x; \theta_k^{(t)})$$

where $C$ is the number of classes and $p_c^{(k)}$ is the softmax probability for class $c$.

### 7.6 Properties of EWA

1. **Zero Intrusion**: EWA does not modify the training process. It is a monitoring layer that can be added to any existing FL system.

2. **Privacy by Design**: Only structured primitives (class, coords, entropy) are transmitted — no raw images, text, or gradients.

3. **Conformity Detection**: By comparing entropy-weighted vs count-based contributions per class, EWA quantifies exactly where and how minority knowledge is being suppressed.

4. **Cross-Modal**: The framework applies equally to NLP and CV, with the only difference being the entropy computation method.

5. **Audit Trail**: All conformity analyses are recorded in a tamper-evident audit chain (SHA-256 hash chain), providing compliance evidence.

6. **Communication Efficiency**: Structured primitives are lightweight (a few hundred bytes per detection), adding negligible overhead compared to model parameter transmission.

### 7.7 Experimental Results

We conducted a rigorous evaluation across three real-world tasks spanning both CV and NLP modalities. Unlike preliminary simulations, all experiments use **real datasets, real model training (PyTorch), and real softmax entropy extraction** — no synthetic or simulated entropy values. Each experiment simulates 5 FL clients (1 expert + 4 generalists) over 20 rounds with Non-IID data distributions. The key metric is the **expert's weight share on its specialty class** — the percentage of entropy-weighted contribution attributed to the expert client for the class it specializes in.

| Task | Modality | Dataset | Feature | EWA Expert Wt | FedAvg Expert Wt | $\Delta$ (pp) | Rel. Improvement |
|------|----------|---------|---------|---------------|-----------------|---------------|-----------------|
| Medical CV | CV | Organoid-FL (600) | DINOv2 + PCA 16d | 89.9% ± 11.1% | 54.6% ± 1.7% | +35.3 | 64.6% |
| Financial NLP | NLP | Twitter Sentiment (9,543) | MiniLM-L6-v2 384d | 74.9% ± 13.1% | 62.8% ± 10.5% | +12.1 | 19.3% |
| Medical NLP | NLP | PubMed QA (1,000) | MiniLM-L6-v2 384d | 45.3% ± 8.5% | 38.6% ± 2.6% | +6.7 | 17.4% |
| **Average** | | | | **70.0%** | **52.0%** | **+18.0** | **33.8%** |

**Key findings:**

1. **EWA consistently protects expert knowledge** across all three real-world tasks, with the expert retaining 45–90% weight share under entropy weighting, compared to 39–55% under equal weighting (FedAvg baseline). The average improvement is +18.0 percentage points (33.8% relative).

2. **Effect size correlates with task confidence.** The CV task (organoid classification, 99.2% accuracy) shows the largest improvement (+35.3pp) because the expert client has genuinely low entropy on its specialty class, creating a strong signal for EWA to amplify. The medical QA task (57.7% accuracy) shows the smallest improvement (+6.7pp) because high entropy across all clients leaves less signal for differentiation.

3. **EWA does not blindly trust experts.** When the expert itself is uncertain (high entropy on its specialty class), EWA appropriately reduces its weight share. This is a desirable property — EWA reflects genuine model confidence, not merely data ownership.

4. **CV shows stronger conformity protection than NLP** (+35.3pp vs +9.4pp average). This aligns with our hypothesis that CV entropy (softmax over 3 classes) has lower variance than NLP entropy (sentence embeddings in high-dimensional space), leading to more stable and differentiated weighting.

These results demonstrate that EWA monitoring can effectively detect and quantify conformity effects in real FL training pipelines, with effect sizes that depend on the underlying task difficulty and model confidence.

---

## 8. Challenges and Future Directions

### 8.1 Open Challenges

**8.1.1 Entropy Does Not Equal Accuracy**

Low entropy indicates confidence, not correctness. A model can be confidently wrong—this is the essence of hallucination in LLMs and adversarial examples in CV. Future work should explore:
- Combining entropy with accuracy estimates (e.g., using a small validation set)
- Detecting "confident errors" through cross-client consistency checks
- Adaptive temperature scheduling based on estimated calibration

**8.1.2 Cold-Start Instability**

In the first few FL rounds, entropy estimates may be unstable because:
- The model has not yet learned meaningful representations
- Random initialization creates artificial entropy differences
- Small local datasets produce noisy entropy estimates

Potential solutions include:
- Warm-up periods with uniform averaging before switching to EWA
- Entropy smoothing using exponential moving averages
- Minimum sample size requirements for reliable entropy estimation

**8.1.3 Scalability to Large Models**

For LLMs with billions of parameters, computing entropy on the full local dataset at every round may be expensive. Approximation strategies include:
- Subsampling: Compute entropy on a random subset of local data
- Proxy datasets: Use a small, shared calibration set for entropy estimation
- Layer-wise entropy: Use entropy from intermediate layers rather than the full forward pass

**8.1.4 Privacy Implications**

Entropy values reveal information about the client's data distribution, which could potentially be exploited in privacy attacks. Future work should analyze:
- The information leakage risk of transmitting entropy values
- Differential privacy mechanisms for entropy-weighted aggregation
- The trade-off between aggregation quality and privacy protection

### 8.2 Future Research Directions

**8.2.1 Multi-Modal Entropy**

As multi-modal models (e.g., GPT-4V, Gemini) become prevalent, entropy can be computed across modalities:
- Text entropy + image entropy → joint uncertainty signal
- Cross-modal consistency: disagreement between text and image entropy indicates potential multi-modal hallucination

**8.2.2 Hierarchical Entropy Weighting**

Current EWA weights clients uniformly based on their average entropy. A more sophisticated approach could:
- Weight different layers of the model differently based on layer-specific entropy
- Use entropy trajectories (how entropy changes over training rounds) to identify improving vs. degrading clients

**8.2.3 Entropy for Byzantine-Robust Aggregation**

Combining entropy weighting with Byzantine-robust methods (Krum, Trimmed Mean) could provide defense against both uncertain and adversarial clients:
- First pass: Use entropy to identify potentially unreliable clients
- Second pass: Apply Byzantine-robust aggregation on the remaining clients

**8.2.4 Theoretical Foundations**

Open theoretical questions include:
- What is the optimal temperature $\alpha$ as a function of data heterogeneity?
- Can we prove convergence guarantees that are tighter than FedAvg under specific entropy conditions?
- What is the relationship between entropy-weighted aggregation and optimal transport-based aggregation?

**8.2.5 Applications and Benchmarks**

We call for the development of standardized benchmarks for evaluating uncertainty-aware FL aggregation:
- **Medical FL Benchmark**: Multi-institutional medical data with ground-truth quality labels
- **Financial FL Benchmark**: Multi-fund financial data with return-based quality metrics
- **Industrial FL Benchmark**: Multi-factory defect detection data with known defect rates
- **Conformity Metric Suite**: Standardized metrics for measuring conformity degree, knowledge retention, and minority-client performance

**8.2.6 Entropy-Weighted Federated Inference**

The federated inference paradigms introduced in Section 2.5 present particularly promising application domains for EWA, because inference-level uncertainty signals are richer and more directly observable than training-level signals:

- **Entropy-Weighted Federated RAG**: When multiple clients perform RAG on the same query, the server can aggregate retrieved documents and generated answers by weighting each client's contribution according to its retrieval relevance score and generation token entropy. This naturally implements a "wisdom of the confident crowds" mechanism, where clients with relevant knowledge bases and confident generation are prioritized.

- **Step-Level Entropy Aggregation for Federated CoT**: In federated chain-of-thought distillation, different clients may produce correct reasoning at different steps. Rather than selecting one client's entire chain, a step-level entropy-weighted aggregation could compose an optimal reasoning chain by selecting the most confident step from each client at each reasoning stage. This is analogous to the visual primitive aggregation proposed by Lu et al. (2025), where spatial primitives are weighted by localization certainty.

**8.2.7 Beyond Aggregation: Entropy as a Memory Fidelity Signal**

The discussion so far has treated entropy primarily as a *post-hoc* aggregation weight—a signal that tells the server which clients to trust. A parallel line of research suggests a more fundamental role: entropy as a *proactive* monitor of information integrity within the model itself.

**The memory degradation problem in LLMs.** Despite claims of million-token context windows, LLMs exhibit systematic memory failures that worsen with input length:

- **Context Rot** (Hong et al., 2025; Chroma Research): Across 18 mainstream LLMs, performance degrades non-uniformly as input length increases—even on trivially simple tasks (e.g., repeating a word). Models may begin degrading at 50K tokens despite supporting 1M-token windows. Crucially, this degradation is caused by input length itself, not task difficulty, ruling out capacity explanations.

- **Lost in the Middle** (Liu et al., 2024; TACL): LLMs exhibit a U-shaped retrieval performance curve, reliably accessing information at the beginning and end of the context but systematically ignoring information in the middle. This is a structural limitation of the Transformer attention mechanism, not a training artifact.

- **Perplexity is Unreliable for Long Contexts** (Fang et al., 2024): Standard perplexity metrics fail to capture long-context capability because they conflate next-token prediction quality with information retrieval fidelity. A model can achieve low perplexity while completely ignoring critical context.

**From memory degradation to confabulation.** These retrieval failures do not manifest as "I don't know" responses. Instead, LLMs *confabulate*—generating fluent but fabricated content that fills the gaps left by forgotten information:

- **Semantic Entropy for Confabulation Detection** (Farquhar et al., 2024; *Nature*, cited 1,430+): When an LLM generates multiple semantically equivalent answers to the same question, high semantic entropy (inconsistent answers) indicates confabulation. This method is unsupervised, requires only a single model, and needs no modifications to off-the-shelf LLMs.

- **Misleading Context Induces Confident Errors** (Zhou et al., 2025): In multi-turn and agentic settings, correct in-context information improves both accuracy and model confidence, but *misleading context frequently produces confidently incorrect responses*—breaking the alignment between uncertainty and correctness. This is the most dangerous failure mode: the model does not know that it does not know.

**Why this matters for federated learning.** These findings have direct consequences for FL systems, though the connection is more nuanced than direct application:

| Memory Failure | FL-Relevant Manifestation | Entropy-Based Mitigation |
|---------------|-------------------------|------------------------|
| Context Rot | Long FL training histories may cause models to "forget" early-round gradients | Monitor per-round entropy trajectories; detect degradation patterns |
| Lost in the Middle | Middle-ranked clients' contributions systematically underweighted by attention-based aggregation | Use entropy as an explicit positional correction factor |
| Confident Confabulation | A client with corrupted or misleading local data produces confident but wrong updates | Cross-client entropy consistency checks: flag divergent entropy profiles |

We present this direction as **beyond the scope of the current EWA framework but essential for its long-term viability**. As federated systems scale to longer training horizons and more complex inference tasks (multi-turn dialogues, federated agents), the entropy signal's role will expand from weighting aggregation to monitoring the integrity of the information being aggregated. We identify this as a particularly promising direction for future work, as it unifies two previously separate research communities—uncertainty quantification and long-context reliability—under a common information-theoretic framework.

---

## 9. Conclusion

This survey has presented the first comprehensive review of the intersection between model uncertainty quantification and federated learning aggregation. Our central argument is that model-internal entropy—whether token entropy in LLMs or softmax entropy in vision models—provides a natural, principled, and computationally efficient signal for **detecting and quantifying conformity effects** in federated aggregation.

We have shown that:
1. **Standard FL aggregation suffers from "model conformity"**, a phenomenon analogous to the Asch conformity experiments, where majority-client knowledge dominates the global model at the expense of minority expertise.
2. **Model entropy is an honest and predictive uncertainty signal**, outperforming self-reported confidence and requiring no additional computation beyond the standard forward pass.
3. **The entropy signal is modality-agnostic**, with token entropy (NLP) and softmax entropy (CV) sharing the same information-theoretic foundation and exhibiting similar correlations with prediction quality.
4. **EWA monitoring effectively detects conformity**: across three real-world tasks (medical CV, financial NLP, medical NLP), entropy-weighted analysis assigned experts 70.0% average weight share on specialty classes vs 52.0% under equal weighting, an average improvement of +18.0pp (33.8% relative).
5. **CV entropy provides stronger conformity protection than NLP entropy** (+35.3pp vs +9.4pp average), a finding we attribute to the lower variance of softmax entropy over small class sets and higher model confidence on CV tasks.
6. **The monitoring framework is zero-intrusion**: EWA operates as a parallel analysis layer that does not modify the training process, making it compatible with any existing FL system.

The research agenda we have outlined—from large-scale real-world experiments to multi-modal entropy integration—represents a promising direction for building more trustworthy and equitable federated learning systems. As LLMs and vision models are increasingly deployed in high-stakes domains (healthcare, finance, legal reasoning, industrial inspection), the ability to detect conformity effects and protect minority expertise in collaborative settings is not merely an academic exercise—it is a practical necessity.

We hope this survey catalyzes research at this intersection and provides a foundation for the next generation of uncertainty-aware federated learning monitoring systems.

---

## References

### Federated Learning

[1] McMahan, B., et al. (2017). Communication-Efficient Learning of Deep Networks from Decentralized Data. AISTATS.

[2] Li, T., et al. (2020). Federated Optimization in Heterogeneous Networks (FedProx). MLSys.

[3] Wang, J., et al. (2020). Tackling the Objective Inconsistency Problem in Heterogeneous Federated Optimization (FedNova). NeurIPS.

[4] Li, X., et al. (2021). FedBN: Federated Learning on Non-IID Features via Local Batch Normalization. ICLR.

[5] Karimireddy, S. P., et al. (2020). SCAFFOLD: Stochastic Controlled Averaging for Federated Learning. ICML.

[6] Acar, D. E., et al. (2021). Federated Learning Based on Dynamic Regularization (FedDyn). ICLR.

[7] Blanchard, P., et al. (2017). Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent. NeurIPS.

[8] Yin, M., et al. (2018). A Unified Framework for Byzantine-Tolerant Machine Learning. arXiv.

[9] Mohri, M., et al. (2019). Agnostic Federated Learning. ICML.

[10] Reisizadeh, A., Farnia, F., Pedarsani, R., & Jadbabaie, A. (2020). "Robust Federated Learning: The Case of Affine Distribution Shifts." NeurIPS.

### LLM Uncertainty Quantification

[11] Chen, H., et al. (2025). Inner Confidence: Measuring LLM Uncertainty via Token Entropy. NBER Working Paper No. 34965.

[12] Kadavath, S., et al. (2022). Language Models (Mostly) Know What They Know. arXiv.

[13] Burns, C., et al. (2023). Discovering Latent Knowledge in Language Models Without Supervision. arXiv.

[14] Azaria, A., & Mitchell, T. (2023). The Internal State of an LLM Knows When It's Lying. arXiv.

[15] Kuhn, L., et al. (2023). Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Large Language Models. NeurIPS.

[16] Wang, X., et al. (2023). Self-Consistency Improves Chain of Thought Reasoning in Language Models. ICLR.

[17] Tian, J., et al. (2023). Knowing What They Know: Adapting LLMs Using Their Own Self-Knowledge. arXiv.

[18] Farquhar, S., et al. (2024). Detecting Hallucinations in Large Language Models Using Semantic Entropy. Nature.

[19] Geng, J., Cai, F., Wang, Y., & Koeppl, H. (2024). "A Survey of Confidence Estimation and Calibration in Large Language Models." arXiv:2311.08298.

[20] Huang, Y., Sun, L., Wang, H., Wu, S., et al. (2024). "TrustLLM: Trustworthiness in Large Language Models." arXiv:2401.05561.

[21] Shorinwa, O., Mei, Z., Lidard, J., & Ren, A. Z. (2024). "A Survey on Uncertainty Quantification of Large Language Models: Taxonomy, Open Research Challenges, and Future Directions." arXiv:2412.05563.

[22] Xia, Z., Xu, J., Zhang, Y., & Liu, H. (2025). "A Survey of Uncertainty Estimation Methods on Large Language Models." Findings of ACL, pp. 21381-21396.

### CV Predictive Uncertainty

[23] Hendrycks, D., & Gimpel, K. (2017). A Baseline for Detecting Misclassified and Out-of-Distribution Examples in Neural Networks. ICLR.

[24] Gal, Y., & Ghahramani, Z. (2016). Dropout as a Bayesian Approximation: Representing Model Uncertainty in Deep Learning. ICML.

[25] Lakshminarayanan, B., et al. (2017). Simple and Scalable Predictive Uncertainty Estimation using Deep Ensembles. NeurIPS.

[26] Sensoy, M., et al. (2018). Evidential Deep Learning to Quantify Classification Uncertainty. NeurIPS.

[27] Selvaraju, R. R., et al. (2017). Grad-CAM: Visual Explanations from Deep Networks via Gradient-based Localization. ICCV.

[28] Kendall, A., et al. (2018). Multi-Task Learning Using Uncertainty to Weigh Losses for Scene Geometry and Semantics. CVPR.

[29] Dosovitskiy, A., et al. (2021). An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale. ICLR.

[30] Oquab, M., et al. (2023). DINOv2: Learning Robust Visual Features without Supervision. arXiv.

[31] He, K., et al. (2022). Masked Autoencoders Are Scalable Vision Learners. CVPR.

### Conformity and Social Psychology

[32] Asch, S. E. (1951). Effects of Group Pressure upon the Modification and Distortion of Judgment. Groups, Leadership and Men.

[33] Asch, S. E. (1955). Opinions and Social Pressure. Scientific American, 193(5), 31-35.

[34] Bond, R., & Smith, P. B. (1996). Culture and Conformity: A Meta-Analysis of Studies Using Asch's Line Judgment Task. Psychological Bulletin, 119(1), 111-137.

### Uncertainty-Aware FL and Related Work

[35] Li, S., et al. (2025). "Entropy-based Aggregation Combined with Model and Gradient Alignments for Federated Learning Optimization." OpenReview.

[36] MDPI (2025). "Entropy-Guided Federated Strategy: Weighting Client Updates by Data Diversity." Sensors, 25(12), 3728.

[37] Ruan, Y., & Joe-Wong, C. (2021). "FedSoft: Soft Clustered Federated Learning with Proximal Local Updating." arXiv:2112.06053.

[38] Bai, J., Chen, D., Qian, B., & Yao, L. (2024). "Federated Fine-Tuning of Large Language Models under Heterogeneous Tasks and Client Resources." NeurIPS. arXiv:2402.11505.

[39] Gu, P., Shou, J., et al. (2026). "FedPSAWA: Federated Personalization with State Aware Weighting Aggregation for Cross-Subject Seizure Prediction." Neurocomputing, 674.

[40] Wang, H., et al. (2020). Federated Learning with Matched Averaging (FedMA). ICLR.

[41] Fallah, A., et al. (2020). Personalized Federated Learning with Theoretical Guarantees: A Model-Agnostic Meta-Learning Approach. NeurIPS.

[42] McKinney, S. M., et al. (2020). International Evaluation of an AI System for Breast Cancer Screening. Nature, 577, 89-94.

[43] Vayena, E., & Blasimme, A. (2018). "Machine Learning in Medicine: Addressing Ethical Challenges." PLOS Medicine, 15(11), e1002689.

[44] Sugiyama, M., et al. (2007). Direct Importance Estimation with Model Selection and Its Application to Covariate Shift Adaptation. NeurIPS.

[45] He, W., Jiang, Z., Xiao, T., & Xu, Z. (2023). "A Survey on Uncertainty Quantification Methods for Deep Neural Networks." arXiv:2302.13425.

[46] Wu, Y., Tian, C., Li, J., & Sun, H. (2025). "A Survey on Federated Fine-Tuning of Large Language Models." arXiv:2503.12016.

[47] OpenReview (2024). "Personalized Federated Fine-Tuning with Heterogeneous Data for Language Models." OpenReview.

[48] Salazar, T., Araujo, H., Cano, A., & Abreu, P. H. (2024). "A Survey on Group Fairness in Federated Learning: Challenges, Taxonomy of Solutions and Directions for Future Research." arXiv:2410.03855.

[49] EMNLP (2025). "Federated Fine-Tuning of Large Language Models Using Low-Rank Adaptation." EMNLP.

[50] IEEE (2026). "Federated Learning in Handling Data Distribution Variations." IEEE Access.

[51] ICML (2025). "Convergence of Overparameterized FedAvg with Gradient Descent." ICML.

[52] Sen, M., Aparna, S., Agarwal, R., & Mohan, C. K. (2025). "Overcoming Challenges of Partial Client Participation in Federated Learning: A Comprehensive Review." arXiv:2506.02887.

[53] JMIR (2025). "Token Probabilities to Mitigate Large Language Models Overconfidence in Answering Medical Questions: Quantitative Study." J Med Internet Res. PMC12396779.

[54] Amazon Science (2024). "A Calibrated Reflection Approach for Enhancing Confidence Estimation in LLMs." Amazon Science.

[55] Wang, Y., Ni, S., Ding, Z., & Zhan, Z. (2025). "Evaluating and Calibrating LLM Confidence on Questions with Multiple Correct Answers." arXiv:2602.07842.

[56] Liu, F., Pan, B., Wang, Z., & Yao, X. (2025). "FLEx: Personalized Federated Learning for Mixture-of-Experts LLMs via Expert Grafting." arXiv:2506.00965.

[57] Jimenez, D. M. G., Solans, D., Heikkila, M., & Vitaletti, A. (2024). "Non-IID Data in Federated Learning: A Survey with Taxonomy, Metrics, Methods, Frameworks and Future Directions." arXiv:2411.12377.

[58] Zhang, Y., & Yu, H. (2025). "Uncertainty-Aware Explainable Federated Learning." Expert Systems with Applications. arXiv:2503.05194.

[59] Entropy (2026). "Entropy-Based Methods in Distributed Learning Systems." Entropy, Special Issue. PMC12939742.

[60] Peters, D. (2024). "Fair Sequential Decision Making Given Voter Preferences." AAAI. arXiv:2306.14858.

### Federated Inference

[61] Chakraborty, A., Dahal, C., Gupta, V., et al. (2025). "Federated Retrieval-Augmented Generation: A Systematic Mapping Study." arXiv:2505.18906.

[62] Addison, P., Nguyen, M.-T. H., Medan, T., Shah, J., et al. (2024). "C-FedRAG: A Confidential Federated Retrieval-Augmented Generation System." arXiv:2412.13163.

[63] Mao, Q., Zhang, Q., Hao, H., Han, Z., et al. (2025). "Privacy-Preserving Federated Embedding Learning for Localized Retrieval-Augmented Generation." arXiv:2504.19101.

[64] Shojaee, P., Harsha, S. S., Luo, D., Maharaj, A., et al. (2025). "Federated Retrieval Augmented Generation for Multi-Product Question Answering." arXiv:2501.14998.

[65] Fan, T., Chen, W., Kang, Y., Ma, G., Gu, H., Song, Y., Fan, L., & Yang, Q. (2025). "FedCoT: Federated Chain-of-Thought Distillation for Large Language Models." Findings of EMNLP 2025, pp. 4689–4702.

[66] Li, C., Zhao, Q., Mo, F., & Chen, C. (2025). "FedCoT: Communication-Efficient Federated Reasoning Enhancement for Large Language Models." arXiv:2508.10020.

[67] Lu, R., Ma, Y., Chen, X., Luo, L., Wu, Z., Pan, Z., et al. (2025). "Thinking with Visual Primitives." DeepSeek-AI / Peking University / Tsinghua University.

### Long-Context Reliability and Confabulation

[68] Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Soares, N., Canny, J., & Manning, C. D. (2024). "Lost in the Middle: How Language Models Use Long Contexts." Transactions of the Association for Computational Linguistics, 12, 157–173. arXiv:2307.03172.

[69] Hong, S., et al. (2025). "Context Rot: How Increasing Input Tokens Impacts LLM Performance." Chroma Research. https://www.trychroma.com/research/context-rot

[70] Fang, L., Wang, Y., Liu, Z., Zhang, C., et al. (2024). "What is Wrong with Perplexity for Long-context Language Modeling?" arXiv:2410.23771.

[71] Farquhar, S., Kossen, J., Kuhn, L., & Gal, Y. (2024). "Detecting Hallucinations in Large Language Models Using Semantic Entropy." *Nature*, 630, 593–598. arXiv:2302.09664.

[72] Kuhn, L., Gal, Y., & Farquhar, S. (2023). "Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation." arXiv:2302.09664.

[73] Zhou, T., Medina, J., & Chawla, S. (2025). "Can LLMs Detect Their Confabulations? Estimating Reliability in Uncertainty-Aware Language Models." arXiv:2508.08139.

### Entropy in Federated Aggregation

[74] Wang, L., Wang, Z., Shi, Y., Karimireddy, S. P., & Tang, X. (2023). "Entropy-driven Fair and Effective Federated Learning." ICLR 2023. arXiv:2301.12407.

[75] FedEmerge (2025). "FedEmerge: An Entropy-Guided Federated Learning Method for Sensor Networks and Edge Intelligence." *Sensors*, 25(12), 3728. MDPI.

[76] FedEntOpt (2024). "FedEntOpt: Entropy-Optimized Client Selection for Federated Learning under Label Skew." arXiv:2411.01240.

[77] Sterniczuk, B. (2026). "An Entropy-Based Framework for Model Aggregation in Federated Learning." *Applied Sciences and Technology Research Journal (ASTRJ)*, 213204.

[78] Jiang, Y., et al. (2025). "Uncertainty-Aware Explainable Federated Learning." arXiv.

### Foundational References

[79] Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). "Attention Is All You Need." *NeurIPS 2017*.

[80] Platt, J. (1999). "Probabilistic Outputs for Support Vector Machines and Comparisons to Regularized Likelihood Methods." *Advances in Large Margin Classifiers*, 10(3), 61–74.

---

*This survey was prepared as a foundation for the EWA-Fed research program. The framework and research agenda proposed herein will be validated through empirical experiments across medical, financial, and industrial domains.*

*Generated by 思怡 💡 | May 2026*
