# Review: MemView abstracts for AAMAS 2027 (pre-submission, abstract-level)

**Object reviewed.** The two "Vòng 3" abstracts in `paper/aamas2027-abstract.md` (the versions with the
Open-ViTabQA introduction sentence), under their suggested titles:

- V1: *MemView: Shared Example Memory and Complementary Table Views for Vietnamese Table Question Answering*
- V2: *MemView: An Empirical Study of Shared Memory and Multi-Agent Reasoning for Vietnamese Table Question Answering*

**Scope caveat.** No full paper exists yet, so this is not a review a real reviewer could write. I audited each
claim in the abstracts against the evidence in the repository (`docs/research/2026-09-26-memxam-multi-agent-qwen3-8b.md`
§19–§21, the prediction files in `outputs/mas_tqa/qas_test/`, and the code in `mas_tqa/`). Points marked
**[author-only]** come from that history and would not be visible to a reviewer from the abstract; they matter
because the paper must disclose them or it becomes vulnerable. Scores below are for the paper the abstracts
promise, assuming the full text reports exactly the evidence that exists today.

## Summary

Both abstracts describe MemView, a prompting-only system for question answering over Vietnamese Wikipedia tables
(Open-ViTabQA) built on a small LLM. All agents receive training question–answer pairs from the same table as
in-context examples. Agent A reads a flattened table and draws three samples; agent B reads a Markdown key–value
serialization and cites evidence cells; when they disagree, an LLM validator scores the candidates. With
Qwen3-8B, MemView reaches 81.85 EM on the 992 test questions, above zero-shot, few-shot, multi-agent debate,
Chain-of-Table and CoAgt with the same backbone, above the published Gemini 1.5 Pro result, and 1.58 EM below
the published human score. Ablations attribute most of the gain to the example memory (74.90 EM without it) and
0.3–1.2 EM to the second agent and validator; restricting memory to other tables gives 79.03 EM. V1 frames this
as a system contribution, V2 as an empirical study of where the gains come from.

## Claim–evidence audit

| # | Claim (V1/V2) | Evidence in repo | Status |
|---|---|---|---|
| C1 | Open-ViTabQA is "the first Vietnamese table question answering benchmark", 9,911 QA pairs over 329 tables | Dataset paper abstract ("first Vietnamese dataset for Table QA"); split sizes 7,928/991/992 | Supported, but it is the dataset authors' claim; attribute it ("introduced as the first…") |
| C2 | Memory = same-table training QA pairs | `prompts_qwen.messages_a/b`, `data.retrieve_same_table` | Supported |
| C3 | A: flattened table, 16 exemplars, 3 samples; B: Markdown-KV, 8 exemplars, evidence | `suite_v10` | Supported |
| C4 | Answer returned directly "when A's samples agree and B concurs" | `methods.py:840–841`: also returns when B's answer is invalid; 3 questions fall back to A only when the KV table overflows the context | Slightly inaccurate; fine for an abstract, must be exact in §Method |
| C5 | 2.4 LLM calls per question | 2.39; A's three samples are one request with n = 3 | Supported, but ChatGPT's reviewer already flagged "3 samples vs 2.4 calls" as confusing: say "requests" and explain n = 3 |
| C6 | 81.85 EM, 90.66 F1, 87.38 R1, 64.37 MET, 0.711 BIF | Recomputed this session | Supported. EM includes a yes/no verbalization step (see W6) |
| C7 | Beats ZS 71.77, FS 73.29, debate 72.58, CoT 54.74, CoAgt 48.59 "using the same backbone" | Each is a single run on the full test set | Numerically supported; fairness of the CoT/CoAgt runs is weak (W4), and no baseline has the memory (W3) |
| C8 | Beats Gemini 1.5 Pro 60.80; 1.58 EM below human 83.43 | Dataset paper, Table 11 | Numbers correct; evaluation pipelines differ (W6) |
| C9 | Memory accounts for most of the gain; no memory = 74.90 | `memview_nm.runq1`: 74.90 | Supported (−6.95 EM, paired CI [−8.97; −4.94] on the lenient variant) |
| C10 | Second agent + validator add 0.3–1.2 EM | +0.30 (no memory), +1.21 (other-table memory), +1.00 (same-table memory); the one paired CI computed (same-table, +1.01 [−0.20; +2.22]) includes 0 | Numerically supported; not statistically supported (W5) |
| C11 | Other-table memory = 79.03 EM | `memview_q.runcross1` | Supported |
| C12 | V2: memory contribution "substantially larger" than the added agents | 6.95 vs ≤1.21 EM | Supported |

## Strengths

