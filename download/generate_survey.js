const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, TableOfContents,
  HeadingLevel, BorderStyle, WidthType, ShadingType, VerticalAlign,
  PageNumber, PageBreak, ExternalHyperlink
} = require("docx");

const C = {
  primary: "020617", body: "1E293B", secondary: "64748B",
  accent: "94A3B8", tableBg: "F8FAFC", tableHead: "E2E8F0",
  white: "FFFFFF", link: "2563EB",
};

const bdr = { style: BorderStyle.SINGLE, size: 1, color: C.accent };
const cellB = { top: bdr, bottom: bdr, left: bdr, right: bdr };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 600, after: 300 },
    children: [new TextRun({ text, font: "Times New Roman", size: 36, bold: true, color: C.primary })]
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 400, after: 200 },
    children: [new TextRun({ text, font: "Times New Roman", size: 28, bold: true, color: C.primary })]
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 300, after: 150 },
    children: [new TextRun({ text, font: "Times New Roman", size: 24, bold: true, color: C.body })]
  });
}

function para(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 160, line: 276 },
    alignment: AlignmentType.JUSTIFIED,
    ...opts,
    children: [new TextRun({ text, font: "Times New Roman", size: 22, color: C.body })]
  });
}

function paraRuns(runs, opts = {}) {
  return new Paragraph({
    spacing: { after: 160, line: 276 },
    alignment: AlignmentType.JUSTIFIED,
    ...opts,
    children: runs
  });
}

function bold(text) {
  return new TextRun({ text, font: "Times New Roman", size: 22, color: C.body, bold: true });
}

function normal(text) {
  return new TextRun({ text, font: "Times New Roman", size: 22, color: C.body });
}

function italic(text) {
  return new TextRun({ text, font: "Times New Roman", size: 22, color: C.body, italics: true });
}

function ref(text) {
  return new Paragraph({
    spacing: { after: 80, line: 250 },
    indent: { left: 480, hanging: 480 },
    children: [new TextRun({ text, font: "Times New Roman", size: 20, color: C.body })]
  });
}

function makeCell(text, opts = {}) {
  const isHead = opts.header || false;
  return new TableCell({
    borders: cellB,
    shading: isHead ? { fill: C.tableHead, type: ShadingType.CLEAR } : { fill: C.white, type: ShadingType.CLEAR },
    verticalAlign: VerticalAlign.CENTER,
    width: opts.width ? { size: opts.width, type: WidthType.PERCENTAGE } : undefined,
    children: [new Paragraph({
      spacing: { before: 40, after: 40 },
      alignment: AlignmentType.CENTER,
      children: [new TextRun({
        text, font: "Times New Roman", size: 18,
        bold: isHead, color: C.body
      })]
    })]
  });
}

function makeTable(headers, rows, colWidths) {
  const totalW = colWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [
      new TableRow({
        children: headers.map((h, i) => makeCell(h, { header: true, width: colWidths[i] }))
      }),
      ...rows.map(row => new TableRow({
        children: row.map((cell, i) => makeCell(cell, { width: colWidths[i] }))
      }))
    ]
  });
}

function spacer() {
  return new Paragraph({ spacing: { after: 100 }, children: [] });
}

// ========== BUILD DOCUMENT ==========

