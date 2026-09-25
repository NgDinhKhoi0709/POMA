# Faithful Abstention for Open-ViTabQA — Ranked Shortlist

Scope: methods that let a sub-10B model decide **reliably** whether a table supports an answer, as a
*separate scored decision* rather than a prompt instruction. Table representation/reduction and answer
normalisation are out of scope by request.

---

## 0. The diagnosis in your brief is inverted — this reorders everything

Reconstructing POMA's Null-class confusion matrix from the numbers you gave (946 answerable, 46
unanswerable, 53 false abstentions, 11 hallucinations; total 992 ✓):

| | predicted Null | predicted answer |
|---|---|---|
| **gold Null** (46) | TP = 35 | FN = 11 |
| **gold answerable** (946) | FP = 53 | TN = 893 |

→ **Null precision 39.8 %, Null recall 76.1 %, F1 52.2 %** (reported 51.13 — the 1.1-point gap is
consistent with character-F1 partial credit rather than exact match, so the reconstruction is sound).

**The one-sentence diagnosis.** The system over-predicts Null in absolute terms (88 emitted vs 46 gold,
a factor of **1.9x**), so **precision (39.8 %) is the bottleneck** — but per item it is still far worse on
unanswerables (**23.9 %** missed) than on answerables (**5.6 %** falsely abstained), so "over-conservative"
*understates* the problem: the Null decision is both **too frequent and too noisy**. Recall (76.1 %) is
already respectable; there is little to gain there and much to lose.

Note that the "4.8x" in the brief is a ratio of raw error counts under 20:1 class imbalance, not a
measured cost ratio — see §3, where that distinction changes the threshold arithmetic.

This inverts the natural instinct (add a verifier that abstains harder). Killing false positives is
where all the leverage is, and it is the *only* move that raises Unanswerable-F1 and Answerable-F1
**simultaneously**:

| FPs removed (of 53) | Null-F1 |
|---|---|
| 10 | 56.5 |
| 20 | 61.4 |
| 30 | 67.3 |
| 53 (all) | 86.4 |

**Ranking principle adopted:** prefer methods that can **positively confirm that support exists**
(programmatic cell-grounding, entailment on a specific cell) over methods that measure *how unsure the
model is*. The latter push in the wrong direction on this dataset.

> **Missing datum you should extract before running anything:** the few-shot baseline's Null confusion
> matrix. Its F1 of 56.64 could come from better precision or better recall, and that determines whether
> POMA's orchestration adds FPs or loses TPs. One line of code over existing prediction files.

---

## 1. Deployment gate: logprob availability (verified today, live API)

Queried `https://openrouter.ai/api/v1/models` → `supported_parameters`:

| Backbone | `logprobs` | `top_logprobs` | Verdict |
|---|---|---|---|
| `qwen/qwen3-8b` | **false** | **false** | **No logprobs.** |
| `meta-llama/llama-3.1-8b-instruct` | true | true | OK |
| SEA-LION 8B | **no match** on OpenRouter for any of `sea-lion`, `sealion`, `aisingapore`, `singapore`, `sahabat` in id or display name | — | self-host (vLLM) or another provider |

This is a hard gate, decided before ranking. Anything needing token probabilities is **dead on your
primary Qwen backbone** unless you self-host with vLLM (which gives you logprobs *and* hidden states,
and changes the calculus for several methods below).

**Cost baseline (auditable).** Assumption: ~2 000-token serialised table prompt + ~150-token output.
Live OpenRouter pricing: Qwen3-8B $0.117/M in, $0.455/M out → **$0.000302/question = $0.30 per
992-question run**. Llama-3.1-8B: $0.11/run.

| Extra passes/question | Qwen3-8B cost per full run |
|---|---|
| 1 (baseline) | $0.30 |
| 2 | $0.60 |
| k=5 sampling | $1.50 |
| k=10 sampling | $3.00 — **over your $2 budget** |

So the budget is **much less binding than assumed**: one or two extra LLM calls per question is cheap.
Only k≈10 sampling strains it, and a local NLI model is free. Do not over-penalise multi-call methods.

