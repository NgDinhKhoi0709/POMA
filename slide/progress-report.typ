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

#slide(title: [Two matched-setting pairs, no oracle credit])[
  #text(size: 0.76em)[
    #table(
      columns: (1.3fr, auto, auto, auto, auto),
      inset: 4pt,
      align: (left, right, right, right, right),
      stroke: 0.4pt + luma(180),
      table.header([], [*EM*], [*F1*], [*R1*], [*MET*]),
      table.cell(colspan: 5, fill: luma(230))[*Pair 1 — single answer, no finalizer* (FS raw is an older run)],
      [Few-shot raw], [67.34], [78.63], [73.46], [73.55],
      [POMA-first], [66.63], [79.80], [74.69], [75.76],
      [*Δ (POMA − FS)*], [*−0.71*], [*+1.17*], [*+1.23*], [*+2.21*],
      table.cell(colspan: 5, fill: luma(230))[*Pair 2 — GSA finalizer, same run*],
      [Few-shot + GSA], [70.16], [81.52], [76.93], [77.23],
      [POMA + GSA], [68.45], [81.31], [77.12], [78.15],
      [*Δ (POMA − FS)*], [*−1.71*], [*−0.21*], [*+0.19*], [*+0.92*],
    )
  ]
  #v(0.3em)
  #text(size: 0.78em)[
    - On EM, POMA trails Few-shot in *both* matched pairs: −0.71 with no
      finalizer, −1.71 with GSA — the strongest comparison here, same run and
      same finalizer for both sides (paired 95% CI [−3.93, +0.50] still crosses zero).
    - On F1/R1/MET POMA's small edge shrinks once both sides get GSA (+1.2 to +2.2
      → −0.2 to +0.9; F1 turns negative), and these metrics have no paired CI yet.
    - No matched-setting pair shows POMA beating Few-shot on EM. A larger
      "POMA wins" number elsewhere (e.g. oracle best-of-K) is not from a fair pair.
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
    ],
    text(size: 0.66em)[
      *Configuration*
      #v(0.15em)
      Paper's recipe: Adam, lr 1e-5, batch 16, 10 epochs, max length 128.
      Split sizes 24,376 / 3,009 / 2,991 match the paper. Dev: 85.24 / 85.18.
      Per-label test F1: entailment (used by BIF) 83.61, contradiction 79.89,
      neutral 80.27, other 98.20.
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
= Plan
// ============================================================

== Next Steps

#slide(title: [Next: experiments to improve GaP-TQA])[
  #v(1fr)
  #highlight-block(title: [Next step])[
    Continue experimenting with improvements to GaP-TQA.
  ]
  #v(1fr)
]

#focus-slide[
  Thank you for your time.
]
