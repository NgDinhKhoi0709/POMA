// ============================================================
// POMA — supervisor progress report (English)
// Content source: slide/context/*.md (do not invent figures here)
// Build: python -m typst compile progress-report.typ progress-report.pdf
// ============================================================

#import "packages/ens-rennes-presentation/theme.typ": *

#let highlight-block = tblock.with(color: rgb("#2563eb")) // setup / context
#let result-block = tblock.with(color: rgb("#059669")) // genuinely positive result
#let warning-block = tblock.with(color: rgb("#dc2626")) // limitation / caution

#show: ens-rennes-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Parallel Multi-Agent Orchestration for Vietnamese Table QA],
    subtitle: [Progress report: current status and approaches tested],
    mini-title: [Vietnamese Table QA],
    authors: [Nguyen Dinh Khoi],
    date: datetime(year: 2026, month: 9, day: 22),
  ),
  section-style: "named subsection",
  department: "info",
  display-dpt: false,
  named-index: true,
)

#title-slide(additional-content: [
  #v(0.6em)
  #text(size: 0.85em)[Advisor: Dang Van Thin]
  #v(2em)
])

// ============================================================
= Outline
// ============================================================

#slide(title: [Outline])[
  #v(1fr)
  #enum(
    spacing: 1.1em,
    [*Problem and data* — what Open-ViTabQA actually contains],
    [*System* — the POMA pipeline as it runs today],
    [*Status* — published figures versus audited results],
    [*Experiments* — eight directions measured, plus the separate GaP-TQA system],
    [*Lessons and plan* — what the measurements imply, and what comes next],
  )
  #v(1fr)
]

// ============================================================
= Problem
// ============================================================

== Task

#slide(title: [Vietnamese Table QA on Open-ViTabQA])[
  #highlight-block(title: [Task])[
    Answer Vietnamese questions over semi-structured Wikipedia tables.
    Unanswerable questions must return the exact string `Null`.
  ]
  #v(0.3em)
  #text(size: 0.84em)[
    #grid(
      columns: (1fr, 1fr),
      column-gutter: 1.2em,
      [
        *Three stated challenges*
        - Multilevel headers and merged cells
        - Multistep reasoning over several rows or columns
        - Deciding answerability at all
      ],
      [
        *Project constraint*
        - Open backbone under 10B parameters
        - No fine-tuning of the QA model
        - Only prompts and pipeline structure may change
      ],
    )
  ]
]

== Data

#slide(title: [What the data actually contains])[
  #v(0.3em)
  #text(size: 0.95em)[
    *Measured from repository files, not copied from the paper* #h(0.4em)
  ]
  #v(0.7em)
  #align(center)[
    #text(size: 0.9em)[
      #table(
        columns: (auto, auto, 1fr),
        inset: 6.2pt,
        align: (left, right, left),
        stroke: 0.4pt + luma(180),
        fill: (x, y) => if y == 0 { rgb("#2563eb").lighten(82%) } else if calc.odd(y) { luma(246) } else { white },
        table.header([*Measure*], [*Value*], [*Why it matters*]),
        [QA pairs (train / dev / test)], [7,928 / 991 / 992], [],
        [Source tables], [329], [],
        [Unanswerable (test)], [45/992 = 4.5%], [A rare class; false abstentions are costly],
        [Table length p50 / p90], [647 / 2,097 tokens], [Tables are small — long context is not the bottleneck],
        [Tables over 2,000 tokens], [15.6% of questions], [...but they hold *54.8%* of all table tokens],
        [Hint labels per question], [mean 1.10], [*91%* have one label, so one specialist runs],
        [Answers copied from one cell], [42.3%], [Mostly locating a cell, not computing],
      )
    ]
  ]
]

// ============================================================
= System
// ============================================================

== Pipeline

#slide(title: [POMA as it runs today])[
  #v(0.2em)
  #align(center)[
    #image("assets/pipeline.png", height: 76%)
  ]
  #v(0.3em)
  #text(size: 0.78em)[
    Preprocessing (HTML $->$ logical grid $->$ Flatten V1) $->$ hint predictor
    $->$ question refiner $->$ deterministic 1:1 router $->$ ten parallel
    specialists $->$ answer normalization. No fine-tuning at any stage.
  ]
]