---

## 2. Method cards

### 2.1 Retro-Reader — separate verifier + score fusion + tuned threshold

| field | value |
|---|---|
| Method + link | Retro-Reader (sketchy/intensive reading, E-FV + I-FV + rear verification) — https://arxiv.org/abs/2001.09694 |
| Venue + year | **AAAI 2021** (peer-reviewed) |
| Model sizes | BERT-large, ALBERT-xxlarge, ELECTRA-large (encoders, ≪10B). Not GPT-4-only. |
| Blockers | **Requires fine-tuning** the encoders. No logprobs needed. The *architecture* (two scores + weighted fusion + dev-tuned threshold) transfers without fine-tuning. |
| Gain on abstention | **Polarity verified from the table caption: "Performance on the unanswerable questions from SQuAD2.0 dev set" — positive class = unanswerable.** ALBERT P 91.70 / R 93.42 / F1 92.55 → Retro-Reader P **94.30** / R 92.38 / F1 **93.33**. Trades −1.0 recall for **+2.6 precision** — exactly the direction you need. |
| Cost | 2 encoder passes (parallel modules); at BERT scale this is milliseconds, not API calls. |
| ≥2 datasets? Multilingual? | Yes — SQuAD2.0 **and** NewsQA. **English only.** |

Mechanism worth stealing verbatim: `score_diff = score_null − score_has`; `v = β₁·score_diff + β₂·score_ext`;
emit answer iff `v > δ`, with **δ searched on the dev set**. Two independently-trained signals, linearly
fused, one tuned operating point. This is the canonical "abstention as a separate calibrated decision".

### 2.2 Sufficient Context — answerability judged *without* the answer

| field | value |
|---|---|
| Method + link | Sufficient Context autorater + selective generation — https://arxiv.org/abs/2411.06037 |
| Venue + year | **ICLR 2025** (peer-reviewed), Google/UCSD |
| Model sizes | Gemini 1.5 Pro, GPT-4o, Claude 3.5, Gemma 2 27B, **Mistral 7B**. Autorater results are Gemini-based → **flag: the headline 93 % autorater is a frontier model.** FLAMe (24B) is the "cheap" alternative at F1 0.892. |
| Blockers | No fine-tuning, no logprobs for the autorater itself. Their P(True) variant needs sampling; P(Correct) is verbalised (1 call). Needs an **extra model call**. |
| Gain on abstention | Autorater F1 0.935 / acc 0.930 on 115 human-labelled instances. Selective generation: **+2–10 %** correct-answers-among-responses; risk-coverage curves in Fig. 4, >10 % at high-accuracy region for Gemma 27B on HotpotQA. |
| Cost | +1 call/question (autorater). Their P(True) config is 20 samples + 5 eval calls = 25 calls/q — **do not copy that**. |
| ≥2 datasets? | Yes — HotpotQA, Musique, FreshQA, PopQA, NQ, EntityQuestions. **English only.** |

Two findings that matter more than the headline:
- **`TRUE-NLI` (fine-tuned T5-11B entailment) scores precision 0.938 / recall 0.726** for "sufficient".
  A high-precision "evidence exists" detector is *exactly* the FP-killer shape you need.
- **Fine-tuning for abstention backfired.** For Mistral 7B it "led to a higher abstention rate at the
  cost of fewer correct answers". Direct evidence against fine-tuning your way out of over-abstention.

### 2.3 Two Axes of LLM Abstention — why confidence-thresholding *causes* over-abstention

