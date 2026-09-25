# Open-ViTabQA: practitioner sweep + second-backbone shortlist
Verified live 2026-09-18. Every number below has a URL.

## PART A — practitioner guidance (verified, not from memory)

### Multi-agent: the verdict is "don't", for THIS pipeline
- Cognition, Walden Yan, 2025-06-12, https://cognition.com/blog/dont-build-multi-agents
  (note: cognition.ai 301-redirects to cognition.com). Two principles verbatim:
  P1 "Share context, and share full agent traces, not just individual messages"
  P2 "Actions carry implicit decisions, and conflicting decisions carry bad results"
  Recommends single-threaded linear agents; history-compression model only for very long tasks.
- Anthropic, https://www.anthropic.com/engineering/building-effective-agents
  "finding the simplest solution possible, and only increasing complexity when needed"
  "For many applications ... optimizing single LLM calls with retrieval and in-context examples is usually enough"
  workflows = "task can be easily and cleanly decomposed into fixed subtasks"; agents = open-ended, unpredictable step count.
  "consider adding complexity _only_ when it demonstrably improves outcomes"
- Anthropic, https://www.anthropic.com/engineering/multi-agent-research-system
  "agents typically use about 4x more tokens than chat interactions, and multi-agent systems use about 15x more tokens than chats"
  90.2% improvement over single agent — but ONLY on breadth-first research. Explicitly: "most coding tasks
  involve fewer truly parallelizable tasks than research"; poor fit when agents need shared context / heavy interdependency.
- HF smolagents, 2024-12-31, https://huggingface.co/blog/smolagents — "If the pre-determined workflow falls
  short too often, that means you need more flexibility"; deterministic workflow is "100% reliable with no risk of error";
  code-agents > JSON tool-calling agents for composability.

APPLIED: Open-ViTabQA is fixed-stage (serialize table -> classify answerable/agg-type -> answer -> verify).
That is exactly Anthropic's "cleanly decomposed into fixed subtasks" = **workflow, not multi-agent**.
Do not spend the 15x token multiplier. If a reviewer asks "why not multi-agent", cite these three.

### Structured / constrained decoding (this is the load-bearing part for routing on predicted labels)
- vLLM docs, https://docs.vllm.ai/en/latest/features/structured_outputs.html
  Backends: xgrammar + guidance, `auto` picks. Five types: **choice, regex, json, grammar, structural_tag**.
  `guided_json`/`guided_regex` REMOVED in v0.12.0 -> use `structured_outputs`.
  Reasoning models need `--structured-outputs-config.enable_in_reasoning=True` to constrain inside thinking.
- vLLM blog, 2025-01-14, https://vllm.ai/blog/2025-01-14-struct-decode-intro
  XGrammar (pushdown automaton) gives "up to 5x improvement in time per output token (TPOT) under load" vs Outlines.
  Gaps: GBNF only, weak on regex patterns / numeric ranges inside JSON.
- SGLang/LMSYS, 2024-02-05, https://lmsys.org/blog/2024-02-05-compressed-fsm/ (exists)
  Compressed FSM + jump-forward decoding: "reduce the latency by up to 2x and boost throughput by up to 2.5x".
  Concrete rule: use "a comprehensive regular expression to guide the entire decoding process, rather than
  employing multiple concatenated regular expressions". Re-tokenization overhead ~4%.
  (Checked lmsys.org/blog through Sep 2026 — 2026 posts are all serving/infra/day-0 support; no newer structured-output post.)

- HF blog, 2026-09-03, https://huggingface.co/blog/grpo-with-trl-ifstruct  (small-model structured output)
  LFM2.5-350M on IFStruct: 22.6 -> 29.7 overall after GRPO; **JSON format compliance 18.0 -> 31.9 (+13.9)**;
  bare-list format 16.6 -> 29.7. ~500 samples, 100 steps, free-tier Colab GPU. Still below Qwen3.5-2B's 33.15.
  TAKEAWAY: untuned small models are genuinely bad at emitting schema-valid JSON from prompting alone. Either
  grammar-constrain it (cheap, deterministic, do this) or spend a GRPO run (only if you cannot constrain).

APPLIED at 8B:
1. For the ROUTER stage do NOT ask for JSON at all — use `choice` (enum) constrained decoding. One token of
   real decision, zero parse failures, no brace/quote drift. This is the single highest-leverage trick here.
2. For the ANSWER stage use one flat JSON schema with `structured_outputs`/`json` (not nested, no optional
   unions) — one regex/grammar for the whole object, per the SGLang guidance.