// ============================================================
= Status
// ============================================================

== Audit

#slide(title: [Audit])[
  #text(size: 0.74em)[
    #table(
      columns: (auto, auto, auto, 1fr),
      inset: 4.2pt,
      align: (right, right, center, left),
      stroke: 0.4pt + luma(180),
      fill: (x, y) => if y == 0 { rgb("#2563eb").lighten(82%) } else if calc.odd(y) { luma(246) } else { white },
      table.header([*EM*], [*BIF*], [*n*], [*What it measures*]),
      [74.90], [—], [992], [POMA `all` — oracle best-of-K (mean K 3.44, max K 80)],
      [66.63], [75.00], [992], [POMA-first],
      [67.34], [73.83], [992], [Few-shot raw],
      [68.45], [*76.43*], [992], [POMA + GSA finalizer],
      [*70.16*], [76.10], [992], [*Few-shot + GSA — the single-call baseline wins*],
    )
  ]
  #v(0.3em)
  #text(size: 0.82em)[
    #warning-block(title: [Key comparison])[
      POMA+GSA − FS+GSA = *−1.71 EM*, paired 95% CI [−3.93, +0.50];
      53 wins / 70 losses / 869 ties. Both branches were rerun together, so
      this is the strongest comparison available. BIF leans the other way
      but agrees there is no winner: +0.33, paired 95% CI [−0.98, +1.63].
    ]
  ]
]

== Attribution

#slide(title: [Where the reported gain actually comes from])[
  #text(size: 0.78em)[
    #table(
      columns: (1fr, auto, auto, auto, auto),
      inset: 4.5pt,
      align: (left, right, right, right, right),
      stroke: 0.4pt + luma(180),
      table.header([], [*EM*], [*F1*], [*R1*], [*MET*]),
      [Few-shot (draft Table 2)], [67.14], [78.64], [74.18], [72.30],
      [POMA without Answer Normalization], [68.41], [81.31], [78.98], [75.60],
      [POMA (draft Table 6)], [80.24], [88.23], [86.07], [84.50],
      [*Share of gain from normalization*], [*90%*], [72%], [60%], [73%],
    )
  ]
  #v(0.45em)
  #text(size: 0.84em)[
    - Answer normalization is *orthogonal to multi-agent design* and applies equally to any baseline.
    - Baselines were scored on one string; POMA was scored best-of-K. Adding candidates to a best-of-K set can never lower its score.
    - The draft's own baselines contradict its premise: task decomposition (59.38) and chain-of-thought (59.17) both score *below* zero-shot (62.40).
  ]
  #v(0.35em)
  #text(size: 0.82em)[
    #warning-block(title: [Unresolved arithmetic])[
      §5.6 says normalization flips 177/992 answers, which implies 62.40 without
      it — not the 68.41 in Table 6. And 68.41% is not k/992 for any k.
      These are draft figures; no BIF exists for them.
    ]
  ]
]

== Metric

