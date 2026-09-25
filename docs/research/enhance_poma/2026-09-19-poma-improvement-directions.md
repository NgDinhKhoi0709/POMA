# POMA improvement directions: a joint evidence audit

Date: 2026-09-19. Scope: POMA and RankA records available in the two local repositories.

## 1. Executive summary

1. **Internally measured** ([P-TRACE] §Q9): on the older 992-item API test artifact, one-answer POMA is 67.74 EM and few-shot is 67.34; the paired 95% interval for the +0.40-point difference is [−2.12, 3.02].
2. **Internally measured** ([P-Q2], [P-GAP] summary): a later 992-item Qwen artifact gives POMA-first 66.6331, GSA 68.3468, and few-shot 67.3387; these are separate runs and do not validate the older 80.24 headline.
3. **Internally measured** ([P-TRACE] §Q2–Q4): 880/992 older POMA questions route to one specialist, leaving the proposed poma2 specialist-disagreement gate almost idle. Reject that architecture.
4. **Internally measured** ([R-SYN] §3–4): RankA's strongest positive local result is retrieved examples plus a narrow arithmetic executor: +4.63 N1 EM points [1.6, 7.7] against direct reading on 691 dev questions, with important selection and cost caveats.
5. **Inference/hypothesis** ([P-TRACE] §Q5, [R-SYN] §4): the three most worthwhile directions are (i) fair evaluation plus a deployable one-answer formatter, (ii) narrow execution combined with unseen-table retrieval, and (iii) a gated heterogeneous-solver pilot.
6. **Internally measured** ([R-MAG], [R-RESULT] §3–4): same-backbone role councils and general compiler-first answering have failed in RankA; neither deserves another unchanged full run.
7. **Inference/hypothesis** ([P-V3] §4–5, [R-KB2] §1): multi-agent can contribute only when separate channels produce complementary *correct* answers or independently verifiable evidence and a deployable selector retains them at matched compute.
8. **Internally measured** ([R-SPLIT]): all released dev and test tables appear in train. Train-based methods require unseen-table controls; test must not choose a new architecture.

## 2. Scope, evidence rules, and current state

### 2.1 Evidence notation and non-comparability

- **Internally measured** means computed from repository data, predictions, or logs; split, scorer, sample size, and run are attached to every numerical claim below.
- **Full-text literature** means the cited local research report says it checked the paper's method and result text. It is external mechanism evidence, never a POMA effect estimate.
- **Abstract/secondary only** means an abstract, summary, snippet, leaderboard, or second-hand report; do not make it load-bearing for a journal claim without checking the primary item.
- **Inference/hypothesis** marks a proposed transfer, mechanism, priority, or planning estimate with no isolating POMA experiment.
- **Preregistered** marks an arm or KEEP/DROP rule fixed before that result; the measured result is still labeled separately.
- **Exploratory/post-hoc** marks analyses or design choices made after seeing data, especially when inspecting test outputs.
- Source keys at the end link to a file and section. A row may cite several files; its evidence label applies to the numerical result, while expected POMA gain remains a hypothesis unless directly measured.

The POMA trace family is Qwen3-8B via API, 992 test questions, current POMA repository `evaluation.exact_match` scorer, with only 592 per-specialist traces in the old `hp` run ([P-TRACE] introduction, §Q1). **Internally measured.**

The newer Qwen revision family is also API Qwen3-8B on 992 test questions but uses a later raw POMA run and a distinct finalizer comparison ([P-Q2] Scope; [P-GAP] summary). **Internally measured.** It must not be pooled with the older trace family merely because the model and question count match.

The RankA family is local Qwen3-8B Q4_K_M via `llama.cpp`, primarily dev, one final string, using `scripts/e2e_metrics.py` N1 EM, which equates Vietnamese Yes/No synonyms ([R-KB4] Scoring and Baseline registry). **Internally measured.** Its 56.1 full-dev direct EM and POMA's 67.34 test few-shot EM differ in split, prompting, runtime, and scorer; their difference is not a treatment effect.

RankA's `N0` retains Yes/No surface distinctions, while `N1` equates `Có/Đúng/Phải` and `Không/Sai` ([R-KB4] Scoring). **Internally measured.** POMA's evaluator instead uses its own text and list normalization; a valid joint table needs re-scored predictions under one stated scorer, not copied headline EMs ([P-TRACE] Caveats; [P-GAP] §1). **Inference/hypothesis.**

### 2.2 The paper's blocking numerical and attribution problems

**Internally measured** ([P-TRACE] §Q1): Table 6's “without AN” 68.41 equals 405/592 traced questions, whereas “with AN” 80.24 equals 796/992; under the current scorer the same 592 questions give 68.24 to 79.56. The asserted 177 wrong-to-right flips do not reproduce: 67 appear in those 592 traces, and 177 also equals 796−619, the paper's POMA-minus-zero-shot correct-count gap.

**Internally measured** ([P-TRACE] §Q1): the old `hp` specialist logs cover positions 400–991 only; 400 questions lack per-specialist outputs. Code on disk also differs from the generation code in its list variants and contains mojibake boolean variants. A trace-based causal explanation of the 992-item run therefore has a real missing-data boundary.

**Internally measured** ([P-TRACE] §Q1, §Q11): evaluator drift changes archived few-shot EM from 67.14 to 67.34, zero-shot from 62.40 to 63.10, and Fig. 2's reported POMA/FS `Null` F1 from 51.13/56.64 to 52.24/59.20 under the current artifacts. Current-evaluator predicted hints also score 80.24 versus 80.34 for gold hints under best-of-K, reversing the manuscript's narrow “predicted better” claim.

**Internally measured** ([P-TRACE] §Q5, §Q9): the old POMA best-of-K score of 80.24 falls to 67.74 when the first candidate alone is submitted, a 12.50-point gap; 117/124 best-of-K-only wins come from a variant of one specialist's answer. AN is largely an answer-surface and scoring mechanism, not proof that specialist reasoning improves.

**Internally measured** ([P-Q2] Results; [P-GAP] summary): in the later Qwen run, best-of-K is 74.8992, first-candidate 66.6331, GSA one-answer 68.3468, and few-shot 67.3387. GSA improves over first by 1.7137 points; it exceeds few-shot by 1.0081 points before equalizing its extra LLM call or finalization on few-shot. That is suggestive, not a controlled multi-agent advantage.

**Internally measured** ([P-GAP] §2–4): GSA reads raw specialist candidates and bypasses AN; 92 of its 315 EM failures already have a matching gold form somewhere in POMA's candidate pool. The boolean `Có`/`Đúng`/`Phải` expansion is broken by mojibake in current code, and some AN rules match particular test-question text. Rule provenance and a train-only formatter must be established before reporting a generalizable gain.

**Internally measured** ([P-TRACE] §Q2–Q4): 880/992 questions have one routed specialist, 112 have two, and none has three in the old predicted-hint run. Only 8/64 traced two-specialist cases disagree after canonicalization. A perfect resolver recovers three old-run first-answer errors (+0.30 points), with an upper bound of seven (+0.71) after accounting for untraced cases; the old poma2 gate cannot support a large gain.

**Internally measured** ([P-TRACE] §Q7–Q8): 77.9% of specialist confidences equal 1.0; non-Null confidence correctness AUROC is 0.588. Cell-grounding AUROC is about 0.52 and 88.5% of wrong answerable outputs still cite real cells. Confidence-weighted voting or a simple “cited cell exists” verifier is poorly supported.

**Internally measured** ([P-TRACE] §Q10): on old-test, multi-label Why questions have POMA-first 40.74 versus FS 55.56 (n=27); MathematicalReasoning 64.62 versus 67.69 (n=195); List 66.07 versus 50.00 (n=56). These are diagnostic subgroup contrasts, not evidence that adding a particular agent caused them.