| field | value |
|---|---|
| Method + link | Factorized abstention, dual-risk certification — https://arxiv.org/abs/2607.08456 |
| Venue + year | **arXiv preprint, Jul 2026 — no venue, single author, unrefereed.** |
| Model sizes | Gemma 2 2B, Qwen2.5-3B, **Qwen2.5-7B, Llama-3.1-8B**, Qwen2.5-14B. Squarely your class. |
| Blockers | Best answerability signal is a **hidden-state probe → blocked on OpenRouter**. But the paper states the policy "is agnostic to its source" and runs with elicited P(IK) too. |
| Gain on abstention | **Output answer-confidence → answerability AUROC 0.54–0.67, no scale trend** (Llama-3.1-8B: 0.67). Hidden-state probe: **0.97–0.99**. P(True) post-hoc self-eval on natural false premises: **0.54–0.58**. Factorized two-threshold policy certifies both risk budgets at 8B with correct-answer coverage **0.75 vs 0.31** for confidence-only. |
| Cost | 1 pass (single-pass protocol) + a trained linear readout. |
| ≥2 datasets? | Yes — SelfAware + CREPE (+ matched factual gates). **English only.** |

The load-bearing sentence for your problem: *a calibrated threshold on answer-confidence "cannot reject
U, because W and U overlap … **to hold R_U it must over-abstain**"*. That is a mechanistic explanation
of POMA's 53 FPs. If your orchestration derives Null from agent disagreement/uncertainty, it is
thresholding the **correctness** axis and paying for it in precision on the **answerability** axis.

**Skeptical flags:** certification splits are tiny (n_C = 8–17 items); SelfAware answerability is 87 %
recoverable from bag-of-words alone (surface confound, author admits it). Trust the *direction* and the
Table-1 AUROCs (150+150 items, 5 models); do not quote the coverage numbers as precise.

### 2.4 Semantic entropy — verified, but wrong axis for this problem

| field | value |
|---|---|
| Method + link | https://www.nature.com/articles/s41586-024-07421-0 (read via PMC11186750) |
| Venue + year | **Nature 630, 625–630, 2024.** Claim verified. *Distinct* from Kuhn et al. ICLR 2023 — do not merge their numbers. |
| Model sizes | LLaMA-2-Chat 7B/13B/70B, Falcon 7B/40B, **Mistral 7B**, GPT-4 (paragraphs only). Genuinely tested at 7B. |
| Blockers | Standard estimator **needs token logprobs**. **`discrete semantic entropy` approximates cluster probability from generation counts, disregarding token probabilities, and performs "similar empirically"** → **this is your logprob-free fallback and it is viable on Qwen3-8B.** Needs an entailment model for clustering (GPT-3.5, or **DeBERTa-Large-MNLI** locally). |
| Gain on abstention | AUROC **0.790** averaged over 30 task-model combos, vs naive entropy 0.691, **P(True) 0.698**, embedding regression 0.687. |
| Cost | **10 generations/question** + O(k²) local NLI. ≈$3.00/run on Qwen3-8B → **over budget**; $1.11 on Llama-3.1-8B. |
| ≥2 datasets? | Yes, many (TriviaQA, SQuAD, BioASQ, NQ, SVAMP). **English only.** |

**Why it is ranked below the evidence-grounded methods despite the best pedigree here:** it detects
*confabulations* — wrong answers — which is the **correctness axis**. Per §2.3 that axis reads 0.54–0.67
AUROC on **answerability**. It would tell you the model is unsure, and POMA already over-abstains when
unsure. Expect it to *lower* Null precision. Worth running as a **diagnostic** (is the 53-FP set
high-entropy or low-entropy?), not as the abstention gate.

### 2.5 P(True) / P(IK) — Kadavath et al.

| field | value |
|---|---|
| Method + link | Language Models (Mostly) Know What They Know — https://arxiv.org/abs/2207.05221 |
| Venue + year | arXiv, Nov 2022, Anthropic. Widely cited; **no conference venue.** |
| Model sizes | 800M → 52B. **Crucially: AUROC curves start near 0.5–0.6 at ~1e9 params and improve with scale**; at 8B you are on the weak part of the curve. |
| Blockers | **P(True) needs logprobs** of the `(A)`/`(B)` tokens → **blocked on Qwen3-8B**. **P(IK) needs fine-tuning** (a value head). Calibration requires few-shot; zero-shot P(True) is "poorly calibrated". |
| Gain on abstention | Separates correct/incorrect samples; conditional accuracy at P(True)>0.5 clearly above base rate at 52B. Independently measured elsewhere at **AUROC 0.698 (Farquhar)** and **0.54–0.58 on answerability (§2.3)**. |
| Cost | 5 sampled "brainstormed" answers + 1 eval call ≈ 6 calls/q ≈ $1.80/run. |
| ≥2 datasets? | Yes (TriviaQA, Lambada, GSM8k, arithmetic, HumanEval). **English only.** |