const doc = new Document({
  styles: {
    default: {
      document: {
        run: { font: "Times New Roman", size: 22, color: C.body },
        paragraph: { spacing: { line: 276 } }
      }
    }
  },
  numbering: {
    config: [{
      reference: "bullet-list",
      levels: [{
        level: 0,
        format: LevelFormat.BULLET,
        text: "\u2022",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } }
      }]
    }]
  },
  sections: [
    // ===== COVER PAGE =====
    {
      properties: {
        page: {
          margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 }
        }
      },
      children: [
        spacer(), spacer(), spacer(), spacer(), spacer(), spacer(),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 200 },
          children: [new TextRun({ text: "SURVEY PAPER", font: "Times New Roman", size: 24, color: C.secondary, bold: true })]
        }),
        spacer(),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 300 },
          children: [new TextRun({
            text: "Uncertainty-Driven Aggregation in Federated Learning:",
            font: "Times New Roman", size: 44, bold: true, color: C.primary
          })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 400 },
          children: [new TextRun({
            text: "A Cross-Modal Survey from Token Entropy to Predictive Confidence",
            font: "Times New Roman", size: 36, bold: true, color: C.primary
          })]
        }),
        spacer(),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 100 },
          children: [new TextRun({
            text: "Bridging LLM Uncertainty Quantification, CV Predictive Confidence,",
            font: "Times New Roman", size: 22, color: C.secondary, italics: true
          })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 400 },
          children: [new TextRun({
            text: "and Federated Aggregation Strategies",
            font: "Times New Roman", size: 22, color: C.secondary, italics: true
          })]
        }),
        spacer(), spacer(),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 80 },
          children: [new TextRun({ text: "May 2026", font: "Times New Roman", size: 22, color: C.secondary })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 80 },
          children: [new TextRun({ text: "Preprint", font: "Times New Roman", size: 22, color: C.secondary })]
        }),
        new Paragraph({ children: [new PageBreak()] })
      ]
    },

    // ===== MAIN CONTENT =====
    {
      properties: {
        page: {
          margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 }
        }
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: "Uncertainty-Driven Aggregation in Federated Learning: A Cross-Modal Survey", font: "Times New Roman", size: 16, color: C.accent, italics: true })]
          })]
        })
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "Page ", font: "Times New Roman", size: 16, color: C.accent }),
              new TextRun({ children: [PageNumber.CURRENT], font: "Times New Roman", size: 16, color: C.accent })
            ]
          })]
        })
      },
      children: [
        // TOC
        new Paragraph({
          spacing: { after: 300 },
          children: [new TextRun({ text: "Table of Contents", font: "Times New Roman", size: 32, bold: true, color: C.primary })]
        }),
        new TableOfContents("Table of Contents", {
          hyperlink: true,
          headingStyleRange: "1-3"
        }),
        new Paragraph({ children: [new PageBreak()] }),

        // ===== ABSTRACT =====
        h1("Abstract"),
        para("Federated Learning (FL) has emerged as a foundational paradigm for privacy-preserving collaborative machine learning, enabling multiple clients to train shared models without exposing raw data. However, standard aggregation strategies\u2014most notably FedAvg\u2014treat all client contributions equally, implicitly assuming uniform data quality and model reliability. This assumption breaks down in practice: real-world federated systems exhibit significant data heterogeneity (Non-IID distributions), varying client expertise, and differing noise levels. The resulting \"conformity effect\" causes global models to be dominated by majority-party clients, diluting the specialized knowledge of minority contributors."),
        para("Simultaneously, rapid advances in uncertainty quantification (UQ) have provided powerful tools for measuring model confidence. In natural language processing (NLP), token-level entropy and semantic entropy have proven effective for detecting hallucinations in large language models (LLMs). In computer vision (CV), predictive uncertainty via softmax entropy, Monte Carlo Dropout, and deep ensembles has become standard practice for identifying misclassifications and out-of-distribution samples. Despite these parallel developments, the intersection of model uncertainty and federated aggregation remains largely unexplored."),
        para("This survey provides the first comprehensive cross-modal review of uncertainty-driven aggregation in federated learning. We systematically examine: (1) FL aggregation strategies and their implicit assumptions about client reliability; (2) uncertainty quantification methods across NLP and CV modalities; (3) the conformity problem in federated aggregation, drawing connections to social psychology and social choice theory; (4) hallucination and misclassification detection via uncertainty signals; and (5) the nascent but growing body of work on uncertainty-aware federated aggregation. We identify critical research gaps, propose a unified framework (Entropy-Weighted Aggregation, EWA) that leverages model-internal uncertainty as an aggregation signal, and outline a roadmap for future research. Our analysis spans healthcare, finance, and industrial IoT applications, demonstrating the broad applicability and urgency of uncertainty-driven approaches in federated systems."),
        paraRuns([bold("Keywords: "), italic("Federated Learning, Uncertainty Quantification, Token Entropy, Predictive Uncertainty, Aggregation Strategies, Conformity Effect, Hallucination Detection, Non-IID Data, Cross-Modal Learning")]),

        // ===== 1. INTRODUCTION =====
        h1("1. Introduction"),
        para("The proliferation of data-driven artificial intelligence has created an inherent tension between the need for large, diverse training datasets and the imperative to protect individual and institutional data privacy. Federated Learning (FL), introduced by McMahan et al. (2017), offers an elegant resolution: rather than centralizing data, FL distributes the training process across multiple clients, each contributing model updates (gradients or parameters) to a central server that aggregates them into a global model. This paradigm has found applications in healthcare (cross-hospital medical imaging), finance (cross-institutional fraud detection), mobile devices (keyboard prediction), and industrial IoT (manufacturing quality control)."),
        para("At the heart of every FL system lies the aggregation strategy\u2014the mechanism by which the server combines client updates into a coherent global model. The canonical approach, FedAvg, performs a simple weighted average of client parameters, where weights are proportional to local dataset sizes. This strategy is mathematically clean and computationally efficient, but it rests on a critical assumption: all client contributions are equally reliable. In practice, this assumption is violated in multiple ways. Clients may have vastly different data distributions (the Non-IID problem), varying data quality (noisy labels, missing values), different computational capabilities (affecting convergence quality), and even malicious intent (Byzantine attacks)."),
        para("The consequences of ignoring client heterogeneity are profound. We term this the \"conformity effect\" in federated aggregation, drawing an analogy to Asch's classic conformity experiments in social psychology (1951). Just as individuals in a group may suppress their correct judgment to conform to a majority opinion, minority-party clients in FL see their specialized knowledge diluted by the statistical weight of majority-party clients. A hospital specializing in rare diseases, a financial analyst covering niche markets, or a factory producing unusual product variants\u2014all may find their expertise washed out in the global model."),
        para("Meanwhile, the field of uncertainty quantification (UQ) has matured significantly across both NLP and CV. For LLMs, Farquhar et al. (2024) demonstrated that semantic entropy\u2014a measure derived from the variability of model outputs under stochastic decoding\u2014can reliably detect hallucinations, a finding published in Nature. The \"inner confidence\" framework goes further, showing that token-level conditional probability entropy provides an honest signal of model uncertainty, in contrast to declared confidence which is often poorly calibrated. In CV, predictive uncertainty estimation via softmax entropy, Monte Carlo Dropout (Gal and Ghahramani, 2016), and deep ensembles (Lakshminarayanan et al., 2017) has become standard practice for safety-critical applications."),
        para("These two research streams\u2014FL aggregation and model uncertainty\u2014have developed largely in isolation. A small but growing body of work has begun to explore uncertainty-aware federated aggregation, but existing approaches are fragmented, modality-specific, and lack a unifying theoretical framework. No prior survey has systematically examined the intersection of these fields across both NLP and CV modalities."),
        para("This survey makes the following contributions:"),
        para("(C1) We provide the first cross-modal survey of uncertainty-driven aggregation in FL, covering both NLP (token entropy, semantic entropy) and CV (softmax entropy, Bayesian methods) uncertainty signals."),
        para("(C2) We formalize the \"conformity effect\" in federated aggregation, establishing connections to social psychology (Asch, 1951), social choice theory (Condorcet, 1785), and the computational learning theory of agnostic FL (Mohri et al., 2019)."),
        para("(C3) We identify five critical research gaps at the intersection of UQ and FL, and propose a unified Entropy-Weighted Aggregation (EWA) framework that addresses these gaps."),
        para("(C4) We provide a systematic cross-modal comparison of NLP and CV uncertainty characteristics and their implications for federated aggregation design."),
        para("(C5) We survey applications across healthcare, finance, and industrial IoT, demonstrating the practical urgency of uncertainty-driven approaches."),

        // ===== 2. FL FOUNDATIONS =====
        h1("2. Federated Learning: Foundations and Aggregation"),

        h2("2.1 The FL Paradigm"),
        para("In a standard FL setting, K clients collaboratively train a global model w without sharing their local datasets D_1, D_2, ..., D_K. Each round t consists of: (1) server broadcasts the current global model w_t to selected clients; (2) each selected client c performs local training on D_c to produce an updated model w_c^{t+1}; (3) server aggregates all client updates into a new global model w_{t+1}. The key constraint is that only model parameters (or gradients) are communicated\u2014raw data never leaves the client."),
        para("The success of FL depends critically on the aggregation strategy. A poorly designed aggregator can lead to slow convergence, biased global models, or even complete training failure in the presence of adversarial clients. The choice of aggregation strategy implicitly encodes assumptions about client reliability, data distribution, and the nature of the learning task."),

        h2("2.2 Standard Aggregation Strategies"),
        para("FedAvg (McMahan et al., 2017) computes a weighted average of client parameters, with weights proportional to local dataset sizes: w_{t+1} = sum_c (n_c / n) * w_c^{t+1}. While simple and effective under IID conditions, FedAvg degrades significantly under Non-IID data distributions, where client data distributions diverge substantially."),
        para("FedProx (Li et al., 2020) addresses this by adding a proximal term to the local objective, penalizing deviations from the global model: min_w_c [ L_c(w_c) + (mu/2) * ||w_c - w_t||^2 ]. This constrains local updates and improves convergence under heterogeneity, but does not modify the aggregation itself."),
        para("FedNova (Wang et al., 2020) normalizes local updates by the number of local training steps, addressing the \"client drift\" problem caused by varying amounts of local computation. FedBN (Li et al., 2021) keeps batch normalization statistics local, only aggregating other parameters, which is particularly effective for CV tasks where BN statistics encode data distribution information."),
        para("SCAFFOLD (Karimireddy et al., 2020) introduces control variates to correct for client drift, achieving state-of-the-art convergence under Non-IID conditions. However, it requires additional communication overhead for transmitting control variates."),

        h2("2.3 Quality-Aware and Attention-Based Aggregation"),
        para("A growing line of research recognizes that not all client contributions are equally valuable. FedDQA (2024) introduces data quality-aware client selection, discovering that increased data noise leads to degraded global model performance. FedCon (2025) dynamically adjusts aggregation weights while evaluating client contributions. FedAWR (2025) proposes adaptive learning rate adjustment during aggregation."),
        para("Attention-based approaches assign learned weights to client contributions. FCSA (2024) proposes a Federated Client Selection and Attention Aggregation algorithm. FedABC (2025) uses attention-based client selection for weighted aggregation. Adaptive graph attention-based FL for IoT (2025) assigns higher weights to reliable clients through a trust-aware mechanism. These approaches represent a shift from treating aggregation as a fixed rule to treating it as a learned, data-dependent process."),
        para("However, existing quality-aware methods rely on external signals (loss values, gradient norms, historical accuracy) to assess client quality. They do not leverage the model's own internal uncertainty\u2014a signal that is inherently available, requires no additional computation, and reflects the model's genuine assessment of its own knowledge."),

        h2("2.4 Byzantine-Robust Aggregation"),
        para("Byzantine-robust aggregation addresses the threat of malicious clients who may send arbitrary (potentially adversarial) model updates. Krum (Blanchard et al., 2017) selects the single update closest to the majority, while trimmed mean and median aggregation remove extreme values. FedCVG (2025) proposes a two-stage robust optimization algorithm validated against FedAvg, Krum, FedProx, and SCAFFOLD under Byzantine attacks."),
        para("While Byzantine-robust methods and uncertainty-driven aggregation share the goal of identifying unreliable clients, they operate at different levels. Byzantine methods assume a fraction of clients are actively malicious, while uncertainty-driven methods assume all clients are well-intentioned but vary in their data quality and model confidence. In practice, these approaches are complementary: uncertainty weighting can identify naturally unreliable clients, while Byzantine methods can defend against actively malicious ones."),

        // ===== 3. UQ CROSS-MODAL =====
        h1("3. Uncertainty Quantification: A Cross-Modal Perspective"),

        h2("3.1 Foundations: Types of Uncertainty"),
        para("Uncertainty in machine learning is typically decomposed into two components. Aleatoric uncertainty (data uncertainty) arises from inherent noise or ambiguity in the data\u2014for example, a medical image that is genuinely ambiguous even to expert radiologists. Epistemic uncertainty (model uncertainty) arises from the model's lack of knowledge\u2014for example, a model encountering a disease pattern it has never seen during training. A well-calibrated model should express high uncertainty in both cases, but for different reasons."),
        para("In the context of federated learning, both types of uncertainty are relevant. Aleatoric uncertainty varies across clients (some clients have noisier data than others), while epistemic uncertainty varies across the global model's coverage of the data space (some clients cover rare but important regions). An ideal aggregation strategy should account for both."),

        h2("3.2 NLP: Token-Level Entropy and Semantic Uncertainty"),

        h3("3.2.1 Token Probability and Logprobs"),
        para("Autoregressive language models generate text one token at a time, producing a conditional probability distribution P(x_t | x_{<t}) over the vocabulary at each step. The Shannon entropy of this distribution, H(x_t) = -sum P(x_i | x_{<t}) * log P(x_i | x_{<t}), provides a per-token measure of the model's uncertainty. Low entropy indicates the model is confident about its next token; high entropy indicates uncertainty."),
        para("Token-level entropy has several desirable properties: (1) it is computed from the model's internal probability distribution, not from post-hoc self-assessment; (2) it is available at no additional computational cost during generation; (3) it captures uncertainty at the finest granularity (individual tokens). Burns et al. (2023) and Azaria and Mitchell (2023) demonstrated that token probabilities can effectively distinguish between correct and incorrect model outputs."),

        h3("3.2.2 Semantic Entropy"),
        para("Farquhar et al. (2024), in a landmark paper published in Nature, introduced semantic entropy as a more robust hallucination detection method. Rather than examining individual token probabilities, semantic entropy measures the variability in the semantic meaning of multiple generated responses. If a model generates semantically equivalent responses across multiple sampling runs, it is likely confident; if it generates diverse meanings, it is likely hallucinating."),
        para("Semantic entropy addresses a key limitation of token-level entropy: the model may be confident about individual tokens (low token entropy) while being uncertain about the overall meaning (high semantic entropy). This can happen when the model has learned a fluent but factually incorrect generation pattern. Semantic entropy probes (SEPs), introduced by Kuhn et al. (2024), provide a cheaper approximation that does not require multiple generation passes."),

        h3("3.2.3 Inner Confidence"),
        para("The \"inner confidence\" framework, explored in recent deep research reports, posits that token entropy provides a more honest signal of model uncertainty than declared confidence (the model's self-reported certainty). In financial forecasting experiments with 100,000 Reuters news articles, predictions sorted by inner confidence into quintiles showed a stark accuracy gradient\u2014from approximately 51% (barely above random chance) in the lowest-confidence group to approximately 65% in the highest-confidence group. This predictive power translates into economically significant trading signals."),
        para("The theoretical foundation rests on two pillars. First, declared confidence is contaminated by \"narrative bias\"\u2014the model may construct a plausible-sounding justification for an incorrect answer, leading it to report high confidence in a falsehood. Second, \"decoding bias\" arises from the path-dependent nature of autoregressive generation: the choice of early tokens constrains the probability space for subsequent tokens, creating a feedback loop that can amplify initial errors."),

        h3("3.2.4 Practical UQ Tools for LLMs"),
        para("UQLM (2026), published in JMLR, provides a comprehensive Python package for LLM hallucination detection using state-of-the-art uncertainty quantification techniques. It implements multiple UQ methods including token probability, semantic entropy, and their combinations, offering a standardized toolkit for researchers and practitioners. Pre-trained uncertainty quantification heads (EMNLP 2025) provide supplementary modules that yield substantially better performance at estimating model confidence without requiring architectural changes to the base LLM."),

        h2("3.3 CV: Predictive Uncertainty in Vision Models"),

        h3("3.3.1 Softmax Entropy"),
        para("For classification models, the softmax output provides a probability distribution over classes. The Shannon entropy of this distribution, H(y|x) = -sum p_j * log p_j, is the simplest and most widely used measure of predictive uncertainty. A confident prediction concentrates probability mass on a single class (low entropy), while an uncertain prediction spreads it across multiple classes (high entropy)."),
        para("Softmax entropy is computationally free (available after a single forward pass) and interpretable. However, it is well-known that modern neural networks are typically overconfident\u2014they produce excessively low entropy even on incorrect predictions. This miscalibration problem has been extensively documented (Guo et al., 2017) and motivates the use of more sophisticated UQ methods."),

        h3("3.3.2 Bayesian Approaches"),
        para("Monte Carlo Dropout (MC Dropout; Gal and Ghahramani, 2016) provides a practical approximation to Bayesian inference by performing multiple forward passes with dropout enabled. The variance of predictions across these passes captures epistemic uncertainty. Deep Ensembles (Lakshminarayanan et al., 2017) train multiple independent models and aggregate their predictions, capturing both aleatoric and epistemic uncertainty. While more accurate than softmax entropy, these methods incur significant computational overhead (multiple forward passes or multiple models), which is particularly problematic in federated settings where clients may have limited computational resources."),
        para("Evidential Deep Learning provides a single-pass alternative that captures both types of uncertainty by parameterizing the output distribution with evidential priors. This approach has shown promise in medical imaging applications where computational efficiency is critical."),

        h3("3.3.3 Spatial Uncertainty and Grad-CAM"),
        para("For image classification with convolutional and transformer architectures, uncertainty can be spatially localized. Grad-CAM (Selvaraju et al., 2017) generates attention maps highlighting image regions most influential to the prediction. When combined with uncertainty estimation, these maps can reveal spatial uncertainty\u2014regions where the model is unsure about its classification. For Vision Transformers (ViT), patch-level attention weights provide a natural mechanism for spatial uncertainty estimation, as each image patch contributes independently to the final classification."),

        h2("3.4 Calibration and Overconfidence"),
        para("A fundamental challenge in deploying uncertainty-aware systems is calibration: the alignment between predicted confidence and actual accuracy. Expected Calibration Error (ECL) measures the average discrepancy between confidence and accuracy across confidence bins. Modern neural networks are notoriously poorly calibrated\u2014Guo et al. (2017) showed that temperature scaling (a single-parameter post-hoc calibration) significantly improves calibration on ResNet and DenseNet architectures."),
        para("Recent work has extended calibration to LLMs. Kadavath et al. (2022) demonstrated that LLMs' declared confidence is poorly calibrated, often expressing high confidence in incorrect answers. The CLUE method (2025) introduces calibration via learning uncertainty-error alignment, explicitly aligning predicted uncertainty with actual prediction errors. These findings underscore the importance of using internal probability distributions (token entropy, softmax entropy) rather than declared confidence as uncertainty signals."),

        // ===== 4. CONFORMITY =====
        h1("4. The Conformity Problem in Federated Aggregation"),

        h2("4.1 From Social Psychology to Machine Learning"),
        para("Solomon Asch's conformity experiments (1951) demonstrated that individuals frequently suppress their correct judgment to conform to a clearly incorrect majority opinion. In a classic setup, participants were asked to judge the length of lines, with confederates deliberately giving wrong answers. Approximately one-third of participants conformed to the majority at least once, despite the correct answer being obvious."),
        para("We argue that an analogous phenomenon occurs in federated learning. Consider a medical FL system with five clients: two large research hospitals (majority) and three smaller specialized clinics (minority). The large hospitals handle common diseases and have large, diverse datasets. The smaller clinics specialize in rare conditions and have smaller, more focused datasets. Under FedAvg, the global model is dominated by the majority's parameter updates, causing it to perform well on common diseases but poorly on rare ones\u2014precisely the cases where the specialized clinics' knowledge is most valuable."),
        para("This \"model conformity\" is not a bug but a direct mathematical consequence of weighted averaging when data distributions are heterogeneous. The more clients diverge from the majority distribution, the more their knowledge is diluted. This effect is exacerbated by the Non-IID nature of real-world federated data."),

        h2("4.2 Formalizing Conformity in FL"),
        para("We define the conformity degree (CD) as the performance gap between a minority client's local model and the global model on that client's data: CD_c = Acc_local_c - Acc_global_c. A positive CD indicates that the global model performs worse than the client's local model on the client's own data\u2014evidence that the client's knowledge has been diluted by conformity to the majority."),
        para("The aggregate conformity degree (ACD) across all minority clients measures the overall severity of the conformity problem: ACD = (1/|M|) * sum_{c in M} CD_c, where M is the set of minority clients. A high ACD indicates that the global model systematically fails to capture minority knowledge."),
        para("We hypothesize that the conformity degree is positively correlated with the degree of data heterogeneity (measured by Dirichlet alpha or similar metrics) and negatively correlated with the number of minority clients. These hypotheses can be empirically tested and provide a quantitative framework for studying the conformity effect."),

        h2("4.3 Connections to Social Choice Theory"),
        para("The conformity problem in FL aggregation bears deep connections to social choice theory, particularly Condorcet's jury theorem (1785) and the concept of the \"tyranny of the majority\" (Feffer et al., 2023). In social choice, the challenge is to aggregate individual preferences into a collective decision that respects minority rights. Similarly, in FL, the challenge is to aggregate client updates into a global model that preserves minority knowledge."),
        para("Feffer et al. (2023) explored this connection in the context of moral decision-making by AI systems, showing that majority-vote aggregation can lead to outcomes that harm minority populations. Their analysis draws on computational social choice theory and preference elicitation, providing a theoretical framework that is directly applicable to federated aggregation. The key insight is that simple averaging (whether of votes or model parameters) is fundamentally inadequate when the underlying distributions are heterogeneous."),

        // ===== 5. HALLUCINATION =====
        h1("5. Hallucination and Misclassification Detection"),

        h2("5.1 LLM Hallucination via Uncertainty"),
        para("LLM hallucination\u2014the generation of fluent but factually incorrect text\u2014is a critical challenge for deploying LLMs in high-stakes domains. Farquhar et al. (2024) demonstrated that entropy-based uncertainty estimators can detect a significant subset of hallucinations. Their semantic entropy method achieves state-of-the-art detection performance by measuring the variability of meaning across multiple generated responses."),
        para("Token-level entropy provides a complementary signal. When an LLM hallucinates, it often does so with high fluency\u2014the generated text reads naturally, and individual tokens may have high probability. However, at key decision points (e.g., entity names, numerical values, causal claims), the entropy spike reveals the model's uncertainty. Zou et al. (2025) showed that entropy spikes detected via z-score normalization can effectively identify hallucination boundaries."),
        para("The \"Logprobs Know Uncertainty\" framework (2025) proposes a logprob-based approach that proactively quantifies model uncertainty through antonym-based perturbation and multi-granularity analysis. UQLM (2026) provides a unified toolkit implementing multiple UQ methods for hallucination detection, enabling systematic comparison and practical deployment."),

        h2("5.2 CV Misclassification via Uncertainty"),
        para("In computer vision, predictive uncertainty serves as a natural misclassification detector. Samples with high softmax entropy are more likely to be misclassified. This relationship has been extensively validated across image classification, object detection, and semantic segmentation tasks. The advantage of uncertainty-based detection is that it does not require ground-truth labels\u2014it relies solely on the model's internal probability distribution."),
        para("For medical imaging, uncertainty-aware systems can flag cases where the model is unsure, routing them for human review rather than making autonomous decisions. This \"human-in-the-loop\" approach is particularly valuable in safety-critical applications. Grad-CAM entropy maps add spatial interpretability, showing clinicians exactly which image regions contributed to the model's uncertainty."),

        h2("5.3 Implications for Federated Learning"),
        para("The connection between uncertainty and error detection has profound implications for federated learning. If a client's model exhibits high average uncertainty on its local data, this is a strong signal that the client's data is noisy, out-of-distribution, or otherwise problematic. Such a client's model updates should contribute less to the global model\u2014not because the client is malicious, but because its updates are likely to be unreliable."),
        para("Conversely, a client with low average uncertainty likely has high-quality, well-distributed data and a well-converged local model. Such a client's updates should be weighted more heavily. This insight forms the basis of entropy-weighted aggregation: use the model's own uncertainty as a natural quality signal for aggregation weighting."),

        // ===== 6. INTERSECTION =====
        h1("6. The Intersection: Uncertainty-Driven Federated Aggregation"),

        h2("6.1 Existing Approaches"),
        para("A small but growing body of work has begun to explore the integration of uncertainty into federated aggregation. RESFL (2026) proposes an uncertainty-aware framework for responsible FL that incorporates uncertainty estimates into the aggregation process. FedWKD (2025) integrates bidirectional knowledge distillation, using distilled soft predictions as a form of uncertainty signal for weighted aggregation. FedIVON (2025) combines uncertainty estimation with personalization in federated learning, allowing clients to maintain personalized models with uncertainty-aware global components."),
        para("In the medical domain, several works have explored uncertainty-aware FL. Lopez et al. (2025) surveyed uncertainty in medical federated learning, covering variants of FL, UQ methods, and their intersection. An uncertainty-aware FL framework for clinical decision support (2025) reduces the influence of uncertain updates while incorporating differential privacy. The RSNA review (2025) provides an in-depth analysis of FL, privacy preservation, and UQ in medical imaging."),
        para("Entropy-adaptive differential privacy for FL (2025) proposes adapting the DP noise level based on entropy estimates, providing a direct connection between uncertainty and privacy. This is particularly relevant because standard DP adds uniform noise regardless of model confidence, which can be suboptimal: confident predictions need less noise protection, while uncertain predictions need more."),

        h2("6.2 Critical Research Gaps"),
        para("Despite these promising directions, several critical gaps remain:"),
        para("Gap 1: No unified framework. Existing approaches are fragmented, each addressing a specific aspect (privacy, personalization, robustness) without a common theoretical foundation. There is no framework that unifies NLP and CV uncertainty signals under a single aggregation mechanism."),
        para("Gap 2: Limited cross-modal validation. Most existing works focus on either NLP or CV, but not both. The structural similarity between token entropy (NLP) and softmax entropy (CV) suggests that a unified approach should be possible, but this has not been systematically explored."),
        para("Gap 3: No conformity-aware aggregation. While the conformity effect in FL has been informally discussed, no existing work explicitly addresses it through uncertainty-driven weighting. The connection between model uncertainty and conformity mitigation remains unexplored."),
        para("Gap 4: Minimal hallucination-aware FL. Despite the importance of hallucination detection in LLMs, no existing FL aggregation strategy explicitly filters or downweights hallucination-prone client updates."),
        para("Gap 5: Lack of entropy-specific aggregation theory. Existing quality-aware methods use loss, gradient norms, or historical accuracy as quality signals. The theoretical properties of entropy as an aggregation weight (convergence guarantees, optimality conditions) have not been established."),

        h2("6.3 The EWA Framework"),
        para("We propose the Entropy-Weighted Aggregation (EWA) framework as a unifying approach that addresses these gaps. The core idea is simple: replace the uniform (or data-size-based) weights in FedAvg with entropy-derived weights that reflect each client's model confidence."),
        para("Formally, let H_c be the average entropy of client c's model on its local validation set. The EWA aggregation weight for client c is: w_c = exp(-alpha * H_c) / sum_j exp(-alpha * H_j), where alpha is a temperature parameter controlling the sharpness of the weighting. When alpha = 0, EWA reduces to uniform weighting (equivalent to FedAvg with equal data sizes). As alpha increases, the weighting becomes more aggressive, giving exponentially more weight to low-entropy (high-confidence) clients."),
        para("The EWA framework is agnostic to the modality of uncertainty: for NLP tasks, H_c is the average token-level Shannon entropy; for CV tasks, H_c is the average softmax entropy. This cross-modal generality is a key advantage over existing approaches that are tied to specific modalities or architectures."),
        para("EWA has several desirable properties: (1) it requires only a single scalar (the average entropy) to be communicated per client per round, adding negligible communication overhead; (2) it does not require historical information, avoiding cold-start problems that plague reputation-based methods; (3) it naturally adapts to changing data distributions, as entropy reflects the model's current state rather than past performance."),

        // ===== 7. CROSS-MODAL COMPARISON =====
        h1("7. Cross-Modal Comparison: NLP vs CV Uncertainty in FL"),

        h2("7.1 Structural Comparison"),
        makeTable(
          ["Dimension", "NLP (Token Entropy)", "CV (Softmax Entropy)"],
          [
            ["Uncertainty Source", "Conditional token probability P(x_t | x_{<t})", "Class posterior P(y | x)"],
            ["Granularity", "Per-token (fine)", "Per-sample (coarse)"],
            ["Spatial Resolution", "None (sequential)", "Grad-CAM / patch attention (spatial)"],
            ["Entropy Range", "Wide (0 to log|V|)", "Narrow (0 to log C)"],
            ["Computation Cost", "Free (during generation)", "Free (single forward pass)"],
            ["Calibration", "Poor (LLMs overconfident)", "Moderate (improved by temp scaling)"],
            ["Semantic Sensitivity", "High (semantic entropy)", "Low (pixel-level only)"],
            ["Multi-sample Methods", "Semantic entropy (multiple generations)", "MC Dropout / Deep Ensembles"],
            ["FL Communication Overhead", "1 scalar per client per round", "1 scalar per client per round"],
            ["Key Challenge", "Decoding bias, narrative bias", "Overconfidence, miscalibration"],
          ],
          [25, 37, 38]
        ),
        spacer(),

        h2("7.2 Implications for Federated Aggregation"),
        para("The structural differences between NLP and CV uncertainty have important implications for federated aggregation design. The wider entropy range in NLP suggests that the temperature parameter alpha in EWA may need to be larger for NLP tasks to achieve meaningful differentiation between clients. The finer granularity of token-level entropy in NLP provides more information for aggregation weighting but also introduces more noise, potentially requiring smoothing or averaging across tokens."),
        para("The spatial resolution available in CV (via Grad-CAM or patch attention) offers a unique advantage: it allows the aggregation to be sensitive not just to how uncertain a client's model is, but where in the input space the uncertainty is concentrated. This could enable spatially-aware aggregation, where different image regions receive different weights based on the client's local expertise."),
        para("The semantic sensitivity of NLP uncertainty (via semantic entropy) is both a strength and a challenge. On one hand, it captures higher-level uncertainty that token entropy misses. On the other hand, it requires multiple generation passes, increasing computational cost. For federated settings where clients have limited resources, the trade-off between semantic entropy's accuracy and computational cost must be carefully managed."),

        // ===== 8. APPLICATION DOMAINS =====
        h1("8. Application Domains"),

        h2("8.1 Healthcare"),
        para("Healthcare is perhaps the most compelling domain for uncertainty-driven federated aggregation. Medical FL systems typically involve hospitals with vastly different patient populations, equipment quality, and diagnostic expertise. A large urban hospital may have thousands of diverse cases, while a specialized clinic may have fewer but deeper expertise in rare conditions."),
        para("In medical imaging FL, predictive uncertainty (softmax entropy, MC Dropout) can identify cases where the global model is likely to be wrong, enabling human-in-the-loop workflows. The conformity effect is particularly dangerous here: if the global model is dominated by large hospitals, it may fail on rare diseases that only specialized clinics encounter. EWA can mitigate this by giving higher weight to specialized clinics when their models exhibit low uncertainty on their local data."),
        para("For NLP-based clinical applications (e.g., clinical note classification, diagnosis suggestion), token entropy and semantic entropy can detect hallucinated medical claims\u2014a critical safety requirement. The combination of uncertainty-driven aggregation and hallucination detection creates a multi-layered safety net: EWA prevents unreliable client updates from contaminating the global model, while per-sample uncertainty filtering catches remaining errors at inference time."),

        h2("8.2 Finance"),
        para("Financial FL systems face similar challenges: large institutions with diverse portfolios dominate the global model, while specialized analysts covering niche markets see their expertise diluted. The inner confidence framework's validation on financial forecasting (100,000 Reuters articles, 14% accuracy gap between high and low confidence quintiles) demonstrates the direct applicability of token entropy to financial NLP tasks."),
        para("In federated sentiment analysis for financial markets, EWA can weight client contributions by their model's confidence on local data. A client covering emerging markets (where data is noisier and models are less certain) would naturally receive lower weight than a client covering established markets (where models are more confident). This is not a value judgment about the importance of emerging markets, but a reflection of the model's genuine uncertainty\u2014which is precisely the signal that should drive aggregation weighting."),

        h2("8.3 Industrial IoT"),
        para("In industrial settings, FL enables collaborative quality control across multiple production lines or factories. Different factories may produce different product variants, use different equipment, or operate under different environmental conditions. The resulting data heterogeneity makes standard aggregation ineffective."),
        para("CV-based defect detection systems (e.g., PCB inspection, surface defect classification) can benefit from uncertainty-driven aggregation. A factory that frequently encounters a specific defect type will have a well-calibrated model for that defect (low entropy), while a factory that rarely encounters it will have high entropy. EWA naturally gives more weight to the experienced factory's updates for that defect type, preserving specialized knowledge."),

        // ===== 9. OPEN CHALLENGES =====
        h1("9. Open Challenges and Future Directions"),

        h2("9.1 Theoretical Foundations"),
        para("The theoretical understanding of entropy-weighted aggregation is still in its infancy. Key open questions include: (1) Under what conditions does EWA converge, and at what rate compared to FedAvg? (2) What is the optimal temperature parameter alpha, and how should it be set? (3) Can we establish regret bounds or optimality guarantees for EWA under specific assumptions about the data distribution? (4) How does EWA interact with differential privacy\u2014does entropy weighting amplify or attenuate the privacy-utility trade-off?"),
        para("The connection to social choice theory suggests that tools from computational social choice (e.g., the Dodgson score, the Young score) may provide theoretical insights for designing aggregation rules that respect minority knowledge. The conformity degree metric proposed in Section 4.2 provides a starting point for formal analysis."),

        h2("9.2 Practical Considerations"),
        para("Several practical challenges must be addressed for real-world deployment. First, entropy estimation requires a validation set at each client, which may not always be available. Second, entropy can be unstable in early training rounds when the model has not yet converged, potentially requiring a warm-up period. Third, the relationship between entropy and accuracy is not perfect\u2014low entropy can indicate either genuine expertise or confident errors (the \"confidently wrong\" problem)."),
        para("Communication efficiency is another concern. While EWA adds only a single scalar per client per round, the entropy computation itself requires a forward pass on the validation set. For resource-constrained clients, this may be non-trivial. Efficient entropy estimation methods (e.g., using a subset of the validation set, or caching entropy values across rounds) may be necessary."),

        h2("9.3 Emerging Directions"),
        para("Several exciting research directions are emerging at the intersection of UQ and FL. First, the integration of EWA with differential privacy (entropy-adaptive DP) promises to improve the privacy-utility trade-off by adding more noise to uncertain updates and less to confident ones. Second, the extension to multimodal models (e.g., vision-language models) raises new questions about how to combine entropy signals from different modalities."),
        para("Third, the application of EWA to federated LLM fine-tuning (FedLLM) is particularly promising. As LLMs are increasingly fine-tuned via federated learning (LoRA-based FL, split learning), entropy-weighted aggregation can ensure that clients with high-quality fine-tuning data contribute more to the global LLM. Fourth, the combination of EWA with Byzantine-robust methods could provide comprehensive protection against both natural unreliability and active adversaries."),
        para("Finally, the development of standardized benchmarks for uncertainty-driven FL aggregation is urgently needed. Existing FL benchmarks (e.g., LEAF, FedML) do not include uncertainty metrics, and UQ benchmarks do not include federated settings. A unified benchmark covering multiple modalities, tasks, and uncertainty metrics would significantly accelerate progress in this field."),

        // ===== 10. CONCLUSION =====
        h1("10. Conclusion"),
        para("This survey has examined the intersection of uncertainty quantification and federated learning aggregation from a cross-modal perspective, covering both NLP (token entropy, semantic entropy) and CV (softmax entropy, Bayesian methods) uncertainty signals. We have formalized the \"conformity effect\" in federated aggregation, identified five critical research gaps, and proposed the Entropy-Weighted Aggregation (EWA) framework as a unifying approach."),
        para("The key insight underlying this survey is that model uncertainty\u2014whether measured as token entropy in NLP or softmax entropy in CV\u2014provides a natural, honest, and computationally cheap signal for aggregation weighting. Unlike external quality metrics (loss, gradient norms, historical accuracy), entropy is an intrinsic property of the model's probability distribution that requires no additional computation and reflects the model's genuine assessment of its own knowledge."),
        para("The practical implications are significant. In healthcare, uncertainty-driven aggregation can prevent the dilution of specialized medical knowledge. In finance, it can ensure that confident market insights are weighted more heavily than uncertain ones. In industrial IoT, it can preserve defect detection expertise across heterogeneous production environments."),
        para("We hope this survey catalyzes further research at this intersection. The field is ripe for theoretical advances (convergence guarantees, optimality conditions), empirical validation (large-scale cross-modal experiments), and practical deployment (integration with existing FL frameworks). As AI systems become increasingly deployed in high-stakes domains, the marriage of uncertainty quantification and federated learning will be essential for building systems that are not only accurate and private, but also honest about what they do not know."),

        // ===== REFERENCES =====
        h1("References"),
        ref("[1] McMahan, B., et al. (2017). \"Communication-Efficient Learning of Deep Networks from Decentralized Data.\" AISTATS."),
        ref("[2] Li, T., et al. (2020). \"Federated Optimization in Heterogeneous Networks.\" MLSys (FedProx)."),
        ref("[3] Wang, J., et al. (2020). \"Tackling the Objective Inconsistency Problem in Heterogeneous Federated Optimization.\" NeurIPS (FedNova)."),
        ref("[4] Li, X., et al. (2021). \"Federated Learning on Non-IID Data Silos: An Experimental Study.\" ICDE (FedBN)."),
        ref("[5] Karimireddy, S. P., et al. (2020). \"SCAFFOLD: Stochastic Controlled Averaging for Federated Learning.\" ICML."),
        ref("[6] Blanchard, P., et al. (2017). \"Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent.\" NeurIPS."),
        ref("[7] Farquhar, S., et al. (2024). \"Detecting Hallucinations in Large Language Models Using Semantic Entropy.\" Nature."),
        ref("[8] Gal, Y. and Ghahramani, Z. (2016). \"Dropout as a Bayesian Approximation: Representing Model Uncertainty in Deep Learning.\" ICML."),
        ref("[9] Lakshminarayanan, B., et al. (2017). \"Simple and Scalable Predictive Uncertainty Estimation using Deep Ensembles.\" NeurIPS."),
        ref("[10] Guo, C., et al. (2017). \"On Calibration of Modern Neural Networks.\" ICML."),
        ref("[11] Kadavath, S., et al. (2022). \"Language Models (Mostly) Know What They Know.\" arXiv."),
        ref("[12] Burns, C., et al. (2023). \"Discovering Latent Knowledge in Language Models Without Supervision.\" arXiv."),
        ref("[13] Azaria, A. and Mitchell, T. (2023). \"The Internal State of an LLM Knows When It's Lying.\" arXiv."),
        ref("[14] Kuhn, L., et al. (2024). \"Semantic Entropy Probes: Robust and Cheap Hallucination Detection in LLMs.\" arXiv."),
        ref("[15] Selvaraju, R. R., et al. (2017). \"Grad-CAM: Visual Explanations from Deep Networks via Gradient-based Localization.\" ICCV."),
        ref("[16] Asch, S. E. (1951). \"Effects of Group Pressure upon the Modification and Distortion of Judgment.\" Groups, Leadership and Men."),
        ref("[17] Mohri, M., et al. (2019). \"Agnostic Federated Learning.\" ICML."),
        ref("[18] Feffer, M., Heidari, H., and Lipton, Z. C. (2023). \"Moral Machine or Tyranny of the Majority?\" NeurIPS."),
        ref("[19] UQLM (2026). \"UQLM: A Python Package for Uncertainty Quantification in Language Models.\" JMLR."),
        ref("[20] CLUE (2025). \"Neural Networks Calibration via Learning Uncertainty-Error Alignment.\" arXiv."),
        ref("[21] Zou, C., et al. (2025). \"Thinking, Faithful and Stable: Mitigating Hallucinations in LLMs via Entropy Spikes.\" Stanford CS224R."),
        ref("[22] Logprobs Know Uncertainty (2025). \"Fighting LLM Hallucinations.\" ACM FAccT."),
        ref("[23] RESFL (2026). \"An Uncertainty-Aware Framework for Responsible Federated Learning.\" arXiv."),
        ref("[24] FedWKD (2025). \"Federated Learning Weighted Aggregation with Knowledge Distillation.\" Information Fusion."),
        ref("[25] FedIVON (2025). \"Federated Learning with Uncertainty and Personalization.\" TMLR."),
        ref("[26] FedDQA (2024). \"Data Quality-Aware Client Selection in Heterogeneous Federated Learning.\" ResearchGate."),
        ref("[27] FedCon (2025). \"Scalable and Efficient Federated Learning via Dynamic Aggregation.\" Electronics."),
        ref("[28] FedAWR (2025). \"Aggregation Optimization in Federated Learning.\" Future Internet."),
        ref("[29] FCSA (2024). \"Federated Client Selection and Attention-Based Aggregation.\" IEEE."),
        ref("[30] FedABC (2025). \"Attention-Based Client Selection for Federated Learning.\" arXiv."),
        ref("[31] Entropy-Adaptive DP for FL (2025). Frontiers in Artificial Intelligence."),
        ref("[32] Exploring Uncertainty in Medical FL (2025). Electronics (MDPI)."),
        ref("[33] Privacy-Preserving FL and UQ in Medical Imaging (2025). RSNA."),
        ref("[34] Non-IID Data in FL: A Survey with Taxonomy (2024). arXiv."),
        ref("[35] A Survey on Federated Fine-Tuning of LLMs (2025). arXiv."),
        ref("[36] Federated Reasoning LLMs: A Survey (2025). FCS."),
        ref("[37] FedCVG (2025). \"A Two-Stage Robust Federated Learning Optimization Algorithm.\" Nature Scientific Reports."),
        ref("[38] Lopez, M., et al. (2025). \"Exploring Uncertainty in Medical Federated Learning: A Survey.\" Electronics."),
        ref("[39] Inner Confidence: Measuring LLM Uncertainty via Token Entropy. Deep Research Report, 2026."),
        ref("[40] Condorcet, M. J. A. N. (1785). Essai sur l'application de l'analyse a la probabilite des decisions rendues a la pluralite des voix."),
      ]
    }
  ]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("/home/z/my-project/download/Uncertainty_Driven_Aggregation_FL_Survey.docx", buffer);
  console.log("Survey DOCX generated successfully!");
  console.log("Size:", (buffer.length / 1024).toFixed(1), "KB");
});