3. Model `unanswerable` as an enum field inside that one schema, never as a separate call.
4. If you serve locally, vLLM + xgrammar gives you identical grammar enforcement on BOTH backbones — which is
   what makes the fairness claim in Part C actually true.
5. Do NOT rely on prompt-only JSON at 8B (see the GRPO result above). Grammar constraints are the cheap fix;
   fine-tuning for format is the expensive one.

### Reasoning effort at small scale
- Raschka, 2026-07-18, https://magazine.sebastianraschka.com/p/controlling-reasoning-effort-in-llms
  Qwen3's "Thinking Mode Fusion" SFT stage is what makes `enable_thinking` work. "a smaller model at a higher
  reasoning effort can sometimes reach a similar score as a larger model at a lower reasoning effort", but
  "Increasing reasoning budgets can become uneconomical at some point"; gains saturate on non-math/code tasks,
  and small models may lack the sophistication to use long reasoning. Kimi finding: a FIXED token budget can make
  a reasoning model "overfit to short solutions".
  APPLIED: table lookup/aggregation is closer to math than to open QA, so thinking may help — but you must
  report it as a controlled axis, not silently leave it on.
- Raschka, 2026-01-24, https://magazine.sebastianraschka.com/p/categories-of-inference-time-scaling
  (paywalled past intro) — categories: CoT, self-consistency, best-of-N, rejection sampling w/ verifier,
  self-refinement, search. Intro reports his own test going ~15% -> ~52%.
- Raschka archive verified live: https://magazine.sebastianraschka.com/archive — relevant: "Components of A
  Coding Agent" (2026-04-04), "Using Local Coding Agents" (2026-06-27), "Understanding the 4 Main Approaches to
  LLM Evaluation (From Scratch)" (2025-10-05), "LLM Research Papers: The 2026 List (Jan-May)" (2026-06-06).
  NOT FOUND: any Raschka post specifically on multi-agent systems. Do not cite him for that.

---

## PART B — sub-10B backbone comparison

Vietnamese evidence = SEA-HELM leaderboard, https://leaderboard.sea-lion.ai (data stamp Sep 18, 2026, 58
open-weight models, 2000 bootstraps, 95% CI). VI column pulled from the full table with all 58 selected.

SEA-HELM Vietnamese (VI) for every sub-10B model on the board:
  Qwen 3.5 9B                     SEA 69.13 | VI 71.93 [-1.51,+1.49] -> [70.42, 73.42]
  Gemma 4 (E4B) 8B                SEA 66.30 | VI 67.14 [-1.78,+1.85] -> [65.36, 68.99]
  Qwen 3.5 4B                     SEA 63.82 | VI 68.97
  Qwen 3 8B  (current backbone)   SEA 60.33 | VI 68.17 [-1.63,+1.63] -> [66.54, 69.80]
  SEA-LION v4.5 (Gemma E2B) 5B    SEA 59.23 | VI 61.95
  Gemma 4 (E2B) 5B                SEA 58.82 | VI 61.19
  Qwen 3 VL 8B                    SEA 56.60 | VI 66.79
  SEA-LION v3 (Gemma 2) 9B        SEA 56.52 | VI 63.82
  SEA-LION v4 (Qwen VL) 8B        SEA 56.41 | VI 65.87
  SEA-LION v3.5 R (Llama) 8B      SEA 54.85 | VI 60.66
  Apertus 1.5 8B                  SEA 54.16 | VI 60.26
  SEA-LION v3 (Llama) 8B          SEA 48.68 | VI 57.20
  Gemma 3 4B                      SEA 47.84 | VI 50.72
  (reference, >10B: Gemma 3 12B   SEA 62.44 | VI 66.40 [-2.04,+2.02] -> [64.36, 68.42])
  Llama 3.1 8B                    SEA 37.20 | VI 44.63 [-2.01,+2.03] -> [42.62, 46.66]
  SEA-LION v4 (Apertus) 8B        SEA 36.86 | VI 39.96
  Apertus 8B                      SEA 27.54 | VI 34.46