Verbalised-confidence substitute: GRAB-RAG (§2.7) measures **AURC ≈ 0.43–0.45** for small models'
self-reported confidence, and ECE **0.60–0.95** on should-abstain conditions. Self-reported confidence
from a sub-10B model is a near-useless ranking signal. Do not build the gate on it.

### 2.6 Conformal abstention — the principled way to pick the operating point

| field | value |
|---|---|
| Method + link | Mitigating LLM Hallucinations via Conformal Abstention — https://arxiv.org/abs/2405.01563 |
| Venue + year | arXiv, May 2024, Google DeepMind. **No conference venue found.** |
| Model sizes | **Gemini Pro only — flag: no small-model evidence.** |
| Blockers | **`match count` (m.c.) needs NO logprobs** — it counts how many of k samples the LLM judges similar. `expected match count` (e.m.c.) *does* need logprobs ("not a black-box solution"). No fine-tuning. |
| Gain on abstention | Bounds hallucination risk at a target α with distribution-free guarantee while minimising abstention. Beats log-probability scoring clearly on long answers; **comparable on short answers (TriviaQA)** — your answers are short table values, so this advantage largely evaporates. |
| Cost | k=11 generations (1 greedy + 10 at T=0.9) + similarity prompting. Greedy variant cuts comparisons by k. ~$3/run on Qwen3-8B. |
| ≥2 datasets? | Two (Temporal Sequences, TriviaQA). **English only.** |

The transferable part is not the score, it is **conformal risk control**: fix a tolerated error rate α,
calibrate the threshold on a holdout, get a guarantee. Works with **calibration sets as small as
100–300** — your 991-question dev split is ample.

### 2.7 GRAB-RAG — the cautionary result, on exactly your backbones

| field | value |
|---|---|
| Method + link | Prompt-Based Abstention Fails Under Misleading Context — https://arxiv.org/abs/2608.22228 |
| Venue + year | **arXiv preprint, Aug 2026 — no venue, unrefereed, single author.** |
| Model sizes | **Phi-4-mini 3.8B, Llama-3.1-8B, Qwen2.5-7B**, Q4_K_M quantised. Your exact class. |
| Blockers | None — inference-only, five prompt/verifier policies. Uses **DeBERTa-v3-large NLI** locally. |
| Gain on abstention | Defines **FAC (False Abstention Cost)** = abstention rate on questions the model provably can answer — the metric you need. **Adding a generator-side conflict-check verifier (P3) cut wrong answers to 13.3 % but drove macro FAC@Q100 to 49.8 %.** An NLI verifier (P4) recovered 18.8 pp of that utility. |
| Cost | 2 passes + local NLI. |
| ≥2 datasets? | Two (NQ, HotpotQA). **English only.** |

**Read this before adding any verifier agent.** It is a quantified demonstration that a naive verifier
can halve your answerable coverage — the precise regression your ablations must catch. Its other
finding cuts the opposite way and is *reassuring* for you: when evidence is simply **missing**, these
models abstain reliably (≤1 % wrong-answer rate under abstention prompting). Open-ViTabQA Nulls are
likely the missing-evidence kind, which suggests POMA's 24 % miss rate is an **orchestration artefact,
not a model-capability limit** — consistent with few-shot beating POMA.

### 2.8 RSAT — cell-level citation with NLI faithfulness, at 1–8B