#slide(title: [BIF: a semantic metric, and the ViNLI model behind it])[
  #text(size: 0.78em)[
    #highlight-block(title: [Definition (following Open-ViTabQA)])[
      $"BIF" = alpha dot "PhoBERTScore-F1"("ref", "pred") + (1 - alpha) dot P_"NLI" ("entailment" | "ref" -> "pred"), quad alpha = 0.5$
      #v(0.1em)
      PhoBERT-large (layer 17) scores meaning overlap; a four-label ViNLI classifier
      scores whether the prediction is *entailed by* the reference. EM and
      character F1 give zero credit to `1709` versus gold `Năm 1709`; BIF does not.
    ]
  ]
  #v(0.2em)
  #grid(
    columns: (1.05fr, 1fr),
    column-gutter: 1.2em,
    align: (left + top, left + top),
    text(size: 0.66em)[
      *I fine-tuned the NLI model myself* — XLM-R Large, four labels
      #v(0.15em)
      #table(
        columns: (1fr, auto, auto),
        inset: 4pt,
        align: (left, right, right),
        stroke: 0.4pt + luma(180),
        fill: (x, y) => if y == 0 { rgb("#2563eb").lighten(82%) } else { white },
        table.header([*ViNLI test (n=2,991)*], [*Acc*], [*Macro-F1*]),
        [Paper (COLING 2022, Table 6)], [85.99], [86.10],
        [*Mine* (best dev epoch 3)], [*85.42*], [*85.49*],
        [Difference], [−0.57], [−0.61],
      )
      #v(0.15em)
      Paper's recipe: Adam, lr 1e-5, batch 16, 10 epochs, max length 128.
      Split sizes 24,376 / 3,009 / 2,991 match the paper. Dev: 85.24 / 85.18.
      Per-label test F1: entailment (used by BIF) 83.61, contradiction 79.89,
      neutral 80.27, other 98.20.
    ],
    text(size: 0.66em)[
      #v(1.6em)
      #warning-block(title: [Limits])[
        Data from a third-party Hugging Face mirror, not an author release:
        a *replication*, not an exact reproduction. BIF is secondary; most
        BIF differences have no paired interval, so conclusions rest on EM.
      ]
    ],
  )
]

// ============================================================
= Experiments
// ============================================================

== Overview

#slide(title: [Everything that has been run])[
  #text(size: 0.5em)[
    #table(
      columns: (auto, 1fr, auto, auto, auto, auto, 1.05fr),
      inset: 3pt,
      align: (center, left, right, center, left, right, left),
      stroke: 0.4pt + luma(185),
      fill: (x, y) => if y == 0 { rgb("#2563eb").lighten(82%) } else if calc.odd(y) { luma(246) } else { white },
      table.header([*ID*], [*Direction*], [*n*], [*Parser*], [*EM effect (paired 95% CI)*], [*BIF effect*], [*Conclusion*]),
      [D01], [Fair scorer and provenance], [992], [legacy], [POMA − FS: *−1.71* [−3.93, +0.50]], [+0.33 [−0.98, +1.63]], [No evidence POMA beats FS],
      [D02], [GSA finalizer (one answer)], [992], [legacy], [POMA 66.63→68.45; FS 67.34→*70.16*], [+1.43 / +2.27], [Helps both; helps FS more],
      [D04], [Arithmetic executor (R2 gate)], [200], [legacy], [*−1.0* [−2.5, 0.0], all four readers], [−0.38], [*Rejected*],
      [D09], [Eight table representations], [200], [legacy], [`md_kv` *+4.0* [−2.0, +10.0]], [`pipe_clean` +2.21], [No significant winner],
      [D10], [Row selection for long tables], [155], [legacy], [k=20 *+1.9* [−2.6, +7.1]; tokens −46.6%], [+0.72], [Real token savings],
      [D11], [Simplified POMA v3 (v3lite)], [992], [legacy], [*+0.40* [−0.50, +1.31]], [+0.64], [No component significant],
      [D12], [Pipe representation], [500], [fixed], [`pipe_nohdr` *+2.0* [−1.0, +5.0]], [+1.10 [−0.71, +2.92]], [Worth validating],
      [D13], [LLM header filtering], [200], [fixed], [*−14.5* [−21.0, −8.0]], [*−10.10* [−14.09, −6.37]], [*Rejected: harmful*],
      [—], [Parser-fix A/B], [991], [both], [fixed − legacy: *−1.41* [−3.13, +0.30]], [−0.37 [−1.30, +0.56]], [Keep fix; claim no gain],
      [—], [N1 — run variation], [900], [legacy], [*−0.44* (second observation *+1.7*)], [−0.12 [−1.04, +0.78]], [Exceeds the measured gains],
      [—], [Hybrid BM25 + PhoBERT], [476], [—], [dense loses to BM25 at every k], [—], [*Rejected* by preset rule],
      [—], [Backbone 2: Gemma-3-4B-IT], [543], [legacy], [POMA − ZS: *−12.89* [−17.13, −8.66]], [*−9.89* [−12.60, −7.14]], [POMA clearly loses],
      [—], [Backbone 3: SEA-LION v3 8B], [992], [—], [ZS 49.50 / FS 49.45 / CoT 47.83], [—], [No paired POMA comparison yet],
      [—], [GaP-TQA, separate system (dev)], [991], [fixed], [A5 − FS+Verbalize *+1.41* [−0.71, +3.53]], [—], [Cheaper; not significant],
    )
  ]
  #v(0.2em)
  #text(size: 0.7em)[
    #warning-block(title: [Read this row-wise only])[
      Every CI for an improvement direction includes zero, except D13, whose
      effect is harmful. The parser fix splits the record: D01–D11 used the old
      parser, D12–D13 the corrected one. Only D12 has a paired BIF interval;
      D02's BIF deltas compare artifacts from different runs; "—" means BIF has no
      matched paired samples for that row (see Backbones slide for Gemma/SEA-LION detail).
    ]
  ]
]