Tokenizer efficiency — MEASURED, not quoted. Same Vietnamese prompt (markdown table of VN provinces +
question + JSON instruction) vs its English translation, via transformers AutoTokenizer:
  Qwen/Qwen3.5-9B                      vi=214  en=191  vi/en=1.12  vocab 248,044
  google/gemma-4-E4B-it                vi=221  en=190  vi/en=1.16  vocab 262,144  (measured via `tokenizers`)
  google/gemma-4-E2B-it                vi=221  en=190  vi/en=1.16  vocab 262,144
  aisingapore/Gemma-SEA-LION-v3-9B-IT  vi=219  en=191  vi/en=1.15  vocab 256,000  (= Gemma-2 tokenizer)
  unsloth/gemma-3-12b-it               vi=222  en=191  vi/en=1.16  vocab 262,144  (= Gemma-3 tokenizer)
  aisingapore/Llama-SEA-LION-v3-8B-IT  vi=189  en=159  vi/en=1.19  vocab 128,000
  Qwen/Qwen3-8B                        vi=225  en=187  vi/en=1.20  vocab 151,643
  SeaLLMs/SeaLLMs-v3-7B-Chat           vi=225  en=187  vi/en=1.20  vocab 151,643  <-- byte-identical to Qwen3-8B
  mistralai/Ministral-8B-Instruct-2410 vi=224  en=185  vi/en=1.21  vocab 131,072
  aisingapore/Apertus-SEA-LION-v4-8B-IT vi=224 en=185  vi/en=1.21  vocab 131,072
  ibm-granite/granite-4.2-8b           vi=266  en=166  vi/en=1.60  vocab 100,352  <-- 18% more VI tokens than Qwen3
(gemma-2 official repo is gated -> Gemma-2 tokenizer measured via the AISG mirror. google/gemma-4-* errors under
transformers 4.57.1 with `'list' object has no attribute 'keys'` -- a config-format lag, NOT gating -- so it was
measured by loading tokenizer.json directly with the `tokenizers` library. Gemma 4 uses 221 VI tokens vs Qwen3-8B's
225: **1.8% fewer**, not 3%.)
Spread across viable candidates is <6% — tokenizer cost is NOT a deciding factor here. Granite is the only
real outlier and it is out on other grounds anyway.

