// ============================================================
// TEMPLATE: blank starter deck. The vendored touying theme under packages/
// carries no logo or affiliation line. See README.md for usage guidelines
// (title length, image size, overflow checks, etc.).
// ============================================================

#import "packages/ens-rennes-presentation/theme.typ": *

// --- Three color-coded blocks used throughout the deck ---
// blue  = background, definitions, and setup
// green = positive findings and results
// red   = limitations, failures, and cautions
#let highlight-block = tblock.with(color: rgb("#2563eb"))
#let result-block = tblock.with(color: rgb("#059669"))
#let warning-block = tblock.with(color: rgb("#dc2626"))

#show: ens-rennes-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [Thesis Title],
    subtitle: [], // leave blank if the title is sufficiently descriptive
    mini-title: [Short Thesis Title], // shown in every footer; keep it SHORT
    authors: [Student One, Student Two],
    date: datetime(year: 2026, month: 1, day: 1),
  ),
  section-style: "named subsection", // first row = section; second = active subsection
  department: "info",
  display-dpt: false,
  named-index: true,
)

#title-slide(additional-content: [
  #v(1em)
  #text(size: 0.9em)[Supervisor: ...]
  #v(2em) // move the content upward if it sits too low; see README layout checks
])

// ============================================================
= Outline
// ============================================================

#slide(title: [Presentation Outline])[
  #v(1fr)
  + Problem Statement
  + Method
  + Experiments
  + Conclusion
  #v(1fr)
]

// ============================================================
= Problem Statement
// ============================================================

== Background

#slide(title: [Slide Title])[
  #highlight-block(title: [Objective])[
    Setup or definition content.
  ]
  #v(0.35em)
  #result-block(title: [Main Finding])[
    Finding or result content.
  ]
]

// For image slides, ALWAYS check the actual aspect ratio (PIL.Image.open(p).size
// or fitz for PDFs) before choosing width: or height:; see README image rules.
== Image Example

#slide(title: [Slide With an Image])[
  #align(center)[
    #image("assets/PLACEHOLDER.png", width: 70%)
  ]
]

// ============================================================
= Conclusion
// ============================================================

#slide(title: [Conclusion])[
  #warning-block(title: [Limitations])[
    Limitations or cautions.
  ]
]

#focus-slide[
  Thank you for your attention!

  #v(1em)
  #text(size: 0.6em)[Questions and Discussion]
]