| field | value |
|---|---|
| Method + link | RSAT: Structured Attribution Makes Small Language Models Faithful Table Reasoners — https://arxiv.org/abs/2605.00199 |
| Venue + year | **arXiv preprint, May 2026 — no venue, unrefereed, 2 authors.** |
| Model sizes | **Qwen2.5 1.5B/3B/7B, Llama-3 1B/3B/8B.** Exactly your class. |
| Blockers | **Requires fine-tuning (LoRA SFT + GRPO), 18.4 GPU-hours** — different cost class, as you flagged. No logprobs. Uses **DeBERTa-v3-base NLI** (free, local, 184M). |
| Gain on abstention | **None — it does not address unanswerability at all.** Faithfulness 0.224→0.826; citation validity 0.992. |
| Cost | 1 inference pass (citations emitted inline). Training is the cost. |
| ≥2 datasets? | Three (WTQ, FeTaQA, TabFact). **English only.** |

Two mechanisms transfer even if you never fine-tune:
1. **JSON output with `cited_cells: [[row, col]]` coordinates** → coordinates are checkable against the
   grid **programmatically, with zero LLM calls**.
2. **NLI entailment between concatenated cited-cell values and the claim text**, scored by a small local
   DeBERTa NLI model.

And one hard warning: **post-hoc attribution collapses on sub-8B models — 12.7 % average format success,
0.4 % for Qwen-3B, and it gets *worse* with scale within a family (Llama-8B: 4.0 %).** Failure mode is
empty/non-JSON output 76–100 % of the time. **Do not design a "now cite your evidence" second agent.**
Citations must be emitted during the answer pass.

### 2.9 Slobodkin et al. — answerability is linearly decodable pre-generation

| field | value |
|---|---|
| Method + link | The Curious Case of Hallucinatory (Un)answerability — https://arxiv.org/abs/2310.11877 |
| Venue + year | arXiv v2, Nov 2023. (Believed EMNLP 2023 — **not verified from the PDF text**; header says arXiv only.) |
| Model sizes | Flan-T5-XXL 11B, Flan-UL2 20B, OPT-IML 30B. **All >10B — flag.** |
| Blockers | Probe needs **hidden states of the first generated token → blocked on OpenRouter**. Beam relaxation needs beam-search access. |
| Gain on abstention | Linear logistic probe on last-layer first-token embedding: **unanswerability F1 75.5–90.4**, vs 15–48 for the non-contextual first layer. **Transfers across datasets** (SQuAD↔NQ↔MuSiQue) well above baseline. |
| Cost | 1 pass + a logistic regression trained on **800 examples**. |
| ≥2 datasets? | Three (SQuAD2.0, NQ, MuSiQue). **English only.** |

Also quantifies the prompt-hint tradeoff precisely: adding an unanswerability hint raises unanswerable-F1
by up to 80 points but costs **−8.3 F1 / −7.1 EM on answerable questions**. If POMA's prompts lean harder
on the hint than few-shot's do, that alone could explain the 53 FPs. **Cheap first experiment: diff the
abstention instruction strength between POMA and few-shot prompts.**

### 2.10 Others, briefly

- **Know Your Limits: A Survey of Abstention in LLMs** — https://arxiv.org/abs/2407.18418, **v3 Feb 2025,
  UW + AI2. Title and existence verified** (your brief flagged it as uncertain — it is real). *TACL
  acceptance not verifiable from the PDF header; cite as arXiv.* Useful framing: abstention factorises
  into `a(x)` query answerability, `c(x,y)` model confidence, `h(x,y)` human values. Your problem is
  purely `a(x)` + `c(x,y)`, and the survey's own taxonomy shows these are addressed by *different*
  method families — corroborating §2.3 independently.
- **TCR-Bench / Semantic-Answerability Gap** — https://arxiv.org/abs/2607.17742 (arXiv preprint Jul 2026,
  no venue). Defines answerability as distinct from semantic relevance in Table RAG; answerability-aware
  reranking lifts top-1 from 18.2 % → 57.4 %. **Weaker fit: it is a *retrieval*-stage problem (which table
  to fetch). Your table is given.** The transferable claim is that an explicit query-table answerability
  judgment beats an implicit representation — which supports §2.2.