Per-candidate cards (OpenRouter figures from the live https://openrouter.ai/api/v1/models JSON):

| Model | HF | Params / ctx / license | Vietnamese evidence | Reasoning | JSON / tool-use | OpenRouter | VI tokenizer |
|---|---|---|---|---|---|---|---|
| **Qwen3-8B** (incumbent) | Qwen/Qwen3-8B | 8.2B (6.95B non-emb) / 32k native, 131k YaRN / Apache-2.0 | SEA-HELM VI 68.17 | hybrid `enable_thinking`; Thinking-Mode-Fusion SFT | tools+tool_choice yes; **`response_format` only — NO `structured_outputs` on OpenRouter** | `qwen/qwen3-8b` $0.117 / $0.455 per M, 131k | 1.20 |
| **Qwen3.5-9B** | Qwen/Qwen3.5-9B | 9B / 262k native (1.01M ext) / Apache-2.0, Feb 2026 | **SEA-HELM VI 71.93 (best sub-10B)** | thinking ON by default, `enable_thinking:false` | tools + `structured_outputs` (json_schema) on OR | `qwen/qwen3.5-9b` $0.10 / $0.15 per M, 262k | **1.12 (best)** |
| **Gemma 4 E4B** | google/gemma-4-E4B-it | 8B w/ embeddings, 4.5B effective / **128k** / **Apache-2.0** | SEA-HELM VI **67.14 [65.36, 68.99]** vs Qwen3-8B **68.17 [66.54, 69.80]** -> CIs overlap | `enable_thinking=True`, `<\|think\|>` tokens; MMLU-Pro 69.4, GPQA-D 58.6, AIME-2026 42.5, LiveCodeBench-v6 52.0, BBEH 33.1 | **tool-use: Tau2 42.2** (agentic). **NO published IFEval, BFCL or JSON-compliance number for E4B** -- see note below | **NOT on OpenRouter** (only gemma-4-26b-a4b-it and gemma-4-31b-it) | ~1.16 (Gemma tok.) |
| Llama-3.1-8B-Instruct | meta-llama/... | 8B / 131k / Llama-3.1 Community | **SEA-HELM VI 44.63 — 23.5 pts below Qwen3-8B** | no thinking mode | `structured_outputs` on OR | `meta-llama/llama-3.1-8b-instruct` $0.05 / $0.08 | 1.19 |
| Gemma 2 9B / Gemma 3 | google/gemma-2-9b-it | 9B / **8k ctx** ; Gemma 3 ladder is 1/4/12/27B — **there is no Gemma 3 9B** | VMLU 59.04 (gemma-2-9b-it, 2024) ; Gemma 3 4B VI 50.72 | none | — | gemma-2-9b NOT on OR; gemma-3-4b-it $0.05/$0.10; gemma-3-12b-it is 12B (>10B) | 1.15-1.16 |
| SEA-LION v4 (Apertus) 8B | aisingapore/Apertus-SEA-LION-v4-8B-IT | 8B / 65k / MIT, updated 2026-02-05 | **SEA-HELM VI 39.96 — worse than Llama-3.1-8B** | none | none published | not on OR | 1.21 |
| SEA-LION v3 (Gemma2) 9B | aisingapore/Gemma-SEA-LION-v3-9B-IT | 9B / **8192 ctx** / Gemma license, 2025-04-14 | SEA-HELM VI 63.82 | none | SEA-IFEval only | not on OR | 1.15 |
| SEA-LION v3 (Llama) 8B | aisingapore/Llama-SEA-LION-v3-8B-IT | 8B / 128k / Llama-3.1 Community, 2025-04-14; card says superseded by Qwen-SEA-LION-v4.5-27B-IT | SEA-HELM VI 57.20 | none | SEA-IFEval | not on OR | 1.19 |
| SeaLLMs-v3-7B-Chat | SeaLLMs/SeaLLMs-v3-7B-Chat | 7B / seallms (non-commercial) license | VMLU-style M3Exam VI 0.649, MGSM 71.2 (vendor card) | none | none | not on OR | 1.20, **tokenizer byte-identical to Qwen — it IS a Qwen2 derivative** |
| Ministral-8B-2512 | mistralai/... | 8B / 262k | **no SEA-HELM entry** | none advertised | `structured_outputs` on OR | `mistralai/ministral-8b-2512` $0.15 / $0.15 | 1.21 |
| granite-4.2-8b | ibm-granite/granite-4.2-8b | 8B / 131k | **no SEA-HELM entry** | `reasoning_effort` on OR | `structured_outputs` on OR | $0.06 / $0.25 | 1.60 (worst) |
| PhoGPT-4B-Chat | vinai/PhoGPT-4B-Chat | 3.7B / 8k / BSD-3 / **Nov 2023** | VMLU 24.01 (PhoGPT-7B5-Instruct) | none | none | no | — |
| Vistral-7B-Chat | Viet-Mistral/Vistral-7B-Chat | 7B Mistral-7B CPT / AFL-3.0 / **2023** | VMLU 50.07 (self-reported) | none | none | no | — |
| VinaLLaMA-7B-Chat | vilm/vinallama-7b-chat | 7B / llama2 license / **Dec 2023** | arXiv 2312.11011 | none | none | no | — |
| Arcee-VyLinh | arcee-ai/Arcee-VyLinh | **3B, base = Qwen2.5-3B** / 32k / Apache-2.0 | m-ArenaHard-vi, LLM-judge, no numbers on card | none | none | no | — |

### Things memory would have got wrong (all verified live)
1. **SEA-LION v4 is current, but it has no good sub-10B Vietnamese model.** AISG's line is now v4.5 / v4.8
   (Qwen-27B, Nemotron-30B/120B MoE, Gemma-E2B-5B). The only sub-10B v4 dense model,
   `aisingapore/Apertus-SEA-LION-v4-8B-IT`, scores **VI 39.96** — SEA branding did NOT buy Vietnamese ability
   here, because the Apertus-8B base is itself at VI 34.46. v3 (Llama 8B / Gemma2 9B) is stale (Apr 2025) and
   its own card points users to a 27B successor. **No SEA-LION belongs on the shortlist.**
2. **There is no Gemma 3 9B.** Gemma 3 = 1B/4B/12B/27B. The sub-10B Gemma options are Gemma 2 9B (8k context —
   disqualifying for serialized tables) or Gemma 3 4B (VI 50.72). Gemma 4 E4B (8B) is the real sub-10B Gemma.
3. **Gemma 4 is Apache-2.0** (frontmatter of google/gemma-4-E4B-it), not the Gemma custom license. This removes
   the usual licensing objection, and is corroborated by AISG shipping a Gemma-4 derivative under MIT.
4. **SeaLLMs v3's tokenizer is byte-identical to Qwen3-8B's** (vocab 151,643, identical token counts on both my
   probes) — it is a Qwen2 derivative. Picking it as "a different backbone" would be indefensible to the reviewer.
5. **Qwen3-8B on OpenRouter does not expose `structured_outputs`.** Its `supported_parameters` list is
   `[... response_format, seed, stop, temperature, tool_choice, tools, top_k, top_p]` — no `structured_outputs`,
   no `logit_bias`, no `logprobs`. Every other candidate (qwen3.5-9b, gemma-4-26b, llama-3.1-8b, ministral-8b,
   granite-4.2-8b, gemma-3-12b) DOES list it. So today your router is running on json-object-mode at best, not
   schema-enforced decoding. OpenRouter docs: "Support is determined per endpoint, not just per model ... only
   some of those providers may support structured outputs", some providers "treat it as a strong hint, so exact
   compliance is not guaranteed" (https://openrouter.ai/docs/features/structured-outputs). Fix: set
   `require_parameters: true` in provider preferences, or self-host.
6. **Qwen3-8B is still the hybrid checkpoint**, not a 2507-style Instruct/Thinking split (the split exists for
   30B-A3B and 235B-A22B on OpenRouter, not for 8B). So `enable_thinking` / OpenRouter's `reasoning` param is a
   real switch you control — and therefore a confound you must pin.

### Budget: not a constraint. Stop optimizing it.
992 questions x ~1,200 input tokens (merged-cell table + prompt) ~= 1.19M input.
- Non-thinking (~100 out-tok/item, 0.1M out): Qwen3-8B ~$0.19/run; Qwen3.5-9B ~$0.13/run.
- Thinking (~1,000 out-tok/item, ~1.0M out): Qwen3-8B ~$0.60/run; Qwen3.5-9B ~$0.27/run.
Your $2 ceiling is ~$1.55 per M blended tokens; every candidate is 3-30x under it. Choose on science, not price.

---

## PART C — recommendation

**Add `google/gemma-4-E4B-it` as the second backbone. Serve it yourself with vLLM + xgrammar.**

SERVING VERIFIED: vLLM's supported-models list includes `Gemma4ForConditionalGeneration` and names the
`gemma-4-E2B` / `gemma-4-E4B` variants explicitly (https://docs.vllm.ai/en/latest/models/supported_models.html).
So the "same engine, same xgrammar grammar on both backbones" plan is executable, not aspirational.
CAVEATS YOU MUST CHECK BEFORE COMMITTING:
  - Your machine is Windows 11 Home. vLLM needs Linux/WSL2 + an NVIDIA GPU. At 4.5B effective params bf16 fits
    in ~16GB, but confirm you have that GPU. If not, this becomes a rented-GPU task, not a laptop task.
  - transformers 4.57.1 in your env cannot load the Gemma-4 config (`'list' object has no attribute 'keys'`).
    You will need a newer transformers + a vLLM version that actually ships the Gemma 4 code path. Verify with
    a 10-minute smoke test (load + one constrained generation) BEFORE building the experiment around it.
  - vLLM's notes flag the earlier Gemma-3n E-variants as "not yet fully optimized" (shared KV caching, version
    pinning). Expect throughput, not correctness, issues; budget wall-clock accordingly.

Why it, and not the alternatives:
- **Vietnamese parity, not a handicap.** SEA-HELM VI 67.14 vs Qwen3-8B's 68.17 — a 1.0-point gap inside
  overlapping CIs. A generalization experiment needs a backbone that is *comparably capable*; if the second
  model is much worse at Vietnamese, every delta is attributable to the model, not to your pipeline. This is
  precisely why **Llama-3.1-8B (VI 44.63) is the wrong pick** even though it is the obvious, cheap, famous one.
- **Maximum training independence.** Different lab, different pretraining corpus, different tokenizer
  (262k Gemma SentencePiece vs 151k Qwen BPE), different architecture family. Qwen3.5-9B would be a *version*
  control, not a *generalization* control — same lab, same tokenizer lineage, near-certainly overlapping data.
  A reviewer who asked for a second backbone to prove generalization will not accept another Qwen.
  Same objection kills SeaLLMs v3 (Qwen2 base) and Arcee-VyLinh (Qwen2.5-3B base).
- **Constraint-compliant and license-clean.** 8B total params (4.5B effective) < 10B; Apache-2.0; 128k context,
  which comfortably holds serialized merged-cell tables (Gemma 2 9B's 8k does not).
- **Matched reasoning axis.** It has an explicit `enable_thinking` switch, so "thinking off on both" is
  actually achievable. Neither Llama-3.1-8B nor any SEA-LION gives you that.
- **Self-hosting is a feature, not a cost.** It removes OpenRouter's per-provider structured-output variance
  (see finding #5), and at 4.5B effective params it fits a single 16GB GPU. You can then run *both* backbones
  under vLLM with the identical xgrammar grammar.
  NOTE THE CONSEQUENCE: adopting this recommendation moves **both** backbones to local vLLM. Qwen3-8B is
  Apache-2.0 and 8.2B, so that is trivially possible — and it is actually the stronger setup, because it fixes
  finding #5 for the incumbent too. The OpenRouter price table above then becomes a sanity check / a cheap
  reproducibility path for readers, not your cost model. Say so in the paper.
- **The one genuinely weak cell, stated plainly.** Google publishes no IFEval, BFCL or JSON-compliance number
  for E4B. What exists is Tau2 42.2 (agentic tool-use) plus MMMLU 76.6 multilingual. Why this does not sink the
  pick: under `choice`-constrained routing and one xgrammar-enforced flat schema, native JSON reliability is
  largely moot — schema violations are impossible by construction, and you should report the parse-failure rate
  (expected 0) as evidence. If you instead run prompt-only JSON, this gap becomes a real risk and the HF
  GRPO/IFStruct result above says you will pay for it.

FALLBACK, IN ORDER, IF THE SMOKE TEST FAILS:
  (a) `google/gemma-3-12b-it` — VI 66.40 [64.36, 68.42], i.e. statistically indistinguishable from Gemma 4 E4B
      and from Qwen3-8B; on OpenRouter at $0.05/$0.15 per M WITH `structured_outputs`; Gemini tokenizer; a
      completely mature, definitely-servable code path. The cost: 11.95B params, which **breaks your stated
      <10B constraint by ~20%**. That is a trade for you to make, not for me — if the <10B rule came from the
      reviewer it is binding; if it came from your own budget framing, note that the budget is not binding
      (see above) and 12B is the scientifically cleaner choice.
  (b) `qwen/qwen3.5-9b` — see below; keeps <10B but gives up lineage independence.
  Do NOT fall back to Llama-3.1-8B, SEA-LION, or Gemma 2 9B; each is ruled out above on hard evidence.

Second choice if you must stay API-only: `qwen/qwen3.5-9b` ($0.10/$0.15, 262k ctx, VI 71.93, and unlike
qwen3-8b it does expose `structured_outputs`). Report it honestly as a **capability/version ablation**, not as
independent-backbone evidence. Optional third: `meta-llama/llama-3.1-8b-instruct` as a deliberate
low-Vietnamese-ability stress point to show the pipeline degrades gracefully — cheap ($0.05/$0.08) and it makes
the "Vietnamese ability is the bottleneck, not the pipeline" argument quantitatively.

**What makes the comparison fair (write this into the paper as a protocol box):**
1. Identical table serialization (same merged-cell expansion, same markdown/HTML choice) — serialize once,
   cache to disk, feed the same byte string to both models.
2. Identical prompts, identical few-shot exemplars, identical order. No per-model prompt tuning. If you tune,
   tune on a dev split for both and report both tuned.
3. **Thinking disabled on both** (`enable_thinking=False` / `reasoning: {exclude/effort:none}`) for the headline
   table; if you also report thinking-on, report it for both, and report thinking-token counts.
4. Identical decoding: same temperature, top_p, top_k, seed, and the same `max_tokens`. Do NOT use each
   vendor's "recommended" sampling params — that is a confound. Fix one setting; note the deviation from
   Qwen's recommended (T=0.7/top_p=0.8 non-thinking) in a footnote.
5. Identical constraint mechanism: the same JSON schema compiled by the same xgrammar backend in the same vLLM
   version, plus `choice`-constrained decoding for the routing label. Not "json mode on one and a regex parser
   on the other."
6. Same token budget, measured in *tokens* not characters — and report input tokens per model. Measured on a
   representative VN table prompt: Gemma 4 = 221 tokens, Qwen3-8B = 225 (**1.8% fewer for Gemma**). Small, but
   quote it rather than assuming parity.
7. One evaluator, run once over both output sets: same normalization (Vietnamese diacritics, number/date
   formats, thousands separators), same EM/F1 implementation, same unanswerable rule.
8. **Pin the unanswerable handling explicitly** — 10% of the 992 are unanswerable, so a model that abstains
   differently can swing the headline by several points. Report answerable-only accuracy, unanswerable
   precision/recall, and the abstention rate for both backbones separately.
9. Report parse-failure / schema-violation rate per backbone as a first-class number. With grammar enforcement
   it should be 0; if it isn't, the routing comparison is invalid.
10. Same number of runs and seeds; report variance, not a single point estimate.
