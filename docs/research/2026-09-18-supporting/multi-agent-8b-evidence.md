# Does multi-agent collaboration help models under ~10B? — Ranked shortlist for Open-ViTabQA

## Bottom line up front

The literature now contains a **direct, compute-matched, open-weight, sub-10B refutation** of the core premise
behind ViPanelTR and POMA. Choi, Zhu & Li (NeurIPS 2025) ran exactly your configuration —
homogeneous agents, same backbone, Qwen2.5-7B-Instruct and Llama3.1-8B-Instruct — and found plain
majority voting equals or beats every debate topology, with a martingale proof that debate cannot
improve expected correctness. Bertalanič & Fortuna (2026) ran N=10 homogeneous 7–8B agents
(Qwen2.5-7B, Llama-3.1-8B, Ministral-3-8B) — which is POMA's architecture — and found debate loses to
isolated self-correction at 2.1–3.4× the tokens.

Your own numbers (0.27–0.56 F1 from review/deliberation; 1.27 EM from all orchestration; 3.5–4× cost)
are **the predicted result**, not an anomaly. They sit inside the published effect range for
homogeneous same-backbone deliberation at 8B.

Three findings you can cite as your own contribution's justification:

1. **Debate at matched compute loses to self-consistency.** Huang et al. (ICLR 2024) Table 7:
   MAD @ 9 responses = 83.0 on GSM8K vs. self-consistency @ 9 responses = 88.2. Not a tie — a 5.2-point loss.
2. **The pessimism is size-graded and gets worse as models get smaller.** Huang et al.'s weakest model,
   Llama-2-70B, degrades from 62.0 → 43.5 → 36.5 on GSM8K under intrinsic self-correction. GPT-4-Turbo
   degrades 91.5 → 88.0 → 90.0. At 8B the degradation should be *worse than 70B*, and the 8B studies confirm it.
3. **Your normalization result is a known confound that the debate literature itself has now flagged.**
   Choi et al. Appendix F, Table 9: with their answer extractor, single-agent GSM8K = 0.8713; with the
   extractor used by Du et al., the *same model* scores 0.6620. They write that extraction method
   "can significantly affect measured performance—sometimes even reversing conclusions." Your
   11.83-of-13.10-EM-from-normalization finding independently replicates this at the Vietnamese Table QA level.
   **This is your strongest publishable claim and it has a citable precedent.**

---

## TIER 1 — Directly load-bearing: sub-10B open-weight, compute-matched or homogeneous-agent

### 1. Debate or Vote: Which Yields Better Decisions in Multi-Agent LLMs? — **the single most important paper for this thesis**

| field | value |
|---|---|
| Paper + link | Choi, Zhu, Li. https://arxiv.org/abs/2508.17536 |
| Venue + year | **NeurIPS 2025** (peer-reviewed) |
| Model sizes tested | **Qwen2.5-7B-Instruct, Llama3.1-8B-Instruct** (main), Qwen2.5-32B-Instruct (scale check). Not GPT-4-only. Your exact backbone class. |
| Compare vs. self-consistency at matched compute? | **Yes — this is the paper's entire design.** Majority Voting is defined as debate with T=0 over the same N=5 agents, so the ensemble is held fixed and only the interaction rounds vary. |
| Finding | Majority voting ≥ debate everywhere. Qwen2.5-7B avg over 7 benchmarks: single 0.7205, best MAD 0.7377, **MV 0.7691**. Llama3.1-8B: single 0.6203, best MAD 0.6990, **MV 0.7242**. Arithmetic on Qwen: MV 0.9900 vs. best MAD 0.8400. Centralized MAD (a judge/aggregator agent) is catastrophic on Llama: 0.6094 → 0.6053 → **0.5670** at T=2/3/5, i.e. *below the single agent*. Scale check at 32B: same conclusion. Heterogeneous personas: "Majority Voting mostly paralleled MAD variants." |
| Theory | Theorem 2: under a Dirichlet-Compound-Multinomial belief model, debate induces a **martingale** over each agent's belief in the correct answer — E[p_{i,t} \| α_{t-1}] = p_{i,t-1}. "debate itself does not systematically improve or degrade an agent's belief on average." Empirically confirmed: mean agent accuracy is flat across rounds 1–5 (their Fig. 4, Table 6). |
| Cost signal | N=5 agents × (1 + T) rounds. T=5 debate = 30 calls vs. MV = 5 calls for worse accuracy. |
| **Why it matters to you** | Their homogeneous-agent, same-backbone setup *is* ViPanelTR/POMA. The martingale result is the mechanism explaining your 0.27–0.56 F1 ablation deltas. Their Appendix F answer-extraction finding is the mechanism explaining your 11.83 EM. |

Quote to use: *"Majority Voting alone accounts for most of the performance gains typically attributed to MAD."*
And: *"we prove formally that majority vote does essentially all the work."*

### 2. The Cost of Consensus: Isolated Self-Correction Prevails Over Unguided Homogeneous Multi-Agent Debate

| field | value |
|---|---|
| Paper + link | Bertalanič & Fortuna, Jožef Stefan Institute. https://arxiv.org/abs/2605.00914 |
| Venue + year | 2026 preprint, ACM conference format. **Provenance caveat: not yet peer-reviewed (3 votes, 57 views on alphaXiv).** Cite as supporting, not load-bearing. |
| Model sizes tested | **Qwen2.5-7B, Llama-3.1-8B, Ministral-3-8B**, N=10 agents, R=3 rounds. Preliminary Qwen2.5-32B replication. Zero frontier models. |
| Compare vs. self-consistency at matched compute? | Partially — compares against **isolated self-correction** (same rounds, no peer exchange), a **stochastic-noise control** (irrelevant rationales injected to control for prompt length), and a **single agent with 10× output budget**. This is a stronger control set than most MAD papers. |
| Finding | Debate loses or ties everywhere in the 7–8B class. Qwen/GSM-Hard: debate 58.8%, self-correct 61.0%, **noise control 63.2%** (!). Ministral/GSM-Hard: debate **20.7%** vs. self-correct 48.3% — a collapse. Three named failure modes, all quantified: **modal sycophancy up to 85.5%** (agents adopt the modal peer answer regardless of validity), **vulnerability rate up to 70.0%** (P(wrong_t \| correct_{t-1})), **oracle gap up to 32.3 pp** (correct answer present in the pool but discarded by plurality voting). Consensus inflates to 90.1% while accuracy falls. Sycophancy onset is fast: already 69.4–77.2% at K=2 peers. Higher temperature *amplifies* conformity. 32B is worse (95.4% sycophancy), not better. |
| Cost signal | **2.1–3.4× tokens vs. self-correction**, up to 28,631 tokens/problem. Single agent at 10× budget: Qwen/MMLU-Hard 66.7% at 619 tokens vs. debate 60.7% at 17,401 tokens. |
| **Why it matters to you** | N=10 homogeneous agents on a shared context = POMA. The noise control is the ablation your thesis is missing: it shows the gain attributed to "deliberation" can be reproduced by injecting *unrelated* rationales, i.e. it is a re-prompting effect, not a collaboration effect. |