- **Not read:** TraceBack (2602.13059, multi-agent table attribution) and FActScore-style decomposition.
  Decomposition looks a poor fit — Open-ViTabQA answers are short spans, not multi-claim paragraphs.

---

## 3. Picking the operating point (your question 6)

**The "4.8x" cost ratio is not in your data.** It is a frequency ratio (§0). You must *choose* the cost
ratio as a thesis decision and state it. Once chosen, for a calibrated score `p(Null|x)`:

> abstain iff `p(Null|x) > c_FA / (c_FA + c_H)`

If you genuinely assert false abstention costs 4.8x a hallucination, the threshold is **0.83** — abstain
only when ≥83 % sure. That is a deliberately high bar and it is what kills the 53 FPs.

Note the objective conflict: **the threshold maximising Null-F1 is not the threshold minimising expected
cost**, because Null-F1 ignores the 946 answerable items entirely. A threshold sweep will show Null-F1
peaking at a *lower* threshold than the cost-optimal one. Report both, and always alongside Answerable-F1.

Three protocol requirements:
1. **Tune on the 991-question dev split, freeze, evaluate once on the 992 test split.** With only ~46
   test Nulls, a threshold tuned on test is worthless — one item moves F1 by ~1 point.
2. **Report the risk-coverage curve and AURC**, not a single operating point. AURC is threshold-free and
   is what makes signals comparable; it is the metric GRAB-RAG uses for exactly these model sizes.
3. **Use conformal risk control (§2.6)** to make it a guarantee rather than a hope: fix tolerated
   hallucination rate α, calibrate on dev, get a distribution-free bound. Works at n=100–300.

**Also report abstention as pure binary classification** — precision, recall, AUROC/AUPRC for the Null
class — separately from EM/char-F1, as your brief anticipated. With 4.6 % positive prevalence, **AUPRC is
the honest headline; AUROC will look flattering.** Bootstrap CIs over the 46 positives are mandatory:
at n=46, ±1 item ≈ ±2 points of recall.

---

## 4. Ranked top-3

### #0 — Run these two first. They cost nothing and may settle the question.

**P1 — Diff the abstention instruction strength between POMA and few-shot prompts.** Zero dollars, zero
API calls, one afternoon. Slobodkin et al. (§2.9) quantify the tradeoff: an unanswerability hint buys up
to +80 unanswerable-F1 but costs **−8.3 F1 / −7.1 EM on answerable questions**. If POMA's *five role
prompts each independently* carry a "say Null if unsure" instruction while the few-shot baseline carries
it once, the hint is being applied ~5x more forcefully — and that alone is a live candidate explanation
for the **entire** 53-FP gap. It also directly supports the claim you already want to make (§2.7): that
the deficit is an **orchestration artefact**, not a model-capability limit. Check this before spending
anything, because if it is the cause, the fix is deleting text.

**P2 — Recover the few-shot baseline's Null confusion matrix** from existing prediction files (§0). Its
F1 of 56.64 could come from better precision or better recall; that single fact tells you whether
orchestration *adds FPs* or *loses TPs*, and it determines which of #1–#3 is even the right target.

**Gating experiment G1 — measured before the #1/#2 order is committed.** See #1 below.

### #1 — Inline cell-citation + programmatic grid verification (the FP-killer)

> **This ranking is conditional.** RSAT's own Table 2 shows **zero-shot `Fmt%` of 0.398–0.566 for
> Qwen 1.5B/3B/7B** given the RSAT system prompt — i.e. un-tuned instruction models emit well-formed
> `cited_cells` roughly half the time; SFT was required to reach ~99 %. At ~50 % compliance the override
> can only fire on half your questions and is structurally unable to rescue most of the 53 FPs.
> **Gating experiment G1: run citation emission on ~100 dev questions and measure format compliance.
> Pre-declared bar: ≥85 % well-formed `cited_cells` with in-bounds coordinates. Below that, #2 becomes
> #1 and this drops to #2.** Qwen3-8B is a generation newer than RSAT's Qwen2.5 models and has stronger
> structured-output behaviour, so the proxy may well understate — which is exactly why this is worth
> 100 questions rather than an argument.