== Examples

#slide(title: [Three representative directions])[
  #text(size: 0.74em)[
    *D10 — row selection for long tables* (n=155, tables over 2,000 tokens)
    #v(0.1em)
    Input tokens −46.6%, cost −35.3%, latency 29.3 $->$ 17.4 s; EM 52.26 $->$ 54.19,
    CI [−2.6, +7.1]. Within full POMA over 992 questions, the saving dilutes to *−6.4%*.
  ]
  #v(0.25em)
  #text(size: 0.74em)[
    *D11 — POMA v3lite, five nested variants* (n=992) — detailed on the next slide
    #v(0.1em)
    control 68.35 $->$ v3lite 68.75. Total 13 wins / 9 losses over 992 questions;
    every CI includes zero.
  ]
  #v(0.25em)
  #text(size: 0.74em)[
    *D13 — LLM header filtering* (n=200, rejected)
    #v(0.1em)
    EM 65.5 $->$ 51.0, CI [−21.0, −8.0]; total tokens +75.9%, cost 2.75×.
    179/200 questions selected no rows at all, because 77.8% of tables have no
    left header column. The damage came from losing *row-locating* columns, not answer columns.
    BIF agrees: 74.20 $->$ 63.86, paired CI [−14.09, −6.37].
  ]
  #v(0.25em)
  #text(size: 0.76em)[
    #warning-block(title: [Pattern])[
      Adding a stage has not paid off. The one measurable win is cost, not accuracy.
    ]
  ]
]

== v3lite

#slide(title: [POMA v3lite: what was built and what it bought])[
  #v(0.1em)
  #align(center)[
    #image("assets/poma-v3lite.png", width: 86%)
  ]
  #v(0.4em)
  #grid(
    columns: (0.95fr, 1fr),
    column-gutter: 1.3em,
    align: (left + top, left + top),
    text(size: 0.56em)[
      #table(
        columns: (auto, 1fr, auto, auto),
        inset: 3pt,
        align: (left, left, right, right),
        stroke: 0.4pt + luma(185),
        table.header([*Variant*], [*Added component*], [*EM*], [*BIF*]),
        [`control`], [POMA-first, full Flatten V1], [68.35], [75.33],
        [`control_fmt`], [\+ rule-based formatter], [68.55], [75.50],
        [`h1`], [\+ H1 long-table reduction], [68.45], [75.57],
        [`h1_fmt`], [\+ both], [68.65], [75.75],
        [`v3lite`], [\+ answerability gate], [*68.75*], [*75.97*],
      )
      #v(0.3em)
      Net effect of all components: *+0.40 EM*, CI [−0.50, +1.31]; BIF +0.64.
    ],
    text(size: 0.56em)[
      *Cut before building* — program agent (low expected value in D04),
      generalist on an alternate view, and the consensus / adjudicator layer.
      #v(0.3em)
      *Why each stage captured so little.* H1 changes 91/992 questions, yet
      deployed prompt tokens fall only *6.4%*. The formatter barely moves POMA,
      which already normalizes answers. The gate replaced `Null` 16 times:
      5 fixed an error, 4 broke a correct `Null`, 7 stayed wrong.
    ],
  )
]

== Backbones

