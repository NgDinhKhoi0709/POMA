---
name: typst-slide
description: >
  Build or edit an academic presentation slide deck in Typst (touying-based theme, e.g.
  ens-rennes-presentation). Use when the user asks to create defense/conference/thesis
  slides from a paper or report, wants an existing .typ slide deck edited, resized, or
  restructured, wants a translated (EN/VN or other language) parallel version of a deck,
  hits a Typst compile error or a layout that "looks broken/ugly/ wrong size" in a
  presentation file, or asks to regenerate a low-quality figure for a slide. Covers theme
  setup, content-fidelity discipline (match the actual source paper, not a stale draft),
  bilingual writing conventions, image-sizing math, avoiding header text-collision and
  silent page overflow, and the mandatory render-and-visually-inspect verification loop.
---

# Typst Slide Deck

Build and maintain academic presentation decks in Typst on a touying-based theme (this
skill was distilled from building `ens-rennes-presentation` defense decks, but the rules
generalize to any touying theme). The single most important fact about this workflow:
**Typst never warns about overflow — a slide that's one line too tall silently spills
onto a blank-looking continuation page, and you will not notice unless you render and
look.** Nearly every rule below exists to prevent or catch that failure mode.

## 0. Before writing anything: find the ground truth

If the deck is derived from a paper/thesis, re-read the *actual current* source file
before drafting slides — not a remembered earlier draft, not the thesis's original
proposal. Papers get revised; sections get cut; RQ counts change. Content that isn't in
the final source must not appear in the slides. If the user says "chỉ theo đúng paper X"
/ "just follow paper X", treat X's on-disk content right now as ground truth and re-derive
structure from it, discarding anything from earlier drafts or memory.

If multiple candidate figures exist for the same concept (e.g. a paper's single cramped
combined diagram vs. a companion report's separate per-component figures), prefer
separate purpose-built figures — split them across multiple slides rather than cramming
one dense figure onto one slide. See `references/layout-recipes.md` for how to size and
lay out multi-figure slides.

## 1. Theme setup

**This project already ships a ready-to-run `ens-rennes-presentation` (HCMUS-branded)
package at its root — don't re-vendor from the Typst cache.** It's fully self-contained
(theme + touying vendored with relative imports, no `@preview` network/registry
dependency, HCMUS logo and colors already patched in):

- `../../../main.typ` (project root `main.typ`) — blank starter deck.
- `../../../packages/` (project root `packages/`) — the vendored theme (do not edit).
- `../../../references/` (project root `references/`) — two complete real defense decks
  (15-slide and 30-slide, already verified overflow-free) to copy patterns from: formulas
  inside blocks, result tables, image-sizing choices, a two-color status-bar/timeline
  built from `grid` + `block`. See `references/README.md` there for what each one
  demonstrates.

Start from the root `main.typ` (or one of the reference decks) directly — nothing to
copy, it's already in this project. See the root `README.md` for the short version of
this same setup.

If this project is instead using a different touying theme (or starting a theme from
scratch), find the installed theme package (Windows Typst cache, adjust for other OSes):
`%LOCALAPPDATA%\typst\packages\preview\<theme-name>\<version>\`. Read that package's own
`template/main.typ` and `theme.typ` once per project to confirm the exact API — themes
vary. Boilerplate for `ens-rennes-presentation` (touying-based):

```typst
#import "@preview/ens-rennes-presentation:0.1.0" : *

#let highlight-block = tblock.with(color: rgb("#2563eb"))  // blue — setup/definitions
#let result-block = tblock.with(color: rgb("#059669"))     // green — findings/positive results
#let warning-block = tblock.with(color: rgb("#dc2626"))    // red — limitations/failure modes

#show: ens-rennes-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [...],        // OFFICIAL registered title — see §5
    subtitle: [],        // can be empty; don't force a subtitle if the title is self-sufficient
    mini-title: [...],   // shown in the footer of every content slide — keep it SHORT
    authors: [...],
    mini-authors: [...],
    date: datetime(year: ..., month: ..., day: ...),
  ),
  section-style: "named subsection",  // header row 1 = all top-level sections, row 2 = active section's subsections
  department: "info",
  display-dpt: false,
  named-index: true,
)

#title-slide(additional-content: [ ... ])

= Top-Level Section        // appears in header row 1
== Subsection               // appears in header row 2, only while this section is active

#slide(title: [Slide Title])[
  content...
]