**Agent/module.** The Answerer is required to emit, in one pass, JSON: `{answer, cited_cells:[[r,c],...]}`
(RSAT §2.8 format). A **Grounding Verifier** — *deterministic code, not an LLM* — then checks: (a) do the
coordinates exist in the grid; (b) does the cited cell's literal value appear in / support the answer
string. Decision rule, Retro-Reader style (§2.1): if the citation **verifies**, emit the answer **even if
an upstream agent voted Null** — a positive-evidence override. If no verifiable citation exists, fall
through to the existing abstention path. Optionally add a continuous score: multilingual NLI entailment
(`mDeBERTa-v3-base-xnli`, local, free) between the cited-cell values and the answer claim, giving a
tunable threshold instead of a binary gate.

**Why #1.** It is the only candidate that attacks precision directly by *confirming support* rather than
measuring doubt. It needs **zero extra LLM calls**. It is the one method whose failure mode is
*symmetric*: a verified citation raises both Null-F1 and Answerable-F1. And it is verifiable in Vietnamese
without a Vietnamese verifier model, because coordinate checking is language-independent.

**Ablation (992 test):**
- `B0` POMA as-is → baseline matrix (35/53/11/893).
- `A1a` + citation emission only (no gate) — **control for prompt-format change alone.** Must be run;
  otherwise gains are confounded with output-format effects.
- `A1b` + programmatic override (binary).
- `A1c` + NLI-scored override, threshold swept on dev, frozen.

Report per arm: **Null TP/FP/FN/TN, Null precision, Null recall, Unanswerable-F1, Answerable-F1, overall
EM, citation-validity rate**, plus bootstrap CIs. Success = FP falls from 53 with FN rising by ≤3.
**Regression tripwire:** Answerable-F1 < 96.49 or FN > 15 → the override is firing on hallucinated
citations; inspect before proceeding.

**Cost.** ~$0.30/run (1 pass, unchanged) + local NLI ≈ free.

**Risk.** Entirely concentrated in format compliance, which is what **G1** measures against the ≥85 %
bar declared above. The secondary risk is that a model emits a *syntactically valid but semantically
wrong* citation and the override then rescues a hallucination — which is why the FN tripwire (>15)
matters as much as the FP target.

### #2 — Sufficient-context agent + factorized two-threshold decision

**Agent/module.** A **Sufficiency Rater** agent that sees only `(question, table)` — **never the proposed
answer** — and emits a binary/scored sufficiency judgment (Joren et al. prompt, §2.2). This is the `a(x)`
axis. Combine with the existing answer-confidence signal `s_C` using either Retro-Reader's linear fusion
or the factorized rule from §2.3: **emit iff `s_A ≥ τ_A` AND `s_C ≥ τ_C`**, both thresholds tuned on dev.

**Why #2.** Best venue backing of anything actionable here (ICLR 2025). It is architecturally the
cleanest realisation of "separate classifier, not a prompt instruction", and the factorized form lets you
report the two error rates separately — which is what your thesis's weakest axis actually needs.
Judging sufficiency *without* the answer is what makes it a genuinely independent signal rather than a
second opinion on the same evidence.

**Ablation (992 test):** `B0` → `A2a` sufficiency label alone as the Null decision → `A2b` factorized
(τ_A, τ_C) → `A2c` learned logistic fusion of both signals. Sweep τ on the 991-dev split; report the full
**risk-coverage curve + AURC** for each, plus the same 2×2 matrix and both F1s per arm. Also report
**Sufficiency-Rater agreement with gold Null labels** as a standalone binary classifier (P/R/AUPRC) —
that number alone tells you whether this can work before you wire it into the pipeline.

**Cost.** +1 call/question = **+$0.30/run** (total ~$0.60). Comfortably inside budget.