- **S1.** The ablation grid (C9–C11) is unusually informative for a Table QA systems paper. It crosses three
  memory conditions (none, other tables, same table) with three aggregation levels (A only, A+B vote, full
  MemView), all from the same runs, and it separates the retrieval effect from the agent effect.
- **S2.** Both abstracts are honest about the small multi-agent contribution. That candor protects the paper
  from the most common rebuttal-phase collapse, where a reviewer finds the ablation the authors buried.
- **S3.** The baseline set is broad for the subfield: prompting baselines in the same prompt frame, a standard
  multi-agent baseline (debate), and two published Table QA agent systems, all on the same backbone and the full
  test set.
- **S4.** The other-table-memory condition directly addresses the obvious objection that same-table demonstrations
  make the setting easier; 79.03 EM shows most of the benefit survives.
- **S5.** V2 states a research question and ends with a finding that follows from the data, which is the
  framing the evidence can actually carry.

## Weaknesses

Ordered by severity. W1 and W2 would each draw a score-lowering comment; W3–W5 are what a careful reviewer writes.

- **W1. [author-only] Design decisions were iterated on the test set, so 81.85 is not a clean held-out number.**
  MemView v10 was run on the full test set (80.65 EM); its test outputs were then analysed (why it returned so
  many Null answers), the prompts were changed (table title, a general Null rule), and v11 was run on the same
  test set (81.85). The table-representation screening (D09) that motivated the Markdown-KV view was also run on
  200 test questions. None of this is visible from the abstract, but a paper that reports v11 as its test result
  without saying so is exposed if anyone asks how the prompt was chosen. *Fix:* either (a) justify every v10→v11
  change on dev and report dev numbers for both, stating plainly that v11 was selected after a test run, or
  (b) freeze the system and report a fresh run on held-out data. Remedy class: `writing` for disclosure,
  `new experiment` for dev justification.
- **W2. The multi-agent contribution is small relative to what the title and venue imply, and the retrieval
  component has close prior work.** Same-table example memory is retrieval of similar in-context demonstrations,
  as in KATE (Liu et al., 2022, "What Makes Good In-Context Examples for GPT-3?") and example selection for
  text-to-SQL (e.g., DAIL-SQL, Gao et al., 2024). The agent side combines self-consistency (Wang et al., 2023),
  two serializations, and an LLM judge (Zheng et al., 2023). By C10, these add 0.3–1.2 EM. For AAMAS the
  question will be "what is learned about agents?" V1 answers it weakly; V2's answer, that memory matters more
  than agent count at this scale, is a finding, but it is supported by one backbone and one dataset, so the
  title's "An Empirical Study of … Multi-Agent Reasoning" overreaches (the reviewer ChatGPT raised the same
  point). *Fix:* keep V2, and scope the claim to "on Open-ViTabQA with an 8B model"; the paper needs a second
  backbone or dataset before the finding generalises. Classes: `writing` (scope), `new experiment` (second
  backbone).
- **W3. Every baseline in the headline list lacks the memory MemView uses.** Zero-shot, few-shot and debate all
  run without same-table examples, so the 8–9 point margins in C7 mostly measure retrieval (C9). The fair
  comparison already exists: agent A alone with the same memory scores 80.85 EM, 1.0 below MemView. A reviewer
  who reads the ablation will see that the abstract's comparison list flatters the system. *Fix:* add the
  memory-matched single agent (80.85) to the abstract's comparison, and in the paper run debate with the same
  memory. Classes: `writing` now, `new experiment` for debate + memory.
- **W4. [author-only] CoAgt and Chain-of-Table are weak reproductions.** Both keep their original English
  WikiTQ prompts on Vietnamese tables; Chain-of-Table runs with thinking disabled and reads only the first
  100 rows; one Chain-of-Table question overflows the context and is counted wrong. Listing 48.59 and 54.74 in
  the abstract invites a "strawman baselines" comment. *Fix:* either drop them from the abstract and describe
  the setup in §Experiments, or run them with translated demonstrations. Classes: `writing` or `new experiment`.
- **W5. Single runs; the small effects are inside run-to-run variation.** Every configuration is one run.
  Two identical earlier runs differed by about 1.6 EM, which is larger than the 0.3–1.2 EM agent gains and
  comparable to the 1.58 EM gap to human performance. The one paired interval computed for the agent gain (same-table memory) includes 0.
  The abstract's phrasing ("gains of 0.3–1.2 EM") is accurate, but V2's conclusion rests on the contrast
  between two effects, one of which is not distinguishable from zero. *Fix:* three runs of MemView, agent A
  alone and few-shot, with means and standard deviations; state the agent gain as "not significant" if it
  stays that way. Class: `new experiment` (about $2–3 of GPU time).