#focus-slide[
  Thank-you text, large centered, solid background, no header/footer.
]
```

Use consistent semantics for the three block colors across the whole deck: blue for
"here's the setup/goal," green for "here's what we found," red for "here's the catch."
A reader scanning fast should be able to tell a slide's role from its block color alone.

## 2. Structure and page budget

- Typical defense/conference deck: **25–35 slides** for a 15–20 min talk. Confirm the
  target with the user before drafting if unstated.
- Mirror the source document's structure: Outline → Motivation/Problem → Background →
  Proposed method (one topic/figure per slide, not crammed) → Experiments (setup slide,
  then one slide per research question, each with its own table/figure + a 1–2 sentence
  takeaway block) → Discussion/Limitations/Conclusion → Publications/References →
  closing `focus-slide`.
- One `==` subsection per major topic or per RQ keeps the header nav a useful progress
  indicator *and* forces titles to stay short (see §3).

## 3. Header text-collision (the #1 layout bug)

Touying-style headers render section/subsection names in two fixed-height, **non-breakable**
blocks. If the combined nav text for a row is too wide, it wraps to a second line and
visually collides with the header content below it. Symptom: subsection labels look
crammed or overlapping in a screenshot.

Rules:
- Keep every `=`/`==` heading to 1–3 words. `"RQ1 — Overall Comparison"` → `"RQ1"`.
  `"Thảo luận & Kết luận"` is fine at 3 words; its literal English translation
  `"Discussion & Conclusion"` is often too long once combined with 5 sibling sections —
  shorten to `"Discussion"`.
- **English is usually longer than the source language.** A heading set that fits in
  Vietnamese may not fit once translated — re-check header wrapping independently for
  every language version, don't assume parity.
- If a title text block itself (e.g. the title-slide's big title) wraps to more lines than
  intended, wrap it in `#text(size: 0.75–0.85em)[...]` to bring it back down rather than
  shortening the actual (official) title.

## 4. Image sizing

Pick **width or height, never both**, based on the image's own aspect ratio vs. the slide
area it fills — the unconstrained dimension scales proportionally, so picking the wrong
one either clips content or leaves large dead space:

- Wide/landscape source (aspect ratio ≳ 1.8) → constrain by `width:`.
- Square-ish or portrait source → constrain by `height:`.
- Always check actual pixel dimensions before choosing (`PIL.Image.open(p).size` or
  `fitz.open(p)[0].rect` for a PDF figure) — don't guess from how it looks in a
  screenshot at some other zoom level.
- Swapping in a replacement asset? Re-check its aspect ratio — reusing the old width/height
  % on a differently-proportioned image is the most common regression when refreshing figures.
- PDF vector figures embed directly: `#image("fig.pdf")` — no rasterization needed.

Full sizing math, the `v(1fr)` vertical-centering trick, and the two-column
image+text grid recipe are in `references/layout-recipes.md` — read it before tuning any
figure slide.

## 5. Title slide polish

- `title:` should be the deck's **official** title (as registered/approved), which can
  differ from an internal codename used throughout the body (e.g. a project/model acronym).
  Put the official title in `title:`; drop or minimize a codename subtitle if the title is
  already descriptive on its own — don't force a redundant subtitle.
- `mini-title`/`mini-authors` populate the footer on *every* slide — keep them short
  (footer is a tight 3-column row). Institution name is often a better footer fill than
  repeating the deck title.
- The whole title-slide body is centered as one block (`align(center+horizon)`). If it
  looks bottom-heavy (big gap above the title box, cramped below), add trailing
  `#v(Xem)` at the *end* of `additional-content` — extra space at the bottom of a
  centered block pulls the whole block upward to keep its center fixed. This is the
  general fix for any lopsided `align(horizon)` block, not just title slides.
- A too-long title can itself overflow the title slide onto a silent page 2 (same failure
  mode as §6) — verify the title slide's page count too, not just content slides.

## 6. The verification loop — mandatory after every change

Typst does not warn on overflow. After *any* content, sizing, or spacing edit:

1. `typst compile deck.typ deck.pdf` — check for actual compile errors (ignore benign
   `unknown font family` warnings from the theme).
2. Check the page count. Any unexpected `+1` vs. what you expected is a strong overflow
   signal — find it before doing anything else.
3. Render the changed slide (and its immediate neighbor, in case content spilled) to PNG
   with `scripts/render_pages.py` (wraps PyMuPDF) and view them with the Read tool.
   After a broad edit (translation, theme change, global font tweak), render **every**
   page — don't sample.