**Risk:** the 93 % autorater was **Gemini 1.5 Pro**. At 8B, expect materially worse — §2.3 shows elicited
answerability signals at 8B land around 0.67–0.88 AUROC depending on model and benchmark. Budget for
this being a mediocre-but-usable signal, which is exactly why it is *fused* rather than used alone.

### #3 — Dedicated local multilingual answerability classifier

**Agent/module.** A standalone **encoder** classifier over `(question, serialised table)` →
P(Null), using `mDeBERTa-v3-base-xnli` or XLM-R, run locally. This is Retro-Reader's External Front
Verifier (§2.1) rebuilt as a separate model, and it sidesteps every OpenRouter blocker: it needs **no
generator logprobs and no generator hidden states** because it *is its own model*. Its scalar output
feeds the same threshold/fusion machinery as #2.

**Why #3 and not higher.** It is the only option that gives a genuinely *calibrated continuous* score at
zero marginal inference cost, and Vietnamese is covered natively (XLM-R/mDeBERTa are multilingual — the
only method here with that property; **every paper surveyed above is English-only**). But it needs
training data, and you have ~99 Null examples in the dev split — thin. Mitigate by starting from an
NLI-pretrained checkpoint and using the entailment head zero-shot, then calibrating rather than
fine-tuning.

**Ablation (992 test):** `A3a` zero-shot NLI entailment score as Null signal (no training at all) →
`A3b` calibrated (temperature/isotonic on dev) → `A3c` fine-tuned on dev Nulls with 5-fold CV. Report
2×2 + both F1s + AUPRC per arm. **Explicitly compare A3a vs A3c** to show whether fine-tuning is worth
the cost class — Joren et al. found fine-tuning for abstention *hurt* a 7B model, so this is a real
question, not a formality.

**Cost.** **$0 inference** (local). Training: minutes on one GPU for a 184M–278M encoder — note this is
**two orders of magnitude cheaper than the 18.4 GPU-hours RSAT needed**, so "fine-tuning is a different
cost class" applies much more weakly here than to the 8B LLM.

---

## 5. What I would not do

- **Do not add a verifier agent that votes to abstain.** GRAB-RAG (§2.7) drove false abstention to ~50 %
  that way; ViPanelTR's ≥3/5-unsupported gate is the same shape, and its Unanswerable-F1 caps at 42.11.
  Your binding constraint is precision. Adding abstention votes makes it worse.
- **Do not build the gate on verbalised self-confidence.** AURC 0.43–0.45, ECE 0.60–0.95 at your model
  sizes (§2.7).
- **Do not use semantic entropy as the gate** — right paper, wrong axis (§2.4). Run it as a diagnostic
  on the 53-FP set.
- **Do not add a post-hoc "cite your evidence" pass** — 12.7 % format success on sub-8B models (§2.8).
- **Do not fine-tune the 8B backbone for abstention** before trying #1–#3; the one direct experiment on a
  7B model made over-abstention *worse* (§2.2).

## 6. Honest limitations of this shortlist

- **Six of the twelve sources are 2026 arXiv preprints with no venue, low vote/view counts, and in three
  cases a single author** (§2.3, §2.7, §2.8, §2.10). They are the closest prior art and the only work at
  your exact model scale — which is also your novelty argument — but they are unrefereed. The top-3 is
  anchored on **AAAI 2021, ICLR 2025, and Nature 2024** for mechanism, with the preprints supplying
  small-model evidence and cautionary results.
- **Every method surveyed was evaluated in English only.** Transfer to Vietnamese is assumed, not shown,
  for all of them. #3 is the only one whose backbone is natively multilingual. This is a genuine
  contribution gap you can claim.
- **No paper found addresses unanswerability in Table QA with a given table.** TCR-Bench is retrieval;
  RSAT is faithfulness without abstention. The intersection you are working in appears genuinely open —
  which is good for the thesis and bad for borrowing baselines.
- Venue for Slobodkin et al. and TACL status for the abstention survey are **unverified**; cite as arXiv.