#slide(title: [The second backbone answers the question directly])[
  #text(size: 0.7em)[
    *Gemma-3-4B-IT via OpenRouter* — n=543 (incomplete run), legacy parser
    #v(0.15em)
    #table(
      columns: (1fr, auto, auto, auto, auto, auto),
      inset: 4pt,
      align: (left, right, right, right, right, right),
      stroke: 0.4pt + luma(180),
      table.header([*System*], [*EM*], [*F1*], [*R1*], [*MET*], [*BIF*]),
      [POMA-first], [26.70], [48.98], [34.41], [35.14], [51.06],
      [Zero-shot], [*39.59*], [*57.31*], [*47.07*], [*47.83*], [*60.95*],
      [*Difference (POMA − ZS)*], [*−12.89*], [−8.33], [—], [—], [*−9.89*],
    )
    #v(0.15em)
    Paired 95% CI EM [−17.13, −8.66], BIF [−12.60, −7.14] — both *exclude zero*
    (BIF n=542/543; one crashing Zero-shot answer excluded from both arms).
  ]
  #v(0.2em)
  #text(size: 0.7em)[
    *SEA-LION v3 8B IT* — local run on Kaggle with vLLM
    #v(0.15em)
    #table(
      columns: (1fr, auto, auto, auto, auto),
      inset: 4pt,
      align: (left, right, right, right, right),
      stroke: 0.4pt + luma(180),
      table.header([*Variant*], [*n*], [*EM*], [*F1*], [*BIF*]),
      [Zero-shot / Few-shot / CoT (full test)], [992 / 991], [49.50 / 49.45 / 47.83], [66.09 / 66.27 / 64.46], [68.24 / 68.34 / 67.20],
      [POMA (stratified 500 subset)], [486], [43.00], [60.07], [*59.89*],
    )
  ]
  #v(0.15em)
  #text(size: 0.66em)[
    #warning-block(title: [Pattern across backbones])[
      Any benefit from POMA depends on the backbone and reverses on a weaker one.
      SEA-LION rows use different question sets, no paired conclusion yet
      (CoT BIF n=897/990: same crash-exclusion as Gemma).
    ]
  ]
]

== GaP-TQA

#slide(title: [Why GaP-TQA has this shape])[
  #grid(
    columns: (1fr, 1fr),
    column-gutter: 1.2em,
    align: (left + top, left + top),
    text(size: 0.62em)[
      *Gold answer types, test (n=992), no API calls*
      #v(0.15em)
      #table(
        columns: (1fr, auto),
        inset: 3.5pt,
        align: (left, right),
        stroke: 0.4pt + luma(180),
        fill: (x, y) => if y == 0 { rgb("#2563eb").lighten(82%) } else if calc.odd(y) { luma(246) } else { white },
        table.header([*Gold is ...*], [*Share*]),
        [one table cell], [44.0%],
        [Yes/No], [19.3%],
        [a span inside a cell], [10.4%],
        [free text], [7.1%],
        [a number in the table / several cells], [5.1% / 5.0%],
        [`Null`], [4.5%],
        [*a number that must be computed*], [*3.0%*],
      )
      #v(0.2em)
      Only 3.0% need arithmetic, which is why the typed executor (D04) found
      nothing to fix. Only 9.0% of questions carry ≥ 2 hint labels, so runtime
      skill agents would have nothing to split.
    ],
    text(size: 0.62em)[
      *Free experiment: a train-derived Yes/No verbalizer node*
      #v(0.15em)
      #table(
        columns: (1fr, auto, auto, auto),
        inset: 3.5pt,
        align: (left, right, right, left),
        stroke: 0.4pt + luma(180),
        fill: (x, y) => if y == 0 { rgb("#2563eb").lighten(82%) } else { white },
        table.header([*System*], [*EM*], [*+ node*], [*Paired 95% CI*]),
        [Few-shot + GSA], [70.16], [*73.29*], [+3.13 [+1.92, +4.33]],
        [POMA + GSA], [68.45], [71.77], [+3.33 [+2.12, +4.54]],
      )
      #v(0.2em)
      Rule: `...đúng không?` → `Đúng`, `...phải không?` → `Phải`, otherwise `Có`;
      negatives → `Không`. It reproduces the gold string for 90.1% of train,
      87.6% of dev, and 91.6% of test Yes/No golds, so it is not fitted to test.
      Measured post hoc on test (n=992, legacy parser); 34 wins / 3 losses.
    ],
  )
  #v(0.3em)
  #text(size: 0.66em)[
    #result-block(title: [Both gates were then run on dev])[
      *Verbalize holds on dev:* +1.21 [+0.30, +2.12], Yes/No 74.4 → 81.7 (A1 vs. A0).
      *Cell-ID `Locate` passes on pure lookup questions* (78–82%, 133 dev questions),
      but emitting the located cell verbatim loses to the reader (A4 below): stopped.
    ]
  ]
]

