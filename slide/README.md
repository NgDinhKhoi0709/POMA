# POMA Progress Presentation

This Typst deck is for **reporting progress to the supervisor**, not for the thesis
defense. It presents the current system, approaches tested, experimental results,
and next steps, then seeks guidance on the research direction.

It is built on the touying-based theme vendored under `packages/`, which is
self-contained: no network access or Typst package registry is required.

**The deck carries no logo, no affiliation line, and no name in the footer.** Both
are handled in `packages/ens-rennes-presentation/theme.typ`: the header's logo slot
is empty (see the comment in `header`), and the footer has just two cells — the
`mini-title` flush left and the slide counter flush right. The old middle
`mini-authors` cell was removed, so setting `mini-authors` in `config-info(...)`
now has no effect. The author's name appears only on the title slide, via
`authors`.

**Numeric notation differs between the source files and the deck.** The
`context/` files keep the original notation, where a comma is the decimal
separator and a period groups thousands (80,24 and 2.000). The English deck
uses the English convention instead — a period for decimals and a comma for
thousands (80.24 and 2,000) — because an English-reading audience would
otherwise misread "2.000" as two. Keep each file internally consistent.

## Structure

```
slide/
  progress-report.typ          <- THE DECK (English, 20 pages) — start here
  progress-report.pdf          <- compiled output
  script-thuyet-trinh.md       <- Vietnamese speaker script, one section per slide
  main.typ                     <- blank starter template, kept unused
  render/                      <- page PNGs from the verification loop
  context/                     <- CONTENT: consolidated research, experiments, and results
  assets/                      <- images used by the deck
  packages/                    <- vendored theme (do not delete or move)
  .claude/skills/typst-slide/  <- Claude Code skill for authoring Typst slides
```

## Content sources

**All deck content comes from [`context/`](context/).** Do not add facts from
memory. Every figure there has a source and metadata (n, parser, scorer, model,
and run).

- Start with [`context/00-README.md`](context/00-README.md), the index and five
  essential points.
- [`context/09-goi-y-cau-truc-slide.md`](context/09-goi-y-cau-truc-slide.md)
  maps content to individual slides for a **15-slide version** (15–20 minutes)
  and a **25-slide version** (if the supervisor wants details on each approach).

**Required rule for reporting numbers:** every results table on a slide needs
a metadata line (n, legacy/fixed parser, model, and run). Two figures may appear
as a direct comparison only when all six attributes match. The rationale and
list are in [`context/05-bang-so-lieu-tong-hop.md`](context/05-bang-so-lieu-tong-hop.md).

## Getting started

1. Edit `progress-report.typ` — `config-info(...)` holds the title, authors,
   and date; the body is one `#slide(...)` per page.
2. Write content as `= Section` → `== Subsection` → `#slide(title: [...])[ ... ]`.
3. Put images in `assets/` and use `#image("assets/file-name.png", width: ...)`.
4. Compile. The `typst` CLI is **not installed** on this machine; the Python
   bindings in the `kltn` conda environment are used instead:

   ```bash
   "D:/.virtual_env/anaconda/envs/kltn/python.exe" -c "import typst; typst.compile('progress-report.typ', output='progress-report.pdf')"
   ```

5. Render and inspect every changed page:

   ```bash
   "D:/.virtual_env/anaconda/envs/kltn/python.exe" .claude/skills/typst-slide/scripts/render_pages.py progress-report.pdf render --dpi 90
   ```

If using Claude Code, open `slide/` as the project. The `/typst-slide` skill is
already in `.claude/skills/` and provides the overflow and image sizing rules
below. For syntax examples, see
`.claude/skills/typst-slide/references/typst-cheatsheet.md` and
`layout-recipes.md`.

## Required layout checks

**Typst does not warn when content overflows a slide.** One extra line can
silently create another, mostly blank page. After each edit:

1. Compile and count PDF pages. An unexpected page count suggests overflow.
2. Render the edited page to a PNG and inspect it:
   ```python
   import fitz
   d = fitz.open("out.pdf")
   d[PAGE_INDEX].get_pixmap(dpi=150).save("check.png")
   ```
3. If content overflows, reduce `#v()` spacing, then font size
   (`#text(size: 0.85em)[...]`), then image size; split the slide if needed.

Common pitfalls:

- **`highlight-block`, `result-block`, and `warning-block` cannot split
  across pages.** A block slightly taller than the remaining space moves to
  a new page.
- **Keep `=` and `==` headings short (1–3 words).** The header has two fixed
  rows; longer headings can wrap over slide content.
- **Set either `width:` or `height:` for images, never both.** Check the real
  aspect ratio first (`PIL.Image.open(p).size`, or `fitz.open(p)[0].rect` for a
  PDF). Use `width:` for wide images (ratio ≳ 1.8) and `height:` for square or
  portrait images. Recheck the ratio when replacing an image.
- **Long results tables overflow more readily than prose.** Remove unused
  columns (for example, ROUGE-1 or METEOR) before shrinking text below `0.8em`.
- **For status bars or timelines**, place adjacent `block(fill: ...)`
  elements in a `#grid`. Every block needs `width: 100%` to avoid disconnected
  pieces.
- Avoid confusing Typst with LaTeX syntax: escape `@` after letters or digits
  (`FAR\@cov`); use `sqrt()`, `>=`, and `->` instead of `\sqrt`,
  `\geq`, and `\rightarrow`. `${\sim}` and `{=}` are LaTeX paste artifacts;
  use plain text or the intended character.

## Three color-coded blocks

Use `highlight-block` in blue for background and setup, `result-block` in green
for positive findings, and `warning-block` in red for limitations and cautions.

**For this deck:** most current results are **neutral or limiting**: every
confidence interval for an improvement approach includes zero. **Do not use a
green `result-block` for an effect whose confidence interval includes zero.**
Reserve green for clearly positive results, such as H1's token savings or the
completed evaluation infrastructure.

## Theme configuration

`aspect-ratio: "16-9"`. The `department` setting only selects an accent color
and takes effect when `display-dpt: true`; with `false`, the default blue
palette applies and the setting is invisible. With
`section-style: "named subsection"`, the first header row shows the section and
the second shows the active subsection.

Because this is a progress meeting rather than a defense:

- `title` states the project plus "Progress report", and the subtitle names the
  purpose of the meeting.
- The closing slide is a **request for guidance** rather than a thank-you to a
  committee. The six decisions appear at the end of
  [`context/08-huong-di-tiep-theo.md`](context/08-huong-di-tiep-theo.md).
- Neither the title slide nor the footer names an institution.

## Suggested lengths

| Version | Slides | Use when |
|---|---:|---|
| As built | 19 + closing | A 15–20 minute update on the current state, tested approaches, and plan |
| Extended | 25 | The supervisor wants details on each experiment (D01–D13, parser, drift) |

`progress-report.typ` is the "as built" version: 20 PDF pages, of which 19 are
numbered slides and the last is the closing slide.

Three slides are essential even if the deck is cut further: the **80.24 → 70.16
result sequence**, **variation across identical runs**, and **overview of
completed experiments**. See
[`context/09-goi-y-cau-truc-slide.md`](context/09-goi-y-cau-truc-slide.md).