4. Look for: text cut off at a slide edge, a header/subsection row wrapped to 2 lines, a
   near-blank "continuation" page repeating the header/footer, or a figure clipped/floating
   with excess dead space.
5. Fix by, in order of preference: reduce `#v()` spacing → shrink `#text(size: ...)` on
   the overflowing block → reduce image %/height → split one dense slide into two. Repeat
   the loop until the page count is stable and every rendered page looks correct.

Never report a layout change as done without having rendered and looked at the result.

## 7. Common Typst syntax pitfalls (vs. LaTeX habits)

Full table in `references/typst-cheatsheet.md`. Highlights that recur constantly:

- `@` followed by a letter/digit is parsed as a **label reference**
  (`HR@5` breaks compilation) — escape as `\@5`.
- `{=}`, `{,}` are LaTeX-paste artifacts, not valid Typst — use bare `=`, `,`.
- No backslash commands: `bold()`, `sqrt()`, `sum_(i=1)^n`, `>=`/`<=` (not `\geq`/`\leq`),
  `->` (not `\rightarrow`), `cal()`, `macron()`.
- `times.circle` is deprecated → use `times.o`. Some LaTeX symbol names (e.g.
  `gt.eq.tilde`) don't exist in Typst — fall back to a plain operator or compose manually.
- Numbered `+` list items: inserting `#v()` or other content *between* items resets the
  list to restart at 1 (Typst treats the interruption as ending the list). Use explicit
  `#enum(spacing: 1.2em, [item1], [item2], ...)` when you need custom inter-item spacing.
- A Python `sed`/regex pass across a whole file for a repeated fix (e.g. escaping every
  `@N`) is more reliable than manual find-and-replace when the pattern recurs dozens of
  times — but double-check it doesn't also touch unrelated syntax (e.g. `@preview` imports).

## 8. Bilingual (or multi-language) decks

Keep each language as a **full independent file** (`deck.typ`, `deck-en.typ`, ...), not a
shared template with string tables — easiest to keep structurally in sync and each
compiles standalone.

- Preserve identical structure, images, tables, formulas, and layout tuning (font sizes,
  grid column ratios, `v()` spacing) — translate only prose: headings, bullets, block
  titles, captions, table headers.
- Keep established technical/CS/ML terms in their conventional language in *every*
  version (don't force-translate "self-attention", "gradient flow", RoPE, etc. into the
  target language if the field doesn't).
- Expect new overflow after translating to a more verbose language — re-run the full
  verification loop (§6) independently per file. Page-count parity across languages is a
  useful sanity check but not guaranteed; trace and fix any divergence rather than
  assuming it's fine.
- Re-check header wrapping independently per language (§3) — section names that fit in
  the source language often don't in translation.

## 9. Regenerating a weak figure

If an existing figure looks visibly worse than the deck's other figures (older style,
low-res raster, cramped), don't just resize it — regenerate it:

1. If a vector source exists (e.g. a `.drawio` XML file), read it to extract exact text
   labels, colors, and structure — this becomes the spec for the new figure, not a
   re-guess from the raster export.
2. Write an image-generation prompt describing the diagram in a flat, vector "draw.io/
   technical diagram" style: rounded boxes with solid single-color fills, thin black
   arrows, short text labels, explicit STRICT CONSTRAINTS banning icons/emoji/clipart/
   gradients/drop-shadows/3D. Reference one of the deck's *other* already-good figures as
   the uploaded style-reference image for the generation tool.
3. After the new asset lands, re-derive its sizing from scratch (§4) — don't reuse the
   old asset's width/height % blindly, its aspect ratio has likely changed.

(If a dedicated figure-prompt-style skill/convention is available in this environment,
use its prompt template instead of improvising one.)

## Reference files

These paths are relative to this skill's own folder (`.claude/skills/typst-slide/`):

- `references/typst-cheatsheet.md` — full LaTeX→Typst syntax gotcha table.
- `references/layout-recipes.md` — image sizing math, the `v(1fr)` centering trick, the
  two-column image+text grid recipe with tunable ratios, and the `align(horizon)`
  trailing-space nudge explained with the underlying centering math.
- `scripts/render_pages.py` — compile-independent PDF→PNG page renderer (PyMuPDF) for
  step 3 of the verification loop; run it, then `Read` the output PNGs.

Separately, at the **project root** (three levels up from here): `main.typ` (blank
starter), `packages/` (vendored theme), and `references/` (two full worked-example
decks — a *different* folder from this skill's own `references/` above). See §1 and the
project root's `README.md`.