#slide(title: [GaP-TQA A1: reader + Verbalize])[
  #v(1fr)
  #align(center)[
    #image("assets/gap-tqa-a1.png", width: 96%)
  ]
  #v(1fr)
  #text(size: 0.64em)[
    The control of the separate GaP-TQA system: one reader call on the Flatten V1 table,
    then a deterministic Yes/No verbalizer. Dev (n=991): *70.33 EM*; the verbalizer alone
    adds +1.21 [+0.30, +2.12].
  ]
]

#slide(title: [GaP-TQA A2a: pipe table])[
  #v(1fr)
  #align(center)[
    #image("assets/gap-tqa-a2a.png", width: 96%)
  ]
  #v(1fr)
  #text(size: 0.64em)[
    Same as A1, only the table string changes to `pipe_nohdr`. Dev: *71.95 EM*,
    +1.61 [−0.30, +3.53] vs. A1 — not significant; kept because it is slightly cheaper.
  ]
]

#slide(title: [GaP-TQA A5: graph per class])[
  #align(center)[
    #image("assets/gap-tqa-a5.png", width: 86%)
  ]
  #text(size: 0.62em)[
    Adapted from GaP (arXiv:2607.05369): a fixed graph per question class; the 8B model
    only fills reader leaves. Anchor rows are used for lookup questions only: enabled for
    every class (A3), list questions fall 78 → 56.
  ]
]

#slide(title: [GaP-TQA against zero-shot and few-shot, dev])[
  #text(size: 0.6em)[
    #table(
      columns: (1.5fr, auto, 1.3fr, auto, auto, auto, auto),
      inset: 3.5pt,
      align: (left, right, left, right, right, right, right),
      stroke: 0.4pt + luma(185),
      fill: (x, y) => if y == 0 { rgb("#2563eb").lighten(82%) } else if y == 3 or y == 9 { rgb("#059669").lighten(88%) } else { white },
      table.header([*System (Qwen3-8B, n=991)*], [*EM*], [*vs. FS + Verbalize (95% CI)*], [*W / L*], [*Yes/No*], [*Lookup*], [*Prompt tok.*]),
      [Zero-shot], [62.66], [−9.18 [−12.11, −6.26]], [67 / 158], [47.0], [69.8], [1.65M],
      [Few-shot], [68.31], [−3.53 [−4.84, −2.32]], [3 / 38], [58.5], [72.9], [2.40M],
      [*Few-shot + Verbalize*], [*71.85*], [—], [—], [—], [—], [2.40M],
      [GaP A1: reader + Verbalize], [70.33], [−1.51 [−3.83, +0.81]], [60 / 75], [81.7], [69.8], [1.98M],
      [GaP A2a: + `pipe_nohdr`], [71.95], [+0.10 [−2.12, +2.32]], [64 / 63], [81.7], [72.5], [1.89M],
      [GaP A2b: + `markdown_kv`], [71.14], [−0.71 [−3.03, +1.61]], [65 / 72], [79.3], [73.1], [3.31M],
      [GaP A3: anchor rows, all classes], [70.03], [−1.82 [−4.14, +0.61]], [60 / 78], [79.3], [73.3], [1.06M],
      [GaP A4: `Locate` + emit cell], [68.82], [*−3.03* [−5.55, −0.61]], [59 / 89], [81.7], [68.4], [2.13M],
      [*GaP A5: graph per class*], [*73.26*], [+1.41 [−0.71, +3.53]], [69 / 55], [81.7], [75.5], [*1.46M*],
    )
  ]
  #v(0.3em)
  #text(size: 0.64em)[
    #warning-block(title: [What this shows])[
      GaP-TQA beats zero-shot clearly, but *not* few-shot + Verbalize: A5's +1.41 includes
      zero, and A5 was picked after seeing dev (on 1,000 fresh train questions A5 vs. A2a
      is +1.10 [0.00, +2.20]). The firm gain is cost: *61%* of few-shot's prompt tokens.
      No POMA system has been run on dev yet.
    ]
  ]
]