### 3. Statistical Scouting Finds Debate-Safe but Not Debate-Useful Cases (matched-ceiling, 8B)

| field | value |
|---|---|
| Paper + link | Hu, Shen, Lakshmipathi (Amazon Web Services). https://arxiv.org/abs/2605.09618 |
| Venue + year | 2026 preprint. **Provenance caveat: 0 votes / 10 views, unreviewed.** Methodologically careful and self-critical; cite for the mechanism, not the headline. |
| Model sizes tested | **Llama 3.1 8B Instruct, Ministral 3 8B Instruct.** Nothing larger. |
| Compare vs. self-consistency at matched compute? | **Yes — matched 960-token generation ceiling** across greedy / vote3 / 2-agent critique-revise debate. They are honest that this controls *opportunity to generate*, not realized tokens: debate actually consumes 518 median output tokens vs. vote3's 26, so the comparison is **biased in debate's favour** and debate still barely wins. |
| Finding | MuSiQue: Llama greedy 39.7 / vote3 40.3 / debate 43.7. Ministral greedy 48.3 / vote3 49.0 / **debate 47.0 (worse)**. GSM8K: Llama debate **60.7 vs. vote3 83.3** — a 22.6-point collapse. Win/loss decomposition on Llama/MuSiQue: debate uniquely correct on 13.7%, **flips a correct answer to wrong on 12.3%** — near-exact cancellation. Ministral: hurts 15.7% vs. helps 7.0%, net negative. No fixed protocol wins across the 2×2 of models × datasets. |
| Key structural result | **Vote entropy predicts where debate is *safe*, not where it is *needed*.** Hurt rate collapses from 14–17% to 2.7% at high entropy, but help rate is flat across strata. **66% of debate-helpful cases occur when voting was unanimous but wrong** — invisible to any disagreement-based router. Oracle per-example routing headroom is +14 pp; the best cheap controller recovers 11–19% of it and its CI crosses zero. |
| 8B-specific negative | A one-shot self-critique probe on Llama-3.1-8B **flipped the answer in 127/127 unanimous cases (100%)**, including all 66 where the original answer was correct — zero mutual information with whether debate helps. The authors explicitly refuse to call this sycophancy vs. prompt-format compliance without a contrastive control. Either reading kills self-critique as a router at 8B. |
| Cost signal | Debate = 7 calls, $0.00319/example; vote3 = 3 calls, $0.00133; greedy = 1 call, $0.00044. At 10K examples/day: debate $31.94 vs. greedy $4.42. |

### 4. Stop Overvaluing Multi-Agent Debate — We Must Rethink Evaluation and Embrace Model Heterogeneity

| field | value |
|---|---|
| Paper + link | Zhang, Cui, Chen et al. (PSU / Shanghai AI Lab). https://arxiv.org/abs/2502.08788 |
| Venue + year | 2025, position paper; widely read (389 votes / 12.5K views). v3 June 2025. |
| Model sizes tested | gpt-4o-mini, claude-3.5-haiku, **Llama3.1-8b-instruct, Llama3.1-70b-instruct**. Open-weight at your exact size included. |
| Compare vs. self-consistency at matched compute? | **Yes.** All MAD methods normalized to ~6 LLM calls; SC scaled by sample count; explicit accuracy-vs-tokens scaling curves (their Fig. 6). |
| Finding | 5 MAD frameworks (SoM, Multi-Persona, EoT, ChatEval, AgentVerse) × 9 benchmarks × 4 models = 36 configs. **No MAD method achieves >20% win rate against plain CoT** by ANOVA at p<0.05. Multi-Persona: 0% win rate. Against SC the gap widens: "In most cases when SC can be applied, SC achieves the highest performance, defeating CoT, not to mention MAD methods." Increasing agents (3→9) or rounds (2→4) does not reverse it. Failure mechanism: aggressive methods (MP, ChatEval, AgentVerse) correct many errors but introduce as many; conservative methods (SoM, EoT) do neither. |
| **The one positive result in the whole shortlist** | **Model heterogeneity is "a universal antidote."** Heter-MAD (randomly sampling GPT-4o-mini or Llama3.1-70b per agent turn, p=0.5) improves SoM by **+6.4%** and EoT by **+8.2%** over the same-model average, and beats CoT-average by up to **+5.8%**. Mechanism (their Fig. 5): the gain comes almost entirely from CW/WC questions — those one model solves and the other does not. Simpler frameworks (SoM, EoT) benefit *more* from heterogeneity than complex ones (ChatEval, AgentVerse). |
| Cost signal | MAD "generally a less efficient method for leveraging token consumption" than SC at equal tokens. |
| **Why it matters to you** | This is the paper that tells you what form multi-agent *should* take at 8B: **not personas on one backbone — different backbones.** You have three (Qwen3-8B, SEA-LION 8B, Llama-3.1-8B) and have so far used them as separate experiments rather than as a heterogeneous ensemble. That is the unexploited axis. |

---

## TIER 2 — Foundational / mechanism papers (larger models, but the mechanism transfers downward)

### 5. Large Language Models Cannot Self-Correct Reasoning Yet — **VERIFIED, and the scope is narrower than commonly cited**

| field | value |
|---|---|
| Paper + link | Huang, Chen, Mishra, Zheng, Yu, Song, Zhou (Google DeepMind / UIUC). https://arxiv.org/abs/2310.01798 |
| Venue + year | **ICLR 2024** |
| Model sizes tested | GPT-3.5-Turbo, GPT-4, GPT-4-Turbo, **Llama-2-70b-chat**. **Smallest model is 70B — there is no sub-10B evidence in this paper.** Flag this: "8B cannot self-correct" is an *extrapolation downward*, not a result. |
| Compare vs. self-consistency at matched compute? | **Yes, Section 4, and this is the citation you want.** Table 7 (GSM8K, gpt-3.5-turbo-0301, full test set, 3 agents): standard 76.7 @ 1 response; SC 82.5 @ 3; **MAD round 1 = 83.2 @ 6 responses vs. SC = 85.3 @ 6**; **MAD round 2 = 83.0 @ 9 vs. SC = 88.2 @ 9.** Debate loses by 2.1 and 5.2 points at matched response count. |
| Exact claim (scope) | The claim is scoped to **intrinsic** self-correction — "based solely on its inherent capabilities, without the crutch of external feedback." The paper explicitly says self-correction *works* with reliable external feedback (code executors, unit tests, search, trained verifiers) and for alignment/style tasks. It does **not** claim self-correction is impossible in general. |
| The oracle-leakage critique (verified) | Their Table 1 names three issues: RCI (Kim et al.) and Reflexion (Shinn et al.) **use oracle labels** — ground truth decides when to stop, so correct→incorrect flips are silently discarded; Du et al.'s MAD is an **unfair comparison to self-consistency**; Self-Refine (Madaan et al.) uses **weak initial prompts**, with wrong target labels in the few-shot examples for the initial response only. With oracle labels GPT-3.5 goes 75.9 → 84.3 on GSM8K; without them it goes 75.9 → 75.1 → 74.7. |
| **Size gradient (the part nobody cites)** | Tables 3–4 and Fig. 1 show degradation is monotone in weakness. GPT-4-Turbo: 91.5 → 88.0 → 90.0 (96.0% of answers unchanged). GPT-3.5: 75.9 → 75.1 → 74.7 (74.7% unchanged). **Llama-2-70B: 62.0 → 43.5 → 36.5 on GSM8K and 64.0 → 37.5 → 36.5 on CommonSenseQA**, with only 40.0% of answers unchanged and 31.0% flipped correct→incorrect. Robust across three different feedback prompts. |
| Cost signal | Self-correction round 1 = 3 calls, round 2 = 5 calls, vs. 1 for standard prompting. |
| Root cause quote | *"The fundamental issue is that LLMs cannot properly judge the correctness of their reasoning."* |