**Internally measured** ([R-SPLIT]; read-only check of both repositories' `qas_test.json` by `qa_id` and `answer`): the files have the same 992 IDs and gold answers, including 45 literal `Null`s, although their byte hashes differ. The older POMA trace's 46-gold-`Null` claim remains unexplained and should not be used as a released-dataset fact.

**Internally measured** ([R-SPLIT]): all 329 tables have train questions; all 296 dev and 289 test tables occur in train, and 24/991 dev questions duplicate train-question text. This affects POMA's fixed few-shot examples, train-derived formatter rules, retrieval, learned selectors, and any future tuning. Report released seen-table results and filtered unseen-table results separately.

**Inference/hypothesis** ([P-REVIEW] Part D; [P-JOURNAL] “A contradiction”): the resubmission must disclose and differentiate the same group's ViPanelTR paper and resolve whether the active journal submission is the JIT draft or the README-described KAIS review. Venue and concurrent-submission status are author decisions, not scientific outcomes.

### 2.3 What a fair POMA result would mean

**Inference/hypothesis** ([P-FIX] Tier 1; [R-KB4] Comparison design): freeze dataset, scorer, provider, model settings, prompts, finalizer, answerability rule, and allowed training data before comparison. Score exactly one final answer per system and attach candidate-max only as an oracle diagnostic.

**Inference/hypothesis** ([P-V3] §5; [R-KB4] Comparison design): report paired wins/losses, paired intervals and latency/tokens; cluster uncertainty by table where practical because multiple questions share a table. Match both model-call and realized-token budgets with a strong few-shot/self-consistency control.

**Inference/hypothesis** ([R-KB1] §2; [R-SPLIT]): any train-derived rule or retrieval should exclude same `table_id` and article title in its unseen-table arm; use train for design and dev for selection, then freeze once for test. A POMA test-analysis finding may rule out a design but may not set new thresholds for that same test.

## 3. Directions overview

“Expected gain” is a POMA forecast only when marked **Inference/hypothesis**; RankA's observed deltas belong to its local N1 dev setup. “Cost” refers to extra calls, engineering, and validity risk, not a promise of a dollar amount.

| ID / direction | Group | Mechanism | Existing evidence | Multi-agent relevance | Cost and risk | Expected POMA gain | Status |
|---|---|---|---|---|---|---|---|
| D01 Fair scorer and full provenance | answer normalization and evaluation | One answer, same scorer/AN, complete traces and run hashes | **Internally measured:** old test 67.74 vs 67.34; Table 6 mixed 592/992; later test first 66.6331 ([P-TRACE] §Q1/Q9; [P-GAP] summary) | Not relevant | Low compute; high credibility impact | **Inference/hypothesis:** no intrinsic accuracy gain | has result; repair unrun |
| D02 Deployable formatter / GSA | answer normalization and evaluation | Train-derived canonical choice or grounded one-answer selector | **Internally measured:** later GSA 68.3468 vs first 66.6331, test n=992; old 71.27 yes/no estimate is exploratory ([P-GAP] summary; [P-TRACE] §Q5) | Supporting | Low–medium; leakage and extra-call risk | **Inference/hypothesis:** plausible, unknown after fair control | has result; controlled variant unrun |
| D03 Retrieved demonstrations (A5) | training-free memory or retrieval | Retrieve four train QA/table examples excluding same table/article | **Internally measured:** RankA unseen dev n=691 +2.46 N1 [−0.3,+5.4], inconclusive ([R-SYN] §3) | Not relevant | Moderate context/latency; leakage | **Inference/hypothesis:** unknown API POMA transfer | has result; standalone inconclusive |
| D04 Narrow arithmetic executor (R2) | program-aided | Override only count/sum/avg/argmax/argmin | **Internally measured:** RankA later dev n=691 +3.04 N1 [+1.3,+4.8] ([R-SYN] §4) | Supporting | Planner failures, merged numeric parsing | **Inference/hypothesis:** likely targeted, unknown POMA EM | has result; KEEP component |
| D05 Retrieval plus narrow execution (S) | training-free memory or retrieval | A5 reader plus R2 when action class is suitable | **Internally measured:** RankA dev n=691 61.4 vs 56.7 N1, +4.63 [+1.6,+7.7] ([R-SYN] §4) | Supporting | Around 7–8× direct latency in RankA; selection history | **Inference/hypothesis:** highest measured transfer candidate, no POMA estimate | has result; KEEP on dev |
| D06 POMA v3 mixed solvers | architecture | Text specialist, bounded code, alternate-view generalist; one final answer | **Inference/hypothesis:** design only; old cross-method vote +2.12 is test exploratory ([P-V3] §4–5; [P-TRACE] §Q9) | Core | High calls and adjudicator error | **Inference/hypothesis:** unknown until same-budget dev ablation | unrun |
| D07 Cross-method selector / cascade | architecture | Escalate on canonical text/code/view disagreement, use execution evidence | **Internally measured, exploratory/post-hoc:** old test gate vote 69.86 vs 67.74; RankA D/K/T vote loses to T ([P-TRACE] §Q9; [R-KB3] §6) | Core | Selector overfit and false corrections | **Inference/hypothesis:** unknown; could be negative | has diagnostic result; selector unrun |
| D08 Earned `Null` decision | abstention-Null | Verify missing relation/attribute; re-answer proposed `Null`; permit `Null` for all types | **Internally measured:** RankA full dev 25 false abstentions/10 missed `Null`; POMA old test 53/11 under its rule ([R-RESULT] §6; [P-TRACE] §Q6) | Supporting | Rare class, false-abstention trade-off | **Inference/hypothesis:** modest aggregate, unknown | unrun |
| D09 Alternative table view / locator | table representation | Lossless header/stub view or short manifest, validate coordinates | **Internally measured:** RankA dedup +0.19 on merged dev n=518; structural two-view pilot unrun ([R-MAG] experiment 1; [R-KB7] active candidates) | Supporting | Extra serialization and possible answer degradation | **Inference/hypothesis:** limited unless complementary on dev | unrun; simple dedup rejected |
| D10 Long-table row/column retrieval | table representation | CPU retrieval with source indices and full-table fallback | **Full-text literature** and **Inference/hypothesis:** POMA representation note proposes it; dataset median table ≈647 tokens ([P-REPR] §1; [P-MA] §0) | Not relevant | Evidence loss; little reach on short tables | **Inference/hypothesis:** mainly tail latency, EM unknown | unrun |
| D11 Second backbone / heterogeneous models | backbone | Replicate with independently trained small model, then measure error complementarity | **Internally measured:** POMA only Qwen full fair artifact; RankA mostly one local quantization ([P-Q2]; [R-KB7] gaps) | Supporting | Provider/serving and prompt parity | **Inference/hypothesis:** robustness first, ensemble gain unknown | partly run; matched study unrun |
| D12 Compute-matched sampling / voting | other | Few-shot self-consistency at matched tokens; canonical answer clusters | **Internally measured:** RankA n=100 unweighted D/K/T vote 59 vs T 63; old POMA five-way vote 67.64 vs first 67.74 ([R-KB3] §1; [P-TRACE] §Q9) | Supporting | More calls and correlated errors | **Inference/hypothesis:** necessary control, not assumed gain | controls unrun; naive votes negative |
| D13 General compiler-first answerer | program-aided | Planner AST answer replaces reader broadly | **Internally measured, preregistered:** RankA full dev n=991 B −2.93, R +0.50 [−1.7,+2.7] N1 ([R-RESULT] §1) | Not relevant | High planner error | **Inference/hypothesis:** no reason to repeat unchanged | rejected |
| D14 Same-backbone role council | architecture | Locator→Reader→Skeptic→Arbiter or personas | **Internally measured, exploratory/post-hoc:** RankA dev n=300 final Δ0.00 N1; Locator empty 220/300 ([R-MAG] experiment 2) | Core | Extra calls and propagated errors | **Inference/hypothesis:** no supported gain unchanged | rejected design |
| D15 poma2 specialist-disagreement gate | architecture | Resolve only simultaneous routed-role disagreements | **Internally measured:** old POMA test 880/992 one specialist; resolver +0.30 observed / ≤+0.71 bound ([P-TRACE] §Q2–Q4) | Core | Near-zero trigger; extra complexity | **Inference/hypothesis:** negligible ceiling on old design | rejected |
| D16 Empty/hedge-based `Null` | abstention-Null | Treat empty executor or mixed candidate set as missing evidence | **Internally measured:** RankA full dev only 3/117 empties gold `Null`, B_null −8.88 N1; POMA hedge sees 8/64 answerability errors ([R-RESULT] §1/§6; [P-TRACE] §Q6) | Not relevant | Severe false abstention | **Inference/hypothesis:** negative unchanged | rejected |
| D17 Merged-value dedup / span-frame as main fix | table representation | Remove replicated spans or alter executor frame | **Internally measured, preregistered for span G0:** dedup +0.19 on n=518; span replay net −2 merged/0 normal ([R-MAG] experiment 1; [R-G0] Result) | Not relevant | Little direct reach | **Inference/hypothesis:** no main-effect claim | rejected premise |
| D18 Confidence weights / cell-existence critic | architecture | Weight self-confidence or veto absent citations | **Internally measured:** POMA old test confidence AUROC 0.588 non-Null; grounding AUROC 0.517 ([P-TRACE] §Q7–Q8) | Supporting | Unreliable selector | **Inference/hypothesis:** likely hurts unchanged | rejected |
| D19 Fine-tuning / teacher distillation | other | SFT or adapters trained on train answers/traces | **Full-text literature:** small-model trained table systems exist; **Internally measured:** no POMA/RankA QLoRA trial ([R-KB2] Fine-tuning; [R-KB7] gaps) | Not relevant | New protocol, GPU and leakage | **Inference/hypothesis:** unknown | unrun; outside current training-free scope |

### Priority and attainable headroom

The table ranks work by decision value for a Q2 revision, not by the largest number in a different study. A measured effect in RankA is a reason to test transfer, not a promised POMA gain. **Inference/hypothesis** ([R-KB4] Comparison design; [P-V3] §5).

| Priority | Directions | What is actually attainable from current evidence | Decision |
|---|---|---|---|
| Required first | D01 | **Internally measured:** old POMA test first-vs-best-of-K gap is 12.50 points on n=992, while newer run first-vs-all gap is 8.2661 points on n=992; these are separate artifacts ([P-TRACE] §Q5; [P-GAP] summary). | Resolve claims and scorer before choosing a method. **Inference/hypothesis.** |
| High, low engineering | D02 | **Internally measured:** later GSA gains 1.7137 points over later first on n=992; this is selection/finalization, not a controlled multi-agent increment ([P-GAP] summary). | Test same finalization on FS and dev with train-only rules. **Inference/hypothesis (proposed protocol).** |
| High, targeted | D04 | **Internally measured:** RankA R2 gains +3.04 N1 on later dev n=691, with favorable conditional arithmetic precision ([R-SYN] §4; [R-RESULT] §4). | Replicate narrow operations in the POMA API setting. **Inference/hypothesis (proposed protocol).** |
| High, system candidate | D05 | **Internally measured:** RankA S gains +4.63 N1 [1.6,7.7] on later dev n=691; latency is roughly 7–8× direct ([R-SYN] §4). | Audit artifacts and test four-arm factorial before paper claim. **Inference/hypothesis (proposed protocol).** |
| Medium, uncertain standalone | D03 | **Internally measured:** RankA standalone A5 +2.46 N1 [−0.3,+5.4] on later unseen-table dev n=691 ([R-SYN] §3). | Keep as S component; do not claim independent confirmation. **Inference/hypothesis.** |
| Medium, error-specific | D08 | **Internally measured:** old POMA test has 53 false abstentions and 11 missed `Null`s under its rule; RankA full dev has 25 and 10 ([P-TRACE] §Q6; [R-RESULT] §6). | Small `Null` pilot; assess net EM, not the entire headline gap. **Inference/hypothesis (proposed protocol).** |
| Conditional research bet | D06, D07 | **Internally measured:** old-test specialist disagreement can rescue only 3 first-answer errors observed; cross-method differences create more candidate opportunities, but the +2.12 gated-vote result is exploratory on test ([P-TRACE] §Q4/Q9). | Pilot candidate complementarity on dev before building a judge. **Inference/hypothesis (proposed protocol).** |
| Conditional diagnostics | D09, D10 | **Internally measured:** RankA dedup gives +0.19 on n=518 merged dev and most test tables are short in POMA's inspection ([R-MAG] experiment 1; [P-MA] §0). | Run probe/long-tail gates; avoid global format replacement. **Inference/hypothesis (proposed protocol).** |
| Required controls | D11, D12 | **Internally measured:** neither a second completed fair POMA backbone comparison nor a positive local naive-vote result establishes a gain ([P-Q2]; [R-KB3] §1). | Measure robustness and equal-compute alternatives. **Inference/hypothesis (proposed protocol).** |
| Closed unchanged | D13–D18 | **Internally measured:** each tested premise has a negative or near-zero result in its stated setup ([R-RESULT] §1; [R-MAG] experiments 1–2; [R-G0]; [P-TRACE] §Q2–Q8). | Reopen only with a new mechanism and isolating control. **Inference/hypothesis.** |

This ranking deliberately separates **negative** results (D13–D18 in their tested forms), an **inconclusive** result (standalone D03 on n=691), and **unrun** mechanisms (D06 adjudication, D08 burden-of-proof, D09 two-view locator, and D19 training) ([R-KB5] E02–E16; [P-V3] §5). **Internally measured** for the recorded statuses; **Inference/hypothesis** for future value.

An **underpowered** example is RankA's T-versus-D thinking pilot: T 63% versus D 58% on n=100, but the paired interval for the +5-point difference is [−4,+14] and T took 11.2 seconds per question ([R-SYN] §5; [R-KB5] E08). **Internally measured.** It is neither evidence that thinking helps nor a negative result; it needs a larger, matched-budget check only if thinking is a serious control. **Inference/hypothesis.**

The old POMA +2.52-point comparison after giving both POMA-first and few-shot deterministic variants is still a best-of-K comparison, albeit more symmetric, and has a paired interval [0.10,4.94] on n=992 ([P-TRACE] §Q9). **Internally measured.** It supports studying a common formatter, not claiming that a deployable single-answer multi-agent system is +2.52 points better. **Inference/hypothesis.**

The newer Qwen GSA result is more deployable because it emits one string, but its two invalid outputs and additional LLM call must be charged to its method; applying a comparable finalizer to few-shot remains necessary ([P-Q2] GSA; [P-GAP] §2). **Internally measured** for outputs and calls; **Inference/hypothesis** for the control requirement.

## 4. Per-direction analysis

### D01. Fair scorer and provenance

- **Hypothesis — Inference/hypothesis:** the paper becomes reviewable when every comparison uses one final answer, one scorer, and a reproducible artifact manifest ([P-FIX] Tier 1; [R-KB4] Comparison design).
- **For — Internally measured:** old best-of-K 80.24 versus first 67.74 on the same 992 old-test questions; Table 6 mixes 592 and 992; current evaluator changes archived baseline scores ([P-TRACE] §Q1/Q5).
- **Against — Inference/hypothesis:** this does not itself improve answer quality; the newer Qwen run already shows a distinct 74.8992 best-of-K score, so a repair may lower a headline ([P-Q2] Results).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** freeze scorer and source commit, rerun/re-score complete dev artifacts, log all specialist outputs, and evaluate first, GSA, and equal finalizers against identical few-shot outputs; do not select from test ([P-FIX] Tier 1; [R-KB4]).

### D02. Deployable formatter or GSA

- **Hypothesis — Inference/hypothesis:** train-only answer-form rules or a one-answer grounded finalizer recover surface-form errors without gold-aware best-of-K selection ([P-GAP] §2/§6).
- **For — Internally measured:** later Qwen test GSA 68.3468 versus first 66.6331, both on n=992 under that run's evaluator; 92/315 GSA EM failures have a matching form in the POMA candidate pool ([P-GAP] summary/§2).
- **Against — Internally measured:** GSA adds a model call and has two invalid outputs in the later run; AN's boolean variants are mojibake and several rules are question-literal, so the current gain is not a clean general-format result ([P-Q2] GSA; [P-GAP] §3–4).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** derive generic formatter rules on train, compare FS+same formatter, POMA-first+same formatter, GSA from raw, and GSA after canonicalization on dev; ablate literal rules; report valid-output rate and realized calls ([P-GAP] §6; [P-FIX] Tier 1).

### D03. Retrieved demonstrations

- **Hypothesis — Inference/hypothesis:** related train examples teach answer conventions and content patterns beyond fixed few-shot examples ([R-SYN] §3).
- **For — Internally measured:** unseen-table screening on 300 RankA dev questions showed A5 +6.0 N1 versus direct, while random four-shot gave +0.3; both used the same local Qwen backbone and scorer ([R-SYN] §3).
- **Against — Internally measured:** on a later 691-question dev confirmation set, unseen-table A5 was +2.46 [−0.3,+5.4], below its +3 preregistered confirmation threshold; seen-table +12.0 on screening is leakage-prone ([R-SYN] §3; [R-SPLIT]).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** compare fixed shots, four random matched shots, question-neighbor A5, and answer-form-only examples at equal token budget on an unseen-table dev slice; then test interaction with POMA's existing few-shot prompt ([R-KB4] Required slices; [R-KB7] priorities).

### D04. Narrow arithmetic executor

- **Hypothesis — Inference/hypothesis:** deterministic count, sum, average, and extrema repair derived-answer errors when planner precision is adequate ([R-RESULT] §4).
- **For — Internally measured:** RankA full-dev executor count/sum/avg accuracy was 53% versus 27% direct on 89 `status=ok` items; argmax/argmin was 62% versus 31% on 26; R2 gained +3.04 [1.3,4.8] on later n=691 dev ([R-RESULT] §4; [R-SYN] §4).
- **Against — Internally measured:** filter/project and compare favored direct reading, 55% versus 64% and 53% versus 68% on the selected full-dev executor-success cases; program agents on merged tables may be brittle ([R-RESULT] §4; [P-PROG] warning).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** preserve direct as default; log planner operation and execution status, validate Vietnamese number parsing, then compare R2 to direct and to an equal-call prompted calculation arm by operation and table type on dev ([R-KB4] Required slices).

### D05. Retrieval plus narrow execution

- **Hypothesis — Inference/hypothesis:** retrieved examples and deterministic arithmetic fix partly distinct errors, so their combination may outperform either alone ([R-SYN] §4).
- **For — Internally measured:** RankA n=691 local dev A0 56.7, A5 59.2, R2 59.8, and S 61.4 N1; S−A0 +4.63 [1.6,7.7], S−A5 +2.17 [0.4,3.9] ([R-SYN] §4).
- **Against — Internally measured:** R2 was chosen after an initial 300-question screen; 175 later questions had been inspected in aggregate before one combined-system rule was locked, and S was roughly 7–8× direct latency; no POMA API replication exists ([R-KB3] §5; [R-SYN] §7).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** audit exact S artifacts, replay a frozen dev subset, then run the four-arm factorial A0/A5/R2/S with shared scorer and unseen-table retrieval in POMA's API setting; count interaction, cost, and false `Null` changes ([R-KB7] priority 1; [R-KB4]).

### D06. POMA v3 mixed solvers

- **Hypothesis — Inference/hypothesis:** text, executable program, and genuinely alternate table view make different *correct* answers available; an execution-grounded resolver can use them ([P-V3] §4).
- **For — Internally measured, exploratory/post-hoc:** old POMA and few-shot disagree on 217/992 old-test questions; the fixed gate plus five-way vote gave 69.86 versus POMA-first 67.74, indicating cross-method opportunity in that artifact ([P-TRACE] §Q9).
- **Against — Internally measured:** RankA's broad local compiler arm lost −2.93 on n=991 dev and its same-backbone role council gained 0.00 on n=300; v3 itself has no output ([R-RESULT] §1; [R-MAG] experiment 2).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** on dev, run S, P, and G separately under fixed total tokens; inspect co-failure, unique correct answers, invalid programs, and oracle-of-three before building an adjudicator; stop if P or G supplies no material unique correct answers ([P-V3] §5; [R-KB7] Multi-agent decision).

### D07. Cross-method selector and cascade

- **Hypothesis — Inference/hypothesis:** canonical disagreement can trigger a cheap, precise executable check only where it can change the answer ([P-V3] §4; [R-KB2] Selection).
- **For — Internally measured, exploratory/post-hoc:** old-test POMA-first≠FS gate fires 217/992 and the predetermined vote reached 69.86; RankA D/K/T oracle-of-three is 75% on n=100, showing candidate headroom but no deployable selector ([P-TRACE] §Q9; [R-KB3] §6).
- **Against — Internally measured:** on RankA's same 100 items, majority 59% lost to T-always 63%; POMA's five-way unconditional vote was 67.64, below its 67.74 first answer ([R-KB3] §1; [P-TRACE] §Q9).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** compare strong-channel-always, fixed rule, order-swapped LLM judge, code-grounded adjudicator, and equal-cost self-consistency on the same dev predictions; report correct→wrong and wrong→correct flips plus escalation cost ([R-KB7] priority 5; [P-V3] §5).

### D08. Earned `Null` decision

- **Hypothesis — Inference/hypothesis:** a distinct answerability check can correct false abstention while preserving true `Null` when it tests the requested attribute or relation, not merely whether an entity is present ([R-KB1] §7; [P-V3] §4).
- **For — Internally measured:** POMA old-test has 53 false abstentions and 11 missed `Null`s under its candidate-set rule; RankA full-dev direct has 25 and 10; both show a concrete error target under different scorers and splits ([P-TRACE] §Q6; [R-RESULT] §6).
- **Against — Internally measured:** RankA's unconstrained Skeptic said information was insufficient on 130/300 items, and `empty_selection→Null` lost 8.88 N1 points on full dev; simple entity-string coverage AUROC is roughly 0.44–0.55 ([R-MAG] experiment 2; [R-RESULT] §1; [R-KB1] §7).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** on dev compare baseline, question-word prior, hard veto, and evidence-based re-answer/absence check; permit `Null` outside any question-word gate, and count rescued false abstentions minus broken true `Null`s ([R-KB7] priority 2 and protocol conflict).

### D09. Alternative view and structural locator

- **Hypothesis — Inference/hypothesis:** a lossless header/stub view or short structural manifest can improve cell localization while the original fluent view remains the answer source ([P-STRUCT] §3; [R-KB2] Representing merged cells).
- **For — Full-text literature:** the POMA structure report says AIT-QA isolates a transposition gain in its own model/task and TABVERSE finds larger format effects on structure probes than end QA at 7B scale; these are transfer hypotheses, not Open-ViTabQA gains ([P-STRUCT] §2–3).
- **Against — Internally measured:** RankA's merged-value dedup changed 50.0 to 50.2 N1 on n=518; its Phase 1 diagnosis found little support for header/span geometry as the dominant error, and span-frame G0 failed ([R-MAG] experiment 1; [R-KB1] §5; [R-G0]).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** first score structure probes and same-question oracle-of-two for flat versus alternate view; require unique correct answers and coordinate validity before adding a locator agent; compare a one-agent alternate-view control ([R-KB7] priority 4; [P-STRUCT] §3).

### D10. Long-table retrieval

- **Hypothesis — Inference/hypothesis:** row/column retrieval with provenance and a full-table fallback reduces tail latency or context failure without losing needed evidence ([P-REPR] §1).
- **For — Full-text literature:** the POMA report checks TAP4LLM, TableRAG, and PieTa as source methods for index-based table selection, but their datasets and often trained components differ ([P-REPR] §§1–2).
- **Against — Internally measured:** test-table median is about 647 tokens and p90 about 2,097 in a POMA dataset inspection; most questions do not face a context-window bottleneck ([P-MA] §0).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** restrict evaluation to the long-table tail; compare full Flatten V1 with fixed-budget lexical selection plus fallback; measure evidence recall, tokens, failures, and EM, not EM alone ([P-REPR] recommendations).

### D11. Second backbone and heterogeneous models

- **Hypothesis — Inference/hypothesis:** an independent small backbone tests robustness and may supply complementary correct answers; model diversity itself is not a free performance claim ([P-BACK] Part C; [R-KB2] Multi-agent).
- **For — Abstract/secondary only:** the POMA backbone shortlist uses a Vietnamese leaderboard to identify possible model parity and independence; it is not a Table QA result ([P-BACK] Part B).
- **Against — Internally measured:** RankA's current positive results use one local quantized Qwen, while POMA's newer fair artifact has a full Qwen result but no comparable completed Gemma matrix in the cited report; model/provider/thinking changes can confound a two-backbone contrast ([R-KB7] gaps; [P-Q2]; [P-BACK] Part C).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** run the same frozen prompts, table bytes, answer formatter, scorer, and thinking setting on both backbones and the same dev items; report complementarity before any ensemble and then confirm each arm separately ([P-BACK] Part C).

### D12. Compute-matched sampling and voting

- **Hypothesis — Inference/hypothesis:** any multi-agent gain should survive comparison with a single model given the same realized token and call budget ([P-REVIEW] W3; [P-V3] §5).
- **For — Full-text literature:** the POMA multi-agent evidence review reports compute-matched studies where simple voting or self-consistency often beats debate on 7–8B models; this supports a strong control, not a predicted POMA score ([P-8B] Tier 1).
- **Against — Internally measured:** two local votes already disappoint: RankA D/K/T majority 59 versus T 63 on n=100, and old POMA unconditional five-way vote 67.64 versus 67.74 on n=992 test ([R-KB3] §1; [P-TRACE] §Q9).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** dev sweep a small fixed set of sample counts, cluster equivalent answers with the same train-only formatter, and plot EM against realized tokens and latency; compare the selected count once on frozen test ([R-KB4] Comparison design; [P-MA] §5).

### D13. General compiler-first answerer

- **Hypothesis — Inference/hypothesis:** a planner plus executor might turn reasoning into reliable symbolic execution; the tested broad replacement did not ([R-KB3] §3).
- **For — Internally measured:** on full RankA dev executor-success arithmetic cases, count/sum/avg and extrema outperform direct reading conditionally ([R-RESULT] §4).
- **Against — Internally measured, preregistered:** broad B is −2.93 N1 and route R +0.50 [−1.7,+2.7] on n=991 full dev, with lookup/compare losses ([R-RESULT] §1/§4; [R-PROTO]).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** do not repeat B unchanged; only reopen after a new planner demonstrates held-out filter/compare precision above direct on its target slice, then compare to D04 ([R-KB7] closed directions).

### D14. Same-backbone role council

- **Hypothesis — Inference/hypothesis:** role prompts could divide evidence finding, answering, skepticism, and arbitration; the tested roles did not supply distinct evidence ([R-MAG] experiment 2).
- **For — Inference/hypothesis:** the architecture is easy to describe and parallelize, but no internal controlled result shows it beating a compute-matched single reader ([P-REVIEW] F4; [R-KB7] multi-agent decision).
- **Against — Internally measured, exploratory/post-hoc:** RankA final council Δ0.00 N1 on 300 dev questions; Locator returned empty cells on 220/300 and Skeptic over-abstained on 130/300 ([R-MAG] experiment 2).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** only reopen with a genuinely new evidence source and an ablation removing that source; compare to a same-call reprompt and strong single-channel reader ([R-KB7] closed directions).

### D15. poma2 specialist-disagreement gate

- **Hypothesis — Inference/hypothesis:** resolving disagreements could improve a multi-specialist answer; the existing router seldom creates them ([P-V3] §0–2).
- **For — Internally measured:** 8/64 traced multi-specialist cases disagree after canonicalization, and four have at least one correct specialist answer ([P-TRACE] §Q3–Q4).
- **Against — Internally measured:** 880/992 have one specialist, 182/196 old best-of-K errors are invisible to this gate under the report's categories, and the observed first-answer rescue is only three questions ([P-TRACE] §Q2–Q4).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** none for poma2 unchanged; any new gate must first demonstrate a dev trigger rate and unique-correct-answer pool large enough to matter, with its own selector precision ([P-V3] §5).

### D16. Empty or hedge as `Null`

- **Hypothesis — Inference/hypothesis:** absence of a program result or a mixed candidate set might indicate unanswerability; current evidence rejects both as certificates ([R-RESULT] §6; [P-TRACE] §Q6).
- **For — Inference/hypothesis:** an empty result may be informative only if the query itself is validated and the requested relation is checked independently; this specific protocol has not been run ([R-KB7] closed directions).
- **Against — Internally measured:** only 3/117 RankA full-dev empty selections have gold `Null`, B_null −8.88 N1; POMA's hedge trigger sees only 8/64 answerability errors and 0/11 missed `Null`s in its old test run ([R-RESULT] §1/§6; [P-TRACE] §Q6).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** reopen only with a separate relation-absence certificate and paired false-abstention accounting; an empty selection alone must never force `Null` ([R-KB7] closed directions).

### D17. Deduplication or span-frame as main merged fix

- **Hypothesis — Inference/hypothesis:** removing duplicated merged values or adjusting span projection could correct merged-table errors; the tested mechanisms had little reach ([R-G0] Method).
- **For — Internally measured:** the dedup transformation reduced prompt characters by about 45% on the tested merged tables, so it may still matter for latency under a different cost objective ([R-MAG] experiment 1).
- **Against — Internally measured:** merged dev n=518 EM changed only +0.19 [−1.2,+1.4]; a preregistered replay of 941 logged ASTs gave net −2 merged and zero normal for the span-frame change ([R-MAG] experiment 1; [R-G0] Result).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** do not repeat the old premise; a new representation needs a probe showing missing information or changed planner behavior before an end-to-end council ([R-KB7] closed directions).

### D18. Confidence weights or cell-existence critic

- **Hypothesis — Inference/hypothesis:** confidence and citation grounding could rank specialists; the current fields lack discrimination ([P-TRACE] §Q7–Q8).
- **For — Internally measured:** high-confidence outputs are sometimes more accurate, but the old trace's apparent confidence AUROC 0.663 includes `Null` effects; that is not a calibrated answer selector ([P-TRACE] §Q7).
- **Against — Internally measured:** 511/656 traced confidences equal 1.0; non-Null AUROC 0.588; evidence fraction AUROC 0.517, and all four traced hallucinations cite fully grounded cells ([P-TRACE] §Q7–Q8).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** only reopen with a new signal evaluated on dev for conditional correction, calibration, and false-correction rate; do not put existing scores into weighted consolidation ([P-V3] §2).

### D19. Training and teacher distillation

- **Hypothesis — Inference/hypothesis:** a trained model may learn table operations and answer form better than prompting, but this changes the training-free POMA scope ([R-KB2] Fine-tuning).
- **For — Full-text literature:** RankA's survey records strong trained 7–8B table systems on other benchmarks, with model- and task-dependent transfer ([R-KB6] §D).
- **Against — Internally measured:** no local POMA/RankA QLoRA outcome or unseen-table trained-model validation exists in the supplied evidence; all released dev/test tables already appear in train ([R-KB7] scientific gaps; [R-SPLIT]).
- **Minimal experiment — Inference/hypothesis (proposed protocol):** if scope changes, compare SFT on gold answers before teacher traces or role-specific adapters, split by article/table for validation, and include the same no-training baseline and budget ([R-KB2] Fine-tuning; [R-KB4]).

## 5. What multi-agent actually contributes

### 5.1 Same-backbone, same-token effect by question or table type

**No data** establish a positive POMA multi-agent-minus-single-agent effect at the same backbone, same realized token budget, same finalizer, and same question set. The old +0.40 first-answer test difference is not compute matched, and its paired interval crosses zero ([P-TRACE] §Q9). **Internally measured.**

**No data** isolate a same-budget multi-agent gain by merged-header, merged-value, normal, Why, arithmetic, list, or `Null` slice. The old POMA-versus-FS type table is a different-prompt comparison with overlapping labels; it cannot identify the value of parallel agents ([P-TRACE] §Q10). **Inference/hypothesis.**

**Internally measured** ([P-TRACE] §Q10, old API test n=992, current POMA evaluator): List n=56 is 66.07 POMA-first versus 50.00 FS, a +16.07-point diagnostic contrast; Why n=27 is 40.74 versus 55.56, −14.82; MathematicalReasoning n=195 is 64.62 versus 67.69, −3.07. These slices are small or multi-label, and no equal-token single-agent control was run.

**Internally measured** ([R-MAG] experiment 2, local N1 dev n=300): the role council's overall gain is 0.00; on merged n=162 it is +0.62 with interval [−1.2,+3.1], and on normal n=138 it is −0.72 [−4.3,+2.9]. These results do not transfer numerically to API POMA, but they directly caution against attributing a merged-table gain to role labels.

### 5.2 Separate the four proposed sources of gain

| Source | Evidence and verdict | Required isolating control |
|---|---|
| Diversity of solving method | **Internally measured, exploratory/post-hoc:** old POMA-first and FS differ on 217/992, and a gated vote adds +2.12 old-test points; **Internally measured:** RankA narrow execution adds +3.04 N1 on later dev n=691. This shows possible complementarity, not that v3 works ([P-TRACE] §Q9; [R-SYN] §4). | Same S/P/G candidates, then ablate P and G separately at matched tokens. |
| Specialization by question-type role | **Internally measured:** old router has one specialist on 880/992; old specialist disagreement resolver gains only three first-answer questions; RankA role council Δ0.00 on dev n=300 ([P-TRACE] §Q2–Q4; [R-MAG] experiment 2). | Remove S from v3 and compare to a generalist using the same table view and budget. |
| Cross-verification | **Internally measured:** current POMA confidence/evidence scores lack discrimination; RankA's unconstrained Skeptic over-abstains ([P-TRACE] §Q7–Q8; [R-MAG] experiment 2). **Inference/hypothesis:** execution feedback may differ. | LLM-only judge versus executed check versus no judge, counting both rescue and damage. |
| Plain voting / ensembling | **Internally measured:** unconditional old POMA five-way vote 67.64 is below POMA-first 67.74; RankA D/K/T majority 59 is below T-always 63 on n=100 ([P-TRACE] §Q9; [R-KB3] §1). | Equal-budget sampled few-shot self-consistency and canonical vote with tuned K on dev. |

**Full-text literature** ([P-8B] Tier 1; [P-PROG] opening): external 7–8B studies support testing voting against debate and text/program diversity, but they do not identify which Open-ViTabQA questions v3 will fix. Some cited systems train schedulers, use larger models, or operate on English clean tables. Exact external percentages should be rechecked in their papers before journal submission.

### 5.3 When multiple agents lose at 8B

**Internally measured** ([P-TRACE] §Q2–Q4): 88.71% of old POMA test questions invoke one specialist; a disagreement-only branch cannot rescue the single-specialist errors. Parallel execution itself changes latency, not deterministic answers, unless a later aggregation policy uses distinct outputs ([P-REVIEW] F4). **Inference/hypothesis** for latency until measured.

**Internally measured** ([P-TRACE] §Q9): POMA-first and FS are both wrong on 240/992 old-test questions, 2.30 times the overlap expected under independent error events. The independence calculation is diagnostic; it does not prove cause. The all-five oracle is 79.64, but a five-way vote scores only 67.64.

**Internally measured** ([R-MAG] experiment 2): RankA's local Locator provided `cells: []` in 220/300 and the Skeptic returned insufficient-information on 130/300; the final council only matched direct EM. This is error propagation through empty evidence and excessive vetoing, not a successful division of labor.

**Internally measured** ([R-KB3] §6; [R-KB2] Selection): on the local 100-question D/K/T slice, D=58, K=56, T=63, majority=59, oracle=75. The 75 is headroom conditional on gold knowledge; it is not a selector. Thinking took 11.2 seconds per question versus about 1.1 seconds for direct reading in that pilot.

**Internally measured** ([R-RESULT] §1/§4): a broad program branch loses even when it executes because wrong filtering and comparison can outnumber arithmetic rescues. More agent outputs are harmful if aggregation trusts them without operation-specific validation.

### 5.4 Make poma3 a falsifiable multi-agent study

**Inference/hypothesis** ([P-V3] §4–5; [R-KB7] multi-agent decision): define three independent blind candidate producers on the same dev questions: S, the current routed text specialist; P, bounded executable arithmetic/program reasoning; G, a direct reader on a predeclared alternate view. Each must return a single candidate, evidence identifier, status, tokens, and latency. Do not interpret an invalid program or empty selection as `Null` ([R-RESULT] §6). **Internally measured** for that warning.

**Inference/hypothesis — proposed protocol** ([P-V3] §5; [R-KB4] Comparison design): before selecting a gate, compute per-channel single-answer EM, pairwise both-wrong counts, distinct correct answers when another channel is wrong, invalid-output rates, and oracle-of-three. An oracle quantifies headroom; the final selector is evaluated separately.

**Inference/hypothesis — proposed protocol** ([P-V3] §5): mandatory solver ablations are full S+P+G, −P, −G, and −S, plus one strong FS reader given the same aggregate token budget. The −S ablation directly tests whether dataset-label specialization matters beyond method diversity.

**Inference/hypothesis — proposed protocol** ([P-V3] §5; [R-KB7] priority 5): mandatory decision ablations are no adjudicator, canonical majority/fixed operation rule, LLM-only judge with candidate order swapped, executed adjudicator, and strong-channel-always. Compare each with FS self-consistency at the same realized token budget and same final formatter.

**Inference/hypothesis — proposed protocol** ([P-V3] §5; [R-KB7] priority 2): separately ablate `Null` checks on any predicted `Null`, hedge-only checks, and no check; separately ablate Why causal-evidence checks. Count false abstentions, missed `Null`s, and net final-answer EM, rather than reporting `Null` F1 alone.

**Inference/hypothesis** ([P-V3] §5; [R-KB4] Required slices): publish per-type and four-way table-type results only after the overall protocol is locked. Report paired table-cluster intervals where possible; small Why/How and gold-`Null` slices need counts and uncertainty, not categorical claims.

### 5.5 Directions that exploit multi-agent versus those that do not need it

| Direction | Why an agent boundary might matter | Single-workflow control and current verdict |
|---|---|---|
| D06 mixed S/P/G solvers | **Inference/hypothesis:** independently generated method-specific candidates can offer complementary correct answers ([P-V3] §4). | A single reader plus narrow executor and retrieved examples already has positive local dev evidence; v3 must beat that at matched tokens ([R-SYN] §4). |
| D07 execution-grounded adjudication | **Inference/hypothesis:** one channel can check another's program or cell path with external execution ([P-V3] §4). | Deterministic action-specific R2 may capture the gain without a judge ([R-SYN] §4). |
| D08 separate answerability checker | **Inference/hypothesis:** separate information access or burden-of-proof may help rare `Null` cases ([R-KB2] Abstention). | A one-reader re-ask or fixed prior is a mandatory control; previous Skeptic over-abstained ([R-MAG] experiment 2). |
| D09 structural locator plus reader | **Inference/hypothesis:** one channel locates, another verbalizes, if coordinate precision is high ([P-STRUCT] §3). | A single reader on the alternate view may suffice; G0 and dedup are negative ([R-G0]; [R-MAG] experiment 1). |
| D02 formatter and D01 evaluation | **Internally measured:** surface forms and scorer policy explain large apparent gains ([P-TRACE] §Q5; [P-GAP] §2). | Deterministic train-only rules and a common finalizer need no multi-agent framing. |
| D03 retrieval and D10 table selection | **Internally measured:** A5 can help a single reader; **Inference/hypothesis:** row retrieval may save context ([R-SYN] §3; [P-REPR] §1). | CPU retrieval plus one solver; no extra agent needed. |
| D04 narrow executor and D05 S | **Internally measured:** operation-specific execution and S help local dev ([R-SYN] §4). | One reader with a tool is sufficient unless a separate solver contributes unique correct answers. |
| D11 backbone replication, D12 sampling, D19 training | **Inference/hypothesis:** robustness, ensembling, and training answer separate research questions ([P-BACK] Part C; [R-KB2] Fine-tuning). | Each can be studied with one final-answer interface; “multi-agent” adds no explanatory value by itself. |

## 6. Recommended roadmap

All schedules below are **Inference/hypothesis** work estimates for one researcher after source and environment access is ready. They are not measured project durations. All portfolios start with D01, select on dev, and reserve test for one frozen evaluation of the selected system ([R-KB4] Test policy; [R-KB7] decision 7). Older POMA test diagnostics must not become the new gate's thresholds.

### Portfolio A — safe Q2 resubmission (estimated 5–8 working days)

1. **Days 1–2, Inference/hypothesis (proposed protocol):** reconcile evaluator version, the two Qwen runs, Table 6 and Fig. 2; retain raw predictions and full traces with hashes; correct the 45-versus-46 `Null` count ([P-TRACE] §Q1; [P-Q2]; [R-SPLIT]).
2. **Days 2–4, Inference/hypothesis (proposed protocol):** on dev, run one-answer FS and POMA with identical train-only formatter and AN policy; include POMA-first, GSA, FS+GSA where applicable, and report paired intervals, candidate K, token/call/latency costs ([P-FIX] Tier 1; [P-GAP] §6).
3. **Days 4–6, Inference/hypothesis (proposed protocol):** add an independently trained small backbone with identical protocol if serving permits; finish hint metrics, per-type errors, answerability matrix, and the ViPanelTR/PanelTR comparison ([P-FIX] Tier 1–2; [P-REVIEW] Part D).
4. **Days 6–8, Inference/hypothesis:** rewrite claims around measured attribution. Preserve `all` only as an oracle diagnostic; if fair POMA minus FS includes zero, present the negative orchestration finding and formatter contribution honestly ([P-V3] §5–6).
5. **Stop/drop:** drop the accuracy claim “parallel specialists improve QA” unless a matched single-answer, equal-finalizer comparison is positive with a paired interval excluding zero; do not promise poma3 in this portfolio ([P-FIX] Tier 1; [P-TRACE] §Q9). **Inference/hypothesis (proposed protocol).**

Mandatory ablations: raw/first/GSA or formatter for each applicable system; AN on the baseline; same scorer; hint-source and answerability breakdown; backbone-by-method interaction; cost versus matched few-shot/self-consistency if the paper retains an efficiency or multi-agent claim ([P-FIX] Tier 1; [P-V3] §5). **Inference/hypothesis (proposed protocol).**

### Portfolio B — balanced method paper (estimated 2–3 weeks)

1. Complete Portfolio A's evaluation repair; keep its fair FS and POMA arms fixed ([P-FIX] Tier 1). **Inference/hypothesis (proposed protocol).**
2. Replicate D03, D04, and D05 on an untouched POMA dev subset with unseen-table retrieval and the same one-answer scorer; log operation-class precision and latency ([R-SYN] §3–4; [R-KB4]). **Inference/hypothesis (proposed protocol).**
3. Pilot D08 as a small independent `Null` experiment with baseline, hard-veto control, and evidence-based re-answer; resolve the contradictory old Phase 3 hard-gate wording before implementation ([R-KB7] priority 2). **Inference/hypothesis (proposed protocol).**
4. Freeze the best dev configuration and compare once on test. Position the contribution as a training-free, operation-aware Vietnamese Table QA pipeline if the gains replicate, without labeling its CPU retrieval and executor as evidence of multi-agent collaboration ([R-KB7] active candidates; [R-SYN] §4). **Inference/hypothesis.**
5. **Stop/drop:** drop standalone A5 if unseen-table confirmation remains inconclusive; drop R2 outside arithmetic/extrema; drop the `Null` checker if rescued false abstentions do not exceed broken correct answers or if final EM falls ([R-SYN] §3–4; [R-KB3] §8). **Inference/hypothesis (proposed protocol).**

Mandatory ablations: A0/A5/R2/S factorial, random and fixed-shot controls, seen/unseen-table retrieval, operation-class overrides, one-answer shared formatter, `Null` confusion matrices, and realized time/tokens ([R-KB4] Required slices; [R-SYN] §4). **Inference/hypothesis (proposed protocol).**

### Portfolio C — ambitious multi-agent test (estimated 4–6 weeks)

1. Complete D01 and use Portfolio B's strongest single-workflow arm as the comparison floor ([P-V3] §5; [R-SYN] §4). **Inference/hypothesis (proposed protocol).**
2. On dev only, collect blind S/P/G outputs and run the diversity gate: per-channel accuracy, unique correct counts, co-failure, oracle, invalid program and coordinate rates. Abort if the new channels add no meaningful unique correct answers or cannot be selected without damage ([P-V3] §5). **Inference/hypothesis (proposed protocol).**
3. If the gate passes, implement canonical comparison, execution-grounded adjudication, and separate answerability; keep every component optional and ablatable ([P-V3] §4–5). **Inference/hypothesis (proposed protocol).**
4. Match total realized tokens with a strong FS+self-consistency arm; use two backbones if feasible, one fixed scorer, train-only formatter, unseen-table controls, and a frozen single test run ([P-V3] §5; [R-KB4]). **Inference/hypothesis (proposed protocol).**
5. **Stop/drop:** reject the multi-agent attribution if full S/P/G fails to beat the strongest equal-budget single-workflow arm with a paired interval excluding zero, if −S/−P/−G barely changes results, or if executed adjudication fails to beat fixed rules and order-swapped LLM judging ([P-V3] §5). **Inference/hypothesis (proposed protocol).**

Mandatory ablations: full/−S/−P/−G, each solver alone, original versus alternate table view for G, no/LLM-only/executed judge, candidate-order swap, fixed versus learned-on-dev selection rule, no/hedge-only/all-`Null` answerability, same formatter across arms, and equal-budget FS sampling ([P-V3] §5; [R-KB7] multi-agent decision). **Inference/hypothesis (proposed protocol).**

**Inference/hypothesis** ([P-JOURNAL] Short answer; [P-V3] §6): journal choice follows the actual result. A diagnostic evaluation paper may suit a language-resource venue; a positive mixed-method result needs explicit differentiation from MoRE, MATA, PanelTR, and the group's ViPanelTR. Confirm the existing KAIS/JIT submission state before any new submission.

## 7. Open items and conflicts to resolve

1. **Internally measured conflict:** older POMA trace best-of-K 80.24 / first 67.74 versus later Qwen revision 74.8992 / 66.6331 on 992 test questions. Different raw runs and finalization contexts are identifiable, but the exact prompt, provider, code-commit, and scoring changes behind the gap are not reconciled in the reports ([P-TRACE] §Q1/Q5; [P-Q2]; [P-GAP] summary).
2. **Internally measured conflict:** old Table 6 compares 405/592 without AN with 796/992 with AN; 177 flips are not reproduced. The 592-subset old-evaluator one-question difference and R1/METEOR drift still need the generating script/version ([P-TRACE] §Q1).
3. **Internally measured conflict:** POMA trace analysis says 46 gold `Null` on old test outputs, while both repositories' released 992 QA records agree by ID and answer on 45; explain the extra trace reference or counting logic before recomputing Fig. 2 ([P-TRACE] §Q6; [R-SPLIT]; [P-MA] §0).
4. **Internally measured conflict:** older POMA review spec says table-disjoint and roughly 10% `Null`; RankA release-file audit finds every evaluation table in train and 45/992 `Null`. The release-file audit has stronger direct provenance ([P-SPEC] §0; [R-SPLIT]).
5. **Internally measured conflict:** `fix-plan-POMA.md` says the full Q2 runbook had not run, but `outputs/q2_revision/` contains a later full Qwen raw/GSA comparison and partial Gemma artifacts. Inventory what completed, failed, and has comparable final reports before scheduling reruns ([P-FIX] Headline; [P-Q2] Artifacts).
6. **Internally measured conflict:** old reviewer arithmetic inferred 12 hallucinations from Fig. 2; later trace analysis found 11 in its output. The released gold-`Null` count conflict means the full answerability matrix must be regenerated under one evaluator ([P-REVIEW] F8; [P-V3] §8; [R-SPLIT]).
7. **Internally measured conflict:** RankA's full-dev result file includes R2 +3.13 on all 991 questions, while the cleanest reported confirmation is +3.04 on later 691. They are different samples, and only the latter is the stated confirmation estimate ([R-RESULT] §1; [R-SYN] §4).
8. **Exploratory/post-hoc:** old POMA 69.86 cross-method gate, yes/no formatter 71.27, and RankA 51.4 oracle on a merged aggregate slice are hypothesis-generating, not deployable or fresh-test results ([P-TRACE] §Q5/Q9; [R-G0] Post-hoc).
9. **Internally measured:** 400/992 old `hp` questions lack specialist traces; 48 untraced two-specialist cases limit exact disagreement accounting. Rerun with complete stage logs and source commit ([P-TRACE] §Q1/Q4/Caveats).
10. **Inference/hypothesis:** no same-backbone, equal-token POMA multi-agent superiority estimate exists overall or by table/question type; no poma3 dev run, no proven adjudicator, and no reliable end-to-end S transfer to POMA API are in the supplied records ([P-V3] §5; [R-KB7] open gaps).
11. **Inference/hypothesis:** no measured small-backbone calibration supports the current confidence/evidence critic, and no independent-backbone matched fair POMA comparison is complete in the cited summary ([P-TRACE] §Q7–Q8; [P-Q2]).
12. **Inference/hypothesis:** several literature cards are summary-level or rely on other tasks/models; reopen the primary full text before copying any exact external percentage into the manuscript ([R-KB6] §D/E; [P-8B] tiers).
13. **Inference/hypothesis:** resolve the Phase 3 `Null` protocol contradiction: its revision says question type is only a prior, while older bullets still impose a hard wh-word permission gate ([R-KB7] priority 2 and conflict 5).
14. **Inference/hypothesis:** confirm current submission venue/status, cite ViPanelTR, distinguish the related systems, and do not submit overlapping manuscripts concurrently ([P-JOURNAL] contradiction; [P-V3] §6; [P-REVIEW] Part D).

## Source register

The POMA source files below are local design and analysis records. The RankA originals remain authoritative for RankA experiments; its knowledge base is an index and conflict guide, not a new model run ([R-KB0] Scope).

[P-TRACE]: Khoi/trace-analysis/gate_headroom_report.md
[P-V3]: Khoi/review-POMA-Boost-v2-architecture.md
[P-REVIEW]: Khoi/review-POMA-JIT.md
[P-FIX]: Khoi/fix-plan-POMA.md
[P-JOURNAL]: Khoi/journal-selection-POMA.md
[P-Q2]: ../../outputs/q2_revision/qwen_baseline_comparison_candidate_max.md
[P-GAP]: 2026-09-18-answer-normalization-gsa-score-gap.md
[P-REPR]: 2026-09-17-table-representation-small-lm.md
[P-MA]: 2026-09-18-multi-agent-small-llm-huong-di.md
[P-SPEC]: 2026-09-18-vietnamese-table-qa-methods-spec.md
[P-PROG]: 2026-09-18-supporting/program-aided-shortlist.md
[P-STRUCT]: 2026-09-18-supporting/structure-encoding-shortlist.md
[P-BACK]: 2026-09-18-supporting/backbone-shortlist.md
[P-8B]: 2026-09-18-supporting/multi-agent-8b-evidence.md
[R-KB0]: ../../../RankA/docs/research/knowledge-base/README.md
[R-KB1]: ../../../RankA/docs/research/knowledge-base/01-dataset-and-problem.md
[R-KB2]: ../../../RankA/docs/research/knowledge-base/02-methods-landscape-and-openvitabqa-directions.md
[R-KB3]: ../../../RankA/docs/research/knowledge-base/03-experiments-results-and-lessons.md
[R-KB4]: ../../../RankA/docs/research/knowledge-base/04-evaluation-and-data-card.md
[R-KB5]: ../../../RankA/docs/research/knowledge-base/05-experiment-ledger.md
[R-KB6]: ../../../RankA/docs/research/knowledge-base/06-evidence-registry-and-claim-audit.md
[R-KB7]: ../../../RankA/docs/research/knowledge-base/07-decision-log-and-open-gaps.md
[R-SPLIT]: ../../../RankA/docs/research/2026-09-19-finding-split-not-table-disjoint.md
[R-RESULT]: ../../../RankA/docs/research/e2e-go-nogo-result-fulldev.md
[R-SYN]: ../../../RankA/docs/research/2026-09-19-new-directions-synthesis.md
[R-MAG]: ../../../RankA/docs/research/2026-09-19-magent-merged-null-first-results.md
[R-G0]: ../../../RankA/docs/research/2026-09-19-direction1-g0-result.md
[R-PROTO]: ../../../RankA/docs/research/e2e-go-nogo-protocol.md