// ============================================================
= Lessons
// ============================================================

== Variation

#slide(title: [Run-to-run variation exceeds every measured effect])[
  #text(size: 0.82em)[
    The *same configuration* — model, provider, prompt, cached hints, parser — run twice:
  ]
  #v(0.2em)
  #grid(
    columns: (0.85fr, 1.15fr),
    column-gutter: 1.4em,
    align: (center + horizon, left + horizon),
    text(size: 0.72em)[
      #table(
        columns: (auto, auto, auto),
        inset: 5pt,
        align: (left, right, right),
        stroke: 0.4pt + luma(180),
        table.header([], [*EM*], [*BIF*]),
        [Run 1], [68.33], [75.22],
        [Run 2], [67.89], [75.09],
        [*Difference*], [*−0.44*], [−0.12],
      )
      #v(0.4em)
      *98/900 answers (10.9%)* changed wording with no configuration change.
      #v(0.3em)
      A second observation: 68.35 versus 66.63 on identical settings, a *1.7-point* gap.
    ],
    text(size: 0.66em)[
      #table(
        columns: (1fr, auto, auto, auto),
        inset: 4pt,
        align: (left, right, right, center),
        stroke: 0.4pt + luma(180),
        table.header([*Intervention*], [*EM*], [*BIF*], [*Within variation?*]),
        [D10 H1 k=20], [+1.9], [+0.72], [yes],
        [D12 `pipe_nohdr`], [+2.0], [+1.10], [yes, at the boundary],
        [Parser fix], [−1.41], [−0.37], [yes],
        [D11 v3lite], [+0.40], [+0.64], [yes],
        [D04 R2 gate], [−1.0], [−0.38], [yes],
        [D13 `hdrfilter`], [−14.5], [−10.10], [*no*],
      )
    ],
  )
  #v(0.25em)
  #text(size: 0.76em)[
    #warning-block(title: [Implication])[
      Until this variation is characterized, effects near ±2 points cannot be
      interpreted. Two observations are not a standard deviation — three runs are needed.
    ]
  ]
]

== Headroom

#slide(title: [Large headroom, near-zero captured gain])[
  #text(size: 0.84em)[
    #table(
      columns: (1.4fr, auto, auto),
      inset: 5pt,
      align: (left, right, right),
      stroke: 0.4pt + luma(180),
      fill: (x, y) => if y == 0 { rgb("#2563eb").lighten(82%) } else if calc.odd(y) { luma(246) } else { white },
      table.header([*Mechanism*], [*Ceiling*], [*Captured*]),
      [Arithmetic executor (D04)], [1.8–3.2 pts], [*0*],
      [Answerability gate (D11)], [4.7 pts], [*+0.1*],
      [Specialist-disagreement resolver], [0.71 pts], [+0.30],
      [Perfect row retrieval], [< 0.1 pts], [—],
    )
  ]
  #v(0.45em)
  #text(size: 0.84em)[
    *Common cause: the intervention cannot tell which cases need correcting.*
    - The executor fires on 11 questions every reader *already answered correctly*, and on *0 of 15* reader errors.
    - The answerability gate replaced `Null` 16 times: 5 fixed an error, 4 destroyed a correct `Null`, 7 stayed wrong.
    - An adjudicator has no signal on the 44.2% of disagreements where both branches are wrong.
  ]
  #v(0.35em)
  #text(size: 0.82em)[
    #highlight-block(title: [Rule adopted])[
      Measure the activation gate's *conditional accuracy* before building an
      intervention — not just how many answers are wrong.
    ]
  ]
]