- **W6. Comparisons with published numbers mix evaluation pipelines.** Our EM applies a rule-based yes/no
  verbalization before scoring (it changes MemView by +0.10 EM and the baselines by +0.6 to +0.9); BIF uses our
  ViNLI checkpoint rather than the dataset authors'; METEOR is nltk's implementation, not confirmed to match the
  dataset paper's. The Gemini and human rows are therefore "reported" numbers, as V1/V2 already say for Gemini
  but not for human performance. *Fix:* say "the reported human EM", report raw EM (without verbalization) in
  the paper, and compare BIF only among our systems. Class: `writing`.
- **W7. Presentation.** Both abstracts run to about 270 words, above typical AAMAS abstracts. The five-metric
  list with R1/MET/BIF values adds length without a comparison for those metrics (only MemView's values are
  given). The stopping rule (C4) and the call count (C5) are slightly imprecise. *Fix:* report EM and F1 in the
  abstract, move the other metrics to the results table, and say "requests". Class: `writing`.

## Questions

1. Were any v11 design choices (table title, Null rule, prompt style) validated on dev before the test run? If
   yes, the dev numbers resolve W1.
2. Does debate with the same same-table memory still trail MemView? If MemView's margin over memory-equipped
   debate is also about 1 EM, the V2 framing is confirmed; if debate + memory matches MemView, the "MemView"
   system name is hard to justify.
3. What is the standard deviation of MemView and agent-A-only EM over three runs? If the agent gain exceeds two
   standard deviations, W5 disappears.
4. Is the Open-ViTabQA test set free of near-duplicate questions from the same table's training split? The
   100% EM (lenient variant) on the 46 test questions with Jaccard ≥ 0.8 to a training question suggests some
   near-duplicates;
   reporting how many would pre-empt a leakage concern.

## Limitations

The abstracts note that other-table memory is only a proxy for unseen tables. Missing and needed in the paper:
single dataset and single backbone; dependence on labelled training questions for each table; the test-set
iteration in W1; the verbalization step in W6.

## Scores (default template; AAMAS main track assumed)

- Soundness: 2/4. The headline number was selected with test feedback (W1), and the key comparison is single-run
  (W5).
- Presentation: 3/4. Both abstracts are clear and honest; they are too long and slightly imprecise (W7).
- Contribution: 2/4. The empirical finding (memory ≫ agents) is useful, but W2 limits novelty for an agents
  venue.
- Overall: **V1 4/10, V2 5/10**
- Confidence: 3/5. I know the underlying code and results, but no full paper exists to check.

## Justification of score

W1 undermines the headline 81.85, which caps the overall score at 5. V2 reaches that cap because its framing
matches the evidence; V1 stays at 4 because it presents as a system contribution whose system-specific part adds
about 1 EM (W2, W3). Disclosing or fixing W1, adding the memory-matched baselines (W3) and three-run variance
(W5) would move V2 to about 6.

## If I were you: fix list

### Must fix before submission

- `writing`: Disclose that v11 was chosen after a test run (W1), or report dev numbers that justify each change.
- `writing`: Add agent A alone with the same memory (80.85 EM) to the abstract's comparisons (W3).
- `writing`: Scope V2's title and conclusion to this dataset and model size (W2); drop "controlled".
- `writing`: Write "reported" for the human and Gemini numbers and note the verbalization step (W6).
- `new experiment`: Three runs of MemView, agent A alone and few-shot (W5).

### Should fix if time permits

- `new experiment`: Multi-agent debate with the same same-table memory (W3, Q2).
- `writing`: Cut the abstract to about 200 words, keeping EM and F1 (W7).
- `writing`: Move CoAgt and Chain-of-Table out of the abstract, or state their setup (W4).
- `new experiment`: A second backbone (for example another model under 10B) on the same pipeline (W2).

### Rebuttal prep

- **"The gain is just retrieval of similar examples."** Concede; point to the ablation grid as the contribution
  and to the other-table result (79.03) as evidence that retrieval helps beyond same-table overlap.
- **"The agent gains are within noise."** Concede if the three runs confirm it; the paper's claim is exactly that
  agents add little at this scale, which is a useful negative result for multi-agent design.
- **"Weak reproductions of CoAgt and Chain-of-Table."** Explain the original-prompt policy, and point to
  memory-free debate and few-shot as the fair, same-frame baselines.

**Predicted modal reaction:** scores around 4–5, with the main objection that the improvement comes from
retrieved same-table demonstrations while the multi-agent part is within noise, and that the work fits an NLP
venue better than AAMAS.