**The extrapolation argument you should make explicitly:** at 70B the correct→incorrect flip rate is 31.0%
and accuracy drops 25.5 points. Your backbones are ~9× smaller. The 8B papers (#2, #3) measure exactly
this and find vulnerability rates of 55–70% and sycophancy of 69–85%. The trend is monotone and it
points the wrong way for 8B self-review.

### 6. When Can LLMs Actually Correct Their Own Mistakes? A Critical Survey

| field | value |
|---|---|
| Paper + link | Kamoi, Zhang, Zhang, Han, Zhang (PSU / UIUC). https://arxiv.org/abs/2406.01297 |
| Venue + year | **TACL 2024** (peer-reviewed) |
| Model sizes tested | Survey. Catalogued systems span PaLM-540B, GPT-3.5/4, Llama-2-70B, Minerva 8B/62B, GPT-Neo 1.3B, T5-base/large feedback models. **Almost no sub-10B primary evidence; the small-model entries are cross-model correctors, not self-correctors.** |
| Compare vs. self-consistency at matched compute? | It **demands** this as a checklist requirement ("Comparing with strong baselines using comparable computational cost. Required") and reports that prior work generally fails it: *"Self-correction is often not compared with sufficiently strong baselines, and it is still unclear whether it is better than other approaches."* |
| Finding — the three-way answer | **(1)** *"no prior work demonstrates successful self-correction with feedback from prompted LLMs, except for studies in tasks that are exceptionally suited for self-correction"* — the exception being tasks whose verification decomposes into easier sub-tasks (e.g. CoVe on list-generation). **(2)** *"self-correction works well in tasks that can use reliable external feedback."* **(3)** *"large-scale fine-tuning enables self-correction"* — but they flag that fine-tuning on *small* training data is unexplored. |
| The single most useful sentence for your framing | *"the bottleneck is in the feedback generation."* Models can revise given good feedback; they cannot generate good feedback about themselves. Also: the Saunders hypothesis that recognizing errors is easier than avoiding them *"is only true for certain tasks whose verification is exceptionally easy."* |
| Cost signal | Not quantified per-method; cost-matched comparison is a stated requirement, not a measurement. |
| **Table QA angle (do not re-derive, but note)** | Table QA over a *given* table has an unusually strong verification handle: a predicted answer either does or does not appear in a cell / is or is not consistent with a recomputed aggregate. By Kamoi's taxonomy that is **external feedback via a deterministic tool**, the one category where self-correction reliably works — not intrinsic self-correction, which is the category that fails. |

### 7. More Agents Is All You Need (Agent Forest) — the pro-ensemble case, and it is a *sampling* case

| field | value |
|---|---|
| Paper + link | Li, Zhang, Yu, Fu, Ye (Tencent). https://arxiv.org/abs/2402.05120 |
| Venue + year | **TMLR 10/2024** (peer-reviewed) |
| Model sizes tested | **Llama2-13B, Llama2-70B**, GPT-3.5-Turbo, GPT-4 (single only). Genuine small-open-model coverage. |
| Compare vs. self-consistency at matched compute? | It *is* self-consistency generalized (sampling + similarity voting, BLEU for open-ended). It compares against Debate (Du et al.) and Reflection (Shinn et al.) as *standalone* methods and as *base samplers*. Token usage reported (Table 5, Fig. 14 accuracy-vs-token-budget). |
| Finding — gains are largest exactly where you are | Table 6, relative gain from ensembling: **Llama2-13B +69% on GSM8K, +200% on MATH**; Llama2-70B +37% / +120%; GPT-3.5 only +16% / +34%. *"the relative performance gain is more substantial with increasing task difficulty"* and with **weaker models**. Llama2-13B at ensemble size 15 matches Llama2-70B. |
| Finding — debate ranks **worst** at small scale | Table 4 average ranking across 5 tasks: for Llama2-13B, plain sampling-and-voting ranks **2.2** (best) while **Debate ranks 5.0 (worst of all six methods)**; for 70B, Debate 4.4 vs. Ours 2.6. Table 3: Debate standalone on Llama2-13B GSM8K = 0.38 vs. sampling-and-voting = **0.59**. |
| The HumanEval failure — read this carefully | Debate scores **0 (zero)** on HumanEval for both Llama2-13B and Llama2-70B, standalone and combined. Their explanation: *"the noise generated by referencing the answers of other agents. The synthesized responses, which incorporate input from multiple agents, disrupt the coherence of the code logic."* A structured-output task where reading peers' full outputs destroys the answer. **A flattened table + a structured answer is closer to this regime than to GSM8K.** |
| Cost signal | Linear in ensemble size; ~235 tokens/sample on GSM8K for GPT-3.5. Debate integration capped at ensemble 10 "due to the significant computational overhead introduced by the communication architecture." |
| Caveat | Ensemble sizes of 15–40 are needed for the headline gains. At 40 samples × 992 questions this is a real but tractable cost on local 8B weights; it is not free. |

### 8. Are More LLM Calls All You Need? / Towards the Scaling Properties of Compound AI Systems

| field | value |
|---|---|
| Paper + link | Chen, Davis, Hanin, Bailis, Stoica, Zaharia, Zou. https://arxiv.org/abs/2403.02419 |
| Venue + year | 2024 (Stanford/Berkeley/Princeton) |
| Model sizes tested | **GPT-3.5-turbo-0125 only.** Flag this — no open-weight or small-model evidence. The contribution is theoretical + a scaling law, which is size-agnostic. |
| Compare vs. self-consistency at matched compute? | Vote *is* self-consistency; Filter-Vote adds an LLM filter. The question is scaling in K, not debate-vs-vote. |
| Finding | **Performance is non-monotone in the number of LLM calls.** On MMLU-Physics, TruthfulQA, GPQA and AVERITEC, Vote's accuracy rises then falls. Theorem 2 gives exact conditions: with easy fraction α and per-call correctness p₁ (easy) / p₂ (hard), Vote increases-then-decreases iff p₁+p₂>1 and α<1−1/t. Mechanism: *"More LM calls lead to higher performance on 'easy' queries, but lower performance on 'hard' queries."* On hard queries where an incorrect answer is modal (34% correct vs. 56% wrong in their AVERITEC example), **more votes converge to the wrong answer with certainty.** |
| Practical output | K* is computable from ~100 samples; Table 2 shows predicted K* matching empirical K* exactly, with optimal K ranging from **1 to 30** depending on the easy/hard mix. |
| Cost signal | Explicitly out of scope ("we do not discuss the cost of LM calls"), but the practical message is anti-scaling: *"not blindly scaling up."* |
| **Why it matters to you** | If you adopt self-consistency you must **tune K on a dev split, not assume more is better.** A Vietnamese Table QA test set with a heavy tail of multi-hop/aggregation questions is exactly the "high hard fraction" regime where K* is small. It also predicts that POMA's 10 parallel specialists may be *past* K*. |

---

## TIER 3 — Origin papers (flagged: the evidence base they created is weaker than its citation count implies)

### 9. Improving Factuality and Reasoning in Language Models through Multiagent Debate (Du et al.)

| field | value |
|---|---|
| Paper + link | Du, Li, Torralba, Tenenbaum, Mordatch (MIT/Google Brain). https://arxiv.org/abs/2305.14325 |
| Venue + year | arXiv 2023 → ICML 2024 |
| Model sizes tested | **gpt-3.5-turbo-0301 for every experiment.** One 20-question side experiment mixing ChatGPT + Bard. **Zero open-weight models, zero small models. Flag: effectively GPT-3.5-only.** |
| Compare vs. self-consistency at matched compute? | **No.** They include "Multi-Agent (Majority)" at 3 agents = 3 calls, then compare it to 3 agents × 2 rounds of debate = **9 calls**. Table 1 GSM8K: Majority 81.0 vs. Debate 85.0 — a 3× compute advantage for debate, presented as a like-for-like win. Huang et al. re-ran this on the full test set and the ordering reverses (see #5). Majority voting is **omitted entirely** from the factuality table (Table 2). |
| Test-set sizes | **100 arithmetic, 100 GSM8K, 100 MMLU, 300 chess.** The reported ±3.5 to ±4.7 standard errors mean the headline GSM8K gain (81.0 → 85.0) is within ~1 SE. |
| Finding | +4 to +15 points across six tasks vs. single-agent and vs. reflection. Reflection alone *hurts* on GSM8K (77.0 → 75.0) and MMLU (63.9 → 57.7). |
| Cost signal | 3 agents × 2 rounds = 9 calls minimum; they note "further gains with more agents and rounds" but hit **context-length errors** requiring summarization beyond a few agents. |
| Status | Treat as the hypothesis-generating paper, not as evidence. Its own reported baseline design is the specific thing Huang et al. (ICLR 2024) and Choi et al. (NeurIPS 2025) were written to correct. |

### 10. Encouraging Divergent Thinking in LLMs through Multi-Agent Debate (Liang et al.) — **read the appendix, not the abstract**

| field | value |
|---|---|
| Paper + link | Liang, He, Jiao, Wang, Wang, Wang, Yang, Shi, Tu (Tsinghua / SJTU / Tencent AI Lab). https://arxiv.org/abs/2305.19118 |
| Venue + year | **EMNLP 2024** |
| Model sizes tested | GPT-3.5-Turbo-0301, GPT-4-0314, **vicuna-7b-v1.5-16k, vicuna-13b-v1.5-16k**. Genuinely includes 7B and 13B — and this is where the paper quietly undermines itself. |
| Compare vs. self-consistency at matched compute? | **No.** Self-Consistency appears once (Counter-Intuitive AR, Table 3: 29.5 vs. MAD 37.0) with no sample count or token budget stated. On Common MT, SC is replaced by "Rerank," which uses an **external COMET-QE quality-estimation model** — external feedback, not self-consistency. |
| Finding at 7B/13B — **the gains nearly vanish** | Table 1, Common MT. Vicuna-7b: COMET 74.9 → 75.6 (lexical), 78.3 → 78.6 (contextless), 80.2 → 81.8 (contextual). Human score 2.55 → 2.67. Vicuna-13b: 76.6 → 77.2, 77.6 → 80.1, 82.2 → 82.6. Compare GPT-3.5, where MAD is claimed to surpass GPT-4. **The headline claim ("GPT-3.5 + MAD > GPT-4") is a GPT-3.5 result; the 7B/13B deltas are ≤1.6 COMET.** No Vicuna results are reported on the reasoning benchmark at all. |
| Three small-model warnings, stated by the authors | **(a) More agents hurts.** Table 7: 2 debaters 84.4 COMET → 3 debaters 83.1 → 4 debaters 82.9. Their diagnosis: *"Increasing the number of debaters fails when backbone LLMs are poor at long-text modeling… debaters tend to forget the views of other debaters during the debate."* Directly predicts trouble for POMA's 10 specialists. **(b) A weak judge is a ceiling.** Table 5: with strong (Turbo) debaters, a vicuna-13b judge scores 83.2 COMET / 3.47 human vs. a Turbo judge at 84.4 / 3.69. *"Strong debaters with a weak judge work better than the reverse"* — but the weak judge still costs you. **(c) The judge is biased.** Table 6, mixed-backbone debaters: *"the judge shows a preference to the side with the same LLM as the backbone. This bias indicates that LLMs might not be a fair judge when different LLMs are used for the agents."* (I am quoting their conclusion rather than the per-row counts — the judge column in the extracted Table 6 is ambiguous for the mixed rows and I could not confirm which model judged which row.) Their own mitigation: use the *same* LLM for judge and debaters, or make them fully distinct. |
| Also | Fig. 5: forcing debate past round 1 **harms** results; their adaptive-break (stop at round 1 for most items) is what makes MAD work at all. Maximum "tit for tat" (disagreement 0.988) is *worse* than moderate. |
| Cost signal | 2 debaters + 1 judge, up to 3 iterations; "a limitation of this work is that our method requires more time cost." |

### 11. Should we be going MAD? A Look at Multi-Agent Debate Strategies for LLMs

| field | value |
|---|---|
| Paper + link | Smit, Grinsztajn, Duckworth, Barrett, Pretorius (InstaDeep). https://arxiv.org/abs/2311.17371 |
| Venue + year | **ICML 2024** |
| Model sizes tested | GPT-3.5-turbo main; GPT-4 and **Mixtral 8x7B** as transfer checks. No dense sub-10B model. |
| Compare vs. self-consistency at matched compute? | **Yes, and rigorously** — accuracy plotted against average API calls, average tokens/question, wall-clock seconds, and total USD, across 7 datasets (Figs. 10–16) with a full configuration table. The best cost-controlled comparison in the pre-2025 literature. |
| Finding | *"multi-agent debating systems, in their current form, do not reliably outperform other proposed prompting strategies, such as self-consistency and ensembling using multiple reasoning paths."* On MedQA, Self-Consistency (0.76, $2.16) matches or beats Society-of-Minds at 4 agents × 3 rounds (0.72, $5.19) and every Multi-Persona config. Their nuance: MAD is not inherently worse, it is **more hyperparameter-sensitive**; tuning a novel "agreement intensity" prompt moved Multi-Persona from worst to best. |
| **The open-weight warning** | Hyperparameters tuned on GPT-3.5 **transfer to GPT-4 but fail on Mixtral 8x7B** (their Fig. 9, where MedQA accuracy across configs spans ~0.1 to ~0.6). *"this transferability does not extend well to Mixtral 8x7B."* Any MAD hyperparameter you read off a GPT-family paper is not valid for Qwen3-8B / SEA-LION. |
| Cost signal | Best in class. MedQA: Single Agent 0.68 @ $0.43; SoM 4 agents × 3 rounds 0.72 @ $5.19 (12× cost); ChatEval 3 rounds $3.48; Self-Consistency 0.76 @ $2.16. Debate configs need 2.5–15 API calls/question. |
| Limitation they state | *"future works could extend this line of work using open-source models and in-house infrastructure."* That gap is your thesis's opportunity. |

---

## TIER 4 — Small-model capability floors: judging, aggregation, and agent protocols

### 12. SLMJury: Can Small Language Models Judge as Well as Large Ones? — **directly answers your "grounded single answer selector" question**

| field | value |
|---|---|
| Paper + link | Laddha, Pradhan, Srivastava (LNMIIT / Virginia Tech). https://arxiv.org/abs/2606.07810 |
| Venue + year | 2026 preprint. **Provenance caveat: 1 vote / 30 views, unreviewed.** Large-N and methodologically detailed; I'd cite it with the caveat stated. |
| Model sizes tested | **16 judges, 0.6B–14B**: Llama-3.2-1B/3B, Llama-3.1-8B, Qwen2.5-1.5B/3B/7B, Qwen3-0.6B/1.7B/4B/8B/14B, Phi-4, Phi-4-mini, 3 reasoning variants. N=64,824 judgments per configuration across 8 closed-ended benchmarks + SummEval + MT-Bench. |
| Compare vs. self-consistency at matched compute? | Yes for the judging task: individual judge vs. 3-judge majority vote vs. multi-agent debate (Reflect-Critique-Refine). |
| **Answer: yes, an 8B model can judge — well** | Phi-4 (14B) 89.55%, Qwen3-14B 89.51%, **Qwen3-8B 88.96%**, Phi-4-mini (3.8B) 88.22%, Qwen3-4B 87.81%, **Llama-3.1-8B 86.79%** agreement with the oracle. *"Reliable automated evaluation does not require large proprietary models."* Instruction-following rate >99.8% for every top judge — output is parseable. |
| **But: debate destroys judging, and voting adds nothing** | *"under the Reflect-Critique-Refine (RCR) debate protocol, multi-agent debate degrades accuracy across all tested configurations."* Best debate config = 87.04% vs. best individual = 89.55%. Best 3-judge majority-vote panel = 89.61% vs. best individual 89.55% — **+0.06%**, because "the top judges already share highly correlated error patterns." Persona robustness is excellent (Qwen3-14B varies 0.08% across six adversarial personas). |
| Two failure modes that matter for a selector | **(a) Default-accept bias:** 60–65% of top-judge errors are false positives — accepting an incorrect answer rather than rejecting a correct one. A selector built this way will under-reject. **(b) Domain specialization dominates scale:** Qwen2.5-7B scores 95.9% on math but **58.7%** on general reasoning (a 37.2-point gap); Phi-4 and Qwen 3 hold the gap near 10%. Pick the judge family by generalization gap, not by parameter count. |
| Budget finding | Quick 10-token verdicts beat 8192-token reasoning on *verifiable* domains (math) for 8/13 judges; reasoning wins on *non-verifiable* general tasks. Table QA answer-matching is a verifiable domain → cheap verdicts likely suffice. |
| Cost signal | 10 tokens vs. 8192 tokens per verdict — a ~800× output-token difference with no accuracy loss on verifiable tasks. |

### 13. AgentFloor: How Far Up the Tool-Use Ladder Can Small Open-Weight Models Go?

| field | value |
|---|---|
| Paper + link | Karmakar & Chatterjee (Harvard). https://arxiv.org/abs/2605.00334 |
| Venue + year | 2026 preprint. **Provenance caveat: 9 votes / 33 views, unreviewed.** Pre-registered TOST equivalence testing with bootstrap CIs — unusually rigorous for a preprint. |
| Model sizes tested | **16 open-weight models, 0.27B–32B** (incl. qwen3:8b, ministral-3:8b, qwen3:14b) + GPT-5. 16,542 scored runs, 6-tier ladder, deterministic abstract tools. |
| Compare vs. self-consistency? | Not applicable — this is about agentic protocol-following capability, not answer aggregation. |
| **The answer to "do 8B models follow multi-turn agent protocols?"** | **Up to two steps, yes. Past that, no.** Per-tier TCR for ministral-3:8b: A0 instruction-following 75%, A single tool 84%, **B 2-tool chain 84%**, **C branching on an intermediate result 56%**, **D multi-source synthesis 16%**, **E long-horizon planning 16%**. qwen3:8b: 80 / 76 / 64 / 24 / 0 / 0. The B→C transition is "the steepest single column-step in the heatmap." At the 80% reliability bar, A0 clears at 4B and A clears at 3B, but **"C, D, and E never clear at any threshold in [60, 90]"** for any open-weight model in the corpus — and GPT-5 only reaches 10% on E. |
| Failure modes at 8B-26B | F4 step-budget exhausted (41%) and F1 hallucinated tool (36%) dominate for the best open-weight model, vs. F5 early resignation (39%) for GPT-5. Different regimes, different fixes. |
| Interventions do not generalize | An explicit-submission prompt took ministral-3:8b from 0/5 to 5/5 on one task and was **null on four other models**. The "natural" plan/execute/submit decomposition prompt **regressed every model tested**. |
| Cost signal | gemma4:26b equivalent to GPT-5 overall (Δ=+0.4 pp, 90% CI [−4.0,+5.1]) at ~15× lower cost and 2.5× lower latency. |
| **Why it matters to you** | A 2-step pipeline (retrieve/normalize → answer) is inside the reliable envelope at 8B. A 5-persona review-then-deliberate loop, or a hint-predictor → router → 10-specialists chain, is tier C/D territory — the region where no 8B model clears 60%. This is the capability explanation for why POMA's orchestration bought 1.27 EM. |

### 14. The Interaction Tax: When Communication Erases Diversity in Multi-Agent Teams

| field | value |
|---|---|
| Paper + link | Ann, Liu, Tan (University of Chicago). https://arxiv.org/abs/2608.23541 |
| Venue + year | 2026, ICML-formatted preprint. **Provenance caveat: 4 votes / 18 views, unreviewed; 5 seeds per cell and the main effect is driven by one of three tasks (their own leave-one-out shows β_div drops from +0.188 to +0.014 when Erdős is removed). Cite the mechanism, not the coefficient.** |
| Model sizes tested | Claude Sonnet 4, GPT-4o, Gemini 2.5 Flash. **No small models — this is a frontier-model study.** Flag it. |
| Compare at matched compute? | **Yes** — all 10 configurations under an identical budget vector (200K tokens, 600s, 25 steps), with Best-of-N, Self-Refine and Verifier-Guided Search as single-agent controls, on 11 verifier-scored tasks with held-out evaluators. |
| Finding | **"No configuration achieves positive aggregate MEG"** — not one multi-agent workflow beats the best single-agent baseline. MoA (independent proposers, then synthesis) is the only one whose CI includes zero. **The mechanism is the transferable part:** when agents read each other's complete outputs, mean pairwise solution distance collapses from 0.315 to 0.229 **within a single round**. Chain, MAgICoRe and Debate all have positive same-model MIG but negative diverse-model MIG (−0.024, −0.035, −0.078). MoA escapes because "its proposers never see each other's outputs." |
| The conditional rule for critique | Critique helps **only when the violated rule is cheap to locate and repair.** Knapsack (capacity violation = one arithmetic check): diverse Debate 10/10 feasible vs. 2/10 same-model. 3AP-Free (find an arithmetic-progression triple among many): diverse Debate **0/10** vs. 6/10. On graded-feedback tasks the first critique round **degrades the solution 57% of the time (17/30 runs)**. |
| Prescription | *"Lower-bandwidth signals, such as scores, method descriptions, or failure causes, may preserve independent exploration while still supporting coordination."* Their workflow recipe: 2–3 diverse model families → generate independently, no cross-visibility → rank with a deterministic checker → critique-and-revise **only if the task exposes local, checkable violations** → verify with a held-out check. |
| Cost signal | All 10 configurations run under an identical budget vector: 200K tokens, 600s wall clock, 30s per call, 25 steps. Interaction therefore costs the same as independent sampling here and still loses — the tax is in lost diversity, not in tokens. |
| **Why it matters to you** | If a frontier trio cannot survive full-solution exchange, three 8B models will not. And it names the fix: exchange *scores and failure causes*, not full candidate answers. |

---

## VERDICT

> **For an 8B backbone on Vietnamese Table QA, what is the evidence-backed justification for using multi-agent at all, and what specific form should it take?**

**There is no evidence-backed justification for deliberative multi-agent — persona role-play, self-review,
peer critique, or debate — on a single sub-10B backbone.** Five independent studies at 7–8B
(Choi NeurIPS 2025; Bertalanič 2026; AWS 2026; Zhang 2025 on Llama3.1-8B; Liang EMNLP 2024 on Vicuna-7B/13B)
all find that same-backbone deliberation is at best equal to, and usually worse than, sampling the same
model K times and voting, at equal or lower cost. Choi et al. prove why: under a Bayesian belief model,
debate is a martingale — it moves individual beliefs around but leaves the expected probability of the
correct answer unchanged. Empirically, at 8B the variance is not neutral but *adverse*, because
RLHF-tuned small models are sycophantic: modal-adoption rates of 69–85% and correct→wrong flip rates of
55–70% mean peer exposure destroys more correct answers than it rescues. The AWS study's win/loss
decomposition makes this concrete: debate is uniquely correct on 13.7% of MuSiQue items and uniquely
wrong on 12.3%. Your 0.27–0.56 F1 ablation deltas are that cancellation, measured on your data.

**Three things are still justified, in descending order of evidential support.**

**(a) Sampling + aggregation (self-consistency), with K tuned — not assumed — and with one scope caveat
you must state.** This is the compute-matched winner in every head-to-head. Li et al. (TMLR 2024) show
the gain from ensembling grows as models get weaker and tasks get harder: Llama2-13B gains +69% relative
on GSM8K and +200% on MATH, against +16%/+34% for GPT-3.5. You are in the regime where ensembling pays
most. Chen et al. prove the curve is non-monotone in K, with the optimum set by the easy/hard mix, and
give a procedure to estimate K* from ~100 dev samples — do not assume more samples is better, measure it.

**The scope condition:** Chen et al. limit their own claims to *"tasks with a fairly small number of
possible responses (e.g., multiple-choice questions) that support a majority vote,"* and Li et al. had to
replace exact-match voting with BLEU similarity for open-ended generation. Almost all the compute-matched
evidence above comes from multiple-choice or single-integer answer spaces. **Free-form Vietnamese Table QA
has a far larger answer space, and votes only aggregate *through the normalizer*: two correct answers in
different surface forms do not vote together.** So the self-consistency gain is not independent of
normalization — it is a function of it. This is the mechanistic reason POMA's normalizer was worth
11.83 EM, and it means your SC result must be reported as conditional on the normalizer's ability to
collapse surface variants.

**(b) External/tool verification, not self-review.** Kamoi's survey is unambiguous: the bottleneck is
feedback generation, and self-correction works when feedback is *reliable and external*. Table QA has a
free reliable verifier that pure reasoning tasks lack — cell membership, type agreement, recomputable
aggregates. That converts intrinsic self-correction (the failing category) into external-tool
self-correction (the working category). The Interaction Tax result sharpens the condition: critique
helps when the violated rule is cheap to locate (Knapsack, 10/10) and hurts when it is not (3AP-Free,
0/10). Deterministic cell-grounding checks are the cheap-to-locate kind. This ranks above heterogeneity
because its support is peer-reviewed (Kamoi TACL 2024, Huang ICLR 2024) and applies directly at 8B.

**(c) Backbone heterogeneity — the unexploited axis, but the evidence does not yet cover your case.**
Zhang et al. call model heterogeneity "a universal antidote," worth +6.4% (SoM) and +8.2% (EoT) over the
same-model average and up to +5.8% over CoT-average, with the gain traceable to questions one model
solves and the other does not. You have three backbones with different pretraining mixtures — Qwen3-8B,
SEA-LION 8B (Southeast-Asian pretraining), Llama-3.1-8B — and have so far treated them as independent
experimental conditions rather than as ensemble members. Vietnamese Table QA is where their error
distributions should decorrelate most: SEA-LION's Vietnamese coverage is not Qwen's.

**But state the gap honestly: every heterogeneity result I found is cross-tier or cross-lab.** Zhang's
gain comes from pairing gpt-4o-mini with Llama3.1-**70b**; Ann's diversity coefficient comes from
Claude/GPT-4o/Gemini. Choi et al.'s "heterogeneous" test was *personas on one backbone*, and majority
voting still matched it. **There is no published evidence that three same-size 8B open-weight models
decorrelate enough to produce the complementary-error cells the mechanism requires.** That is why (c)
ranks below (b) — and why Ablation A3 below opens with a gate that measures the decorrelation before
spending anything on the architecture. If it holds, combine them **without letting them read each other's
full answers** — independent proposal plus selection, like MoA, not debate.

**On "a stronger judge/aggregator": scaling the judge is not the lever.** SLMJury puts Qwen3-8B at 88.96%
and Llama-3.1-8B at 86.79% oracle agreement with >99.8% instruction-following — an 8B selector is already
adequate. Liang et al. Table 5 shows judge choice is *secondary* to debater quality ("Strong debaters with
a weak judge work better than the reverse"), and SLMJury's 3-judge panel adds only +0.06% because small
judges' errors are correlated. The constraint binds on **generation and on candidate-pool coverage**, not
on selection. Build one selector, audit its default-accept bias (60–65% of its errors), and do not build
a jury or reach for a larger judge.

**Recommended system shape:** K independent samples from each of 2–3 heterogeneous 8B backbones →
deterministic table-grounded verification filter → single-judge or confidence-weighted selection over the
surviving candidates. No debate rounds, no persona review, no peer deliberation. And report every
number with the answer-normalization pipeline held fixed across arms — because Choi et al.'s Appendix F
shows extraction choice can reverse conclusions, and your own 11.83-of-13.10 EM result shows the same.

---

## THREE RANKED DESIGN IMPLICATIONS, WITH THE ABLATION THAT PROVES EACH

> Ranked 1 > 2 > 3 by strength of evidence. The sections below appear in the order 1, 3, 2 on the page;
> each header states its rank and why. Ablations are numbered to match the rank (A1, A2, A3), and A1 must
> run first because A2 and A3 both operate on the candidate pool A1 produces.

### Statistical preamble — your 992-question test set cannot detect your current effect sizes

At n=992 and accuracy ≈65%, SE on one arm ≈ **1.51 pp**. Comparing two arms as *independent*
proportions, the minimum detectable effect at 80% power / α=0.05 two-sided is
(1.96+0.84)·√2·1.51 ≈ **6.0 pp**. Your prior orchestration effect was **1.27 EM**. It was not
measurable at this n by an unpaired test — and neither was 0.27–0.56 F1.

**Every ablation below must be paired** (identical items, identical seeds, McNemar's exact test or a
paired bootstrap over items). For McNemar with discordance rate d, MDE ≈ 2.8·√(d/n). At d=0.15 that is
**3.4 pp**; at d=0.08, **2.5 pp**. To resolve a 1.27-point effect you would need discordance below ~2%,
which no 3.5×-cost architectural change produces. **State this explicitly in the thesis.** "The prior
orchestration gain was within the resolution of the evaluation" is a legitimate, citable negative result,
and it is stronger than a weak positive.

Report for every arm: paired delta, 95% bootstrap CI over items, McNemar p, discordance counts (b, c),
**and total generated tokens**. Bertalanič's noise control and Choi's extraction control are the two
control arms most MAD papers omit; including them is a contribution in itself.

---

### Implication 1 (highest confidence) — Replace all deliberation with self-consistency at matched token budget, and tune K

**Claim.** On an 8B backbone, homogeneous multi-agent deliberation does not beat K-sample
self-consistency at equal generated tokens; the apparent gain is an ensembling effect plus a
re-prompting effect.
**Support.** Choi NeurIPS 2025 (Qwen2.5-7B, Llama3.1-8B, matched ensemble, martingale proof);
Huang ICLR 2024 Table 7 (MAD 83.0 vs. SC 88.2 @ 9 responses); Zhang 2025 (Llama3.1-8B, MAD win rate
<20% vs. CoT, worse vs. SC); Smit ICML 2024 (cost-controlled, 7 datasets).

**Ablation A1 — the token-matched ladder.** Fix a total generated-token budget B per question.
Run, on all 992 items, same seeds, same normalizer:

| arm | description |
|---|---|
| A1.0 | greedy single pass |
| A1.1 | self-consistency, K ∈ {3, 5, 10, 20, 40}, T=0.7 |
| A1.2 | ViPanelTR (5 personas + self-review + peer deliberation) |
| A1.3 | POMA (hint → router → 10 specialists) |
| A1.4 | **noise control** — same number of rounds and same context length as A1.2, but the "peer answers" inserted are answers to *randomly chosen other questions* (Bertalanič's design) |
| A1.5 | **single agent, 10× output budget** (Bertalanič's extended-generation control) |

**Prediction.** A1.1 at matched B ≥ A1.2 and A1.3; and **A1.4 ≈ A1.2**. A1.4 is the decisive arm: if
injecting irrelevant rationales reproduces the deliberation gain, the gain is length/re-prompting, not
collaboration, and the persona architecture is refuted on your own data. Bertalanič found the noise
control *beat* debate on Qwen/GSM-Hard (63.2 vs. 58.8).
**Proves it if:** paired McNemar on A1.1-vs-A1.2 at matched B is non-significant or favours A1.1
(MDE ~2.5–3.4 pp), **and** A1.4-vs-A1.2 is non-significant.
**Also report:** accuracy-vs-K curve to locate K*, per Chen et al. Expect non-monotonicity if your test
set has a large hard fraction; report K* and the fitted easy-fraction α.

**The normalizer interaction — a cheap, novel measurement.** Because votes only merge answers the
normalizer maps together, the K-curve is *normalizer-dependent*: a weak normalizer fragments correct
answers across surface variants and flattens the SC slope. Run the K ∈ {3,5,10,20,40} sweep under **two
normalizer strengths** (e.g. exact match vs. your full normalizer). **The difference in slope is the
interaction**, and it is, as far as I can tell, unmeasured in the literature — Chen et al. and Li et al.
both sidestep it by restricting to small answer spaces or substituting BLEU. This reframes your 11.83-EM
normalization result from "a confound we controlled" into "a mechanism we characterized": at 8B on
free-form Table QA, the normalizer is not post-processing, it is **the aggregation function**, and
test-time scaling is bounded by it. That is a stronger thesis contribution than the ablation it came from.

---

### Implication 3 — Backbone heterogeneity is the only *collaborative* axis left, but gate it on a decorrelation measurement first

> **Ranked third, not second, deliberately.** All supporting evidence is cross-tier (Zhang: gpt-4o-mini
> + Llama3.1-**70b**) or cross-lab-frontier (Ann: Claude/GPT-4o/Gemini). No published result shows that
> three *same-size* 8B open-weight models decorrelate enough for the mechanism to fire. Implication 2's
> support is peer-reviewed and directly on-scale; this one is an extrapolation with a built-in test.

**Claim.** Diversity must come from different model weights, not different system prompts on one model;
and it must be combined by independent-generate-then-select, because full-solution exchange destroys the
diversity within one round.
**Support.** Zhang 2025 Heter-MAD (+6.4% SoM, +8.2% EoT, gains localized to CW/WC questions — exactly
the complementary-error cells); Ann 2026 Interaction Tax (mean pairwise distance 0.315 → 0.229 after one
exchange; MoA is the only configuration with positive diverse-model MIG); Li TMLR 2024 (debate-generated
noise zeroes out structured-output tasks at 13B/70B); Bertalanič 2026 (prompt-level persona variance over
one parameter space "fails to decouple the underlying error distributions").

**Ablation A3 — the diversity-source 2×2.**
Factor 1: diversity source ∈ {same backbone × 3 personas, **3 different backbones** (Qwen3-8B,
SEA-LION 8B, Llama-3.1-8B)}.
Factor 2: combination ∈ {**independent + select** (no cross-visibility), full-answer exchange + 1 debate round}.
Four arms, matched total tokens, all 992 items paired.

**First, measure whether the diversity is even there** — this gates everything. Compute, per item:
(i) **complementarity**: the CW/WC cell sizes, i.e. % of items exactly one backbone gets right
(Zhang's Fig. 5 decomposition); (ii) **between- vs. within-model variance ratio** on per-item correctness
(Ann's B/W ratio — diversity only pays when B/W ≥ ~2); (iii) **Spearman correlation of per-item
correctness** between backbone pairs — low or negative ⇒ errors are independent ⇒ ensembling pays.
**If CW+WC is small or B/W < 1, stop — heterogeneity has nothing to offer on this dataset, and that is
itself a clean reportable negative for Vietnamese Table QA.**

**Prediction.** Heterogeneous + independent-select > homogeneous personas + independent-select >
either with full-answer exchange. Exchange should *reverse sign* for the heterogeneous arm specifically
(that is the interaction tax).
**Proves it if:** the interaction contrast (diversity source × combination) is significant by paired
bootstrap over items, with the heterogeneous-exchange cell below heterogeneous-independent.
**Note on power:** a 2×2 over 992 paired items is your best-powered design here, because the
independent-select and exchange arms share the same round-1 generations — discordance is confined to
items the exchange actually changed, which makes McNemar unusually sensitive.

---

### Implication 2 — Move the remaining "agent" budget into table-grounded external verification, and audit the selector for default-accept bias

> **Ranked second because its support is peer-reviewed and on-scale:** Kamoi (TACL 2024) and Huang
> (ICLR 2024) both explicitly recommend external feedback as the working alternative to self-review,
> and the 8B preprints (#2, #3) converge on it.

**Claim.** An 8B model cannot generate reliable feedback about its own reasoning, but it can reliably
*use* feedback from a deterministic table checker. A cell-grounding verifier will outperform any
self-review loop at a fraction of the cost.
**Support.** Kamoi TACL 2024 ("no prior work shows successful self-correction with feedback from
prompted LLMs in general tasks"; "self-correction works well in tasks where reliable external feedback
is available"; "the bottleneck is in the feedback generation"); Huang ICLR 2024 (intrinsic degrades
monotonically with model weakness; Llama-2-70B 62.0 → 36.5); Ann 2026 (critique helps iff the violation
is cheap to locate: 10/10 vs. 0/10); AWS 2026 (a one-shot self-critique probe on Llama-3.1-8B flipped
127/127 answers — zero information); SLMJury (Qwen3-8B judges at 88.96% but 60–65% of its errors are
false accepts).

**Ablation A2 — the feedback-source ladder**, all arms revising the *same* K candidate answers, matched tokens:

| arm | feedback source |
|---|---|
| A2.0 | no revision (self-consistency output) |
| A2.1 | intrinsic self-critique ("review your answer and find problems") |
| A2.2 | **deterministic table check** — is the answer a cell value / does its type match the column / does a recomputed aggregate agree / is the cited row-column span valid |
| A2.3 | 8B LLM-as-judge selecting among K candidates |
| A2.4 | A2.2 filter, then A2.3 judge over survivors |
| A2.5 | oracle upper bound — is the correct answer anywhere in the K-candidate pool (**the oracle gap**) |

**Prediction.** A2.2 > A2.0 ≥ A2.1, and A2.4 best. A2.1 may fall *below* A2.0, which would replicate
Huang et al. at 8B on a new language and modality — a publishable negative in its own right.
**A2.5 is the most informative single number in your thesis.** Bertalanič measured oracle gaps up to
32.3 pp; AWS measured +14 pp of per-example routing headroom. If your oracle gap is large, the problem
is *aggregation*, not generation, and every remaining engineering hour belongs in the selector rather
than in more agents.
**Selector audit (required, from SLMJury):** report the judge's false-accept vs. false-reject split.
If ~60% of errors are false accepts, the decision threshold is miscalibrated, and shifting it is a
zero-token accuracy gain. Also report agreement stratified by question type (lookup / aggregation /
multi-hop) — SLMJury found 37-point domain gaps within a single judge, so a single aggregate judge
accuracy will hide the failure region.
**Proves it if:** A2.2-vs-A2.1 is significant and signed positive by paired McNemar, and A2.1-vs-A2.0
is non-positive.

---

## What I could NOT verify — stated explicitly

- **No paper evaluates multi-agent deliberation on Vietnamese, or on Table QA, at 8B.** Every result
  above transfers by analogy. The closest structural match is AWS's MuSiQue setting (multi-hop QA over
  supplied context, 8B, matched ceiling) — long context + extraction + multi-hop, but English and not tabular.
- **Nothing measures whether the sycophancy/vulnerability rates found on GSM-Hard and MMLU-Hard hold on
  tabular QA**, where the shared context is a flattened table rather than a word problem. Because all
  your agents read the *same* table string, the "diversity" available to debate is even smaller than in
  these studies — I expect the effect to be *more* negative, not less, but that is an inference, not a measurement.
- **The compute-matched self-consistency evidence is drawn almost entirely from small answer spaces**
  (multiple choice, single integers). Chen et al. state the limitation themselves; Li et al. had to
  substitute BLEU similarity for open-ended tasks. **Its transfer to free-form Vietnamese Table QA is
  conditional on the normalizer, and I found no paper that measures the SC-gain × normalizer-strength
  interaction.** That gap is an opportunity, not just a caveat — see Ablation A1.
- **No same-size open-weight heterogeneity result exists.** Every heterogeneity gain I found pairs models
  from different capability tiers or different labs. Whether three 8B open-weight models decorrelate
  enough is untested in the literature and is the gate in Ablation A3.
- **Huang et al. contains no sub-10B model.** The smallest is Llama-2-70B. "8B cannot self-correct" is an
  extrapolation from a monotone capability gradient plus direct 8B evidence in the 2026 preprints. Say so.
- **Du et al.'s benchmark sizes (100 questions) are small enough that I could not confirm their headline
  GSM8K gain exceeds one standard error** of their own reported ±3.9/±3.5. I am reporting their numbers,
  not endorsing them.
- **Provenance flags.** Items #2, #3, #12, #13, #14 and the vote/view counts for #10's alphaXiv entry are
  2026 arXiv preprints with low engagement and no confirmed peer review. I read actual page text for each
  and report their own stated limitations (seed counts, N=300 subgroup power, single-prompt probes,
  leave-one-out sensitivity). Put load-bearing claims on Choi (NeurIPS 2025), Huang (ICLR 2024),
  Kamoi (TACL 2024), Smit (ICML 2024), Li (TMLR 2024) and Liang (EMNLP 2024); use the preprints as
  converging same-scale support with the caveat stated.
- **I did not independently verify** the Smit et al. Mixtral numbers beyond what their Fig. 9 caption and
  text state, since exact per-config values for Mixtral are not tabulated in the pages returned.