== Literature

#slide(title: [The literature predicted this])[
  #text(size: 0.6em)[
    #table(
      columns: (auto, 1fr, 1.25fr),
      inset: 4pt,
      align: left,
      stroke: 0.4pt + luma(180),
      fill: (x, y) => if y == 0 { rgb("#2563eb").lighten(82%) } else if calc.odd(y) { luma(246) } else { white },
      table.header([*Source*], [*Setup*], [*Result*]),
      [Choi, Zhu & Li (NeurIPS 2025)],
      [Homogeneous agents on one backbone, Qwen2.5-7B and Llama3.1-8B — POMA's setting],
      [Majority voting matches or beats every debate topology, with a martingale proof that debate cannot raise expected correctness],
      [Bertalanič & Fortuna (2026)],
      [N=10 homogeneous 7–8B agents],
      [Debate loses to isolated self-correction while using 2.1–3.4× the tokens],
      [Huang et al. (ICLR 2024)],
      [GSM8K at matched budget],
      [Multi-agent debate at 9 responses 83.0 versus self-consistency at 9 responses 88.2],
    )
  ]
  #v(0.3em)
  #text(size: 0.74em)[
    #highlight-block(title: [Reframing, not an excuse])[
      The 1.27 EM orchestration ablation is *consistent with published results*
      for homogeneous deliberation at 8B, not an anomalous failure.
    ]
  ]
  #v(0.25em)
  #text(size: 0.74em)[
    #result-block(title: [A publishable claim with precedent])[
      Choi et al. report the same model scoring 0.8713 or 0.6620 on GSM8K
      depending only on the answer extractor. POMA's normalization result
      reproduces that phenomenon independently, for Vietnamese Table QA.
    ]
  ]
]

// ============================================================
= Plan
// ============================================================

== Next Steps

#slide(title: [Not yet run, likely worth running])[
  #text(size: 0.62em)[
    #enum(
      spacing: 0.35em,
      [*N1 — finish the run-variation measurement.* Two of three control runs exist
        (gaps 0.44 and 1.7 EM); one more run, about \$5, *no new code*. Sets the effect
        size worth trusting, and decides whether tightening the answerability gate is worth trying.],
      [*N2 — few-shot + GSA and POMA in the same run, on dev.* The central comparison still
        pairs 68.75 and 70.16 from different runs, and it gives GaP-TQA the POMA baseline on
        dev that it lacks.],
      [*N3 — lower H1's k from 20 to 5–8.* The answer row has BM25 rank median 0,
        p90 = 2; about three quarters fewer retained rows, one confirmation run.],
      [*N4 — finish the second-backbone matrix:* Gemma 543/992 scored with no few-shot,
        CoT or finalized branch; SEA-LION still lacks a paired POMA run on the same subset.],
      [*N5 — a Granularity node for GaP-TQA:* after Verbalize, 96 test errors are
        granularity/format (`1709` vs. `Năm 1709`). Learn the policy per class on train, check on dev.],
      [*N6 — port Verbalize and the lookup-only anchor-row chain into POMA and few-shot.*
        Deterministic or cheap; A5 used 74% of A1's tokens.],
      [*N7 — one frozen test run: GaP A5 vs. few-shot + Verbalize.* Test is still unused
        for GaP-TQA; run it once, after N5–N6 are settled on dev.],
    )
  ]
  #v(0.2em)
  #text(size: 0.64em)[
    #warning-block(title: [Not worth repeating])[
      Another pipeline stage, another table representation, a consensus/adjudicator
      layer, specialist-disagreement gating, confidence weighting, or emitting an
      8B-located cell verbatim (GaP A4) — each already measured at or below noise, or harmful.
    ]
  ]
  #v(0.2em)
  #text(size: 0.64em)[
    #highlight-block(title: [How I would state the position today])[
      No fair comparison — same run, one answer, same finalizer — has shown POMA
      outperforming few-shot; all confidence intervals include zero. That is *not* the
      same as "POMA does not work."
    ]
  ]
]

#focus-slide[
  Thank you for your time.
]
