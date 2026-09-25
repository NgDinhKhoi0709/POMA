# Layout Recipes

Concrete, tested snippets for the layout problems that come up on nearly every slide deck.
All assume a touying-based theme where `#slide(title: [...])[ body ]` lays `body` out in a
fixed-height content area (header/footer are outside it).

## 1. Sizing a single figure to fill its slide without clipping or dead space

The core rule: constrain **one** dimension (`width:` or `height:`), matched to the image's
own aspect ratio, and center on the other axis.

```typst
#slide(title: [...])[
  #align(center + horizon)[
    #image("fig.png", height: 90%)   // portrait/square source: constrain height
  ]
]
```

```typst
#slide(title: [...])[
  #align(center)[
    #image("fig.png", width: 100%)   // wide/landscape source: constrain width
  ]
]
```

Decision rule: compute the image's aspect ratio (`w/h`) and compare to the slide content
area's aspect ratio (roughly 2.1–2.3 for a 16:9 slide with a title bar, wider if the slide
has no caption below). If the image is *wider* than the content area's ratio, constrain by
`width`; if *taller/squarer*, constrain by `height`. Getting this backwards is the single
most common "why does this look wrong" bug — the unconstrained dimension scales freely and
either overflows the frame (gets clipped by the page boundary, invisible without rendering)
or comes out much smaller than the available space (ugly dead space).

**Always check actual pixel dimensions before guessing:**

```python
from PIL import Image
print(Image.open("fig.png").size)          # (width, height)
```

```python
import fitz
print(fitz.open("fig.pdf")[0].rect)         # width, height in points, for PDF figures
```

## 2. Figure + caption slide with balanced whitespace (`v(1fr)` trick)

When a slide has a fixed-size figure plus a caption below it, and the two together are
noticeably shorter than the available content height, the block ends up glued to the top
with a big dead zone at the bottom. Fix by bracketing the whole thing with `#v(1fr)`:

```typst
#slide(title: [...])[
  #v(1fr)
  #align(center)[
    #image("fig.pdf", height: 74%)
  ]
  #v(0.3em)
  #align(center)[
    #text(size: 0.78em)[Caption text explaining the figure.]
  ]
  #v(1fr)
]
```

`v(1fr)` works as flexible space inside a slide body (the page/content area has a definite
height), so equal `1fr` spacers before and after the content vertically center it *and*
distribute the leftover space symmetrically — this reads as deliberately centered rather
than "shrunk and stuck at the top." Tune the image `height:`/`width:` % up as far as
possible before the slide overflows (verify with the render loop, main SKILL.md §6); a
figure that's too small relative to its slide looks like a bug even when technically fine.

## 3. Two-column image + text (qualitative example / comparison slides)

For a figure that needs substantial explanatory text alongside it (case studies,
qualitative comparisons), use a `grid` with tuned column-width ratios rather than stacking
image-then-text — this uses the full slide width and reads better for asymmetric content.

```typst
#slide(title: [...])[
  #grid(
    columns: (1.05fr, 1fr),          // tune to the image's own aspect ratio — see below
    column-gutter: 1.8em,
    align: (center + horizon, left + horizon),
    image("fig.png", height: 96%),   // or width: 100% if the source is itself wide/landscape
    text(size: 0.6em)[               // shrink until it fits — see step below
      Intro sentence giving context.

      #v(0.3em)
      - *Point A:* ...
      - *Point B:* ...
      - *Point C:* ...

      #v(0.3em)
      #result-block(title: [Insight])[
        One or two sentences tying the figure back to the argument.
      ]
    ],
  )
]
```

**Tuning procedure (do this in order, re-rendering after each step per §6):**

1. Set the column ratio to roughly match the image's own aspect ratio relative to the
   text column's needs — a wider/landscape image wants a bigger first-column weight (e.g.
   `2.3fr, 1fr` for a very wide side-by-side comparison figure); a near-square image can
   use closer to `1:1` (e.g. `1.05fr, 1fr`).
2. Set the image to whichever of `width`/`height` fills its column without overflowing the
   row height, then bump it up as large as looks good.
3. **The text column font size is the #1 overflow risk in this layout** — a `result-block`
   (or any `tblock`) has `breakable: false` internally, so if the column's total content
   is even slightly too tall, the *entire* block (not just the overflowing line) jumps to
   a new page, leaving a nearly-blank continuation slide. Start around `0.6–0.85em`
   depending on how much text there is, and shrink further (and/or tighten `#v()` gaps
   between bullets and the block) until the whole column fits beside the image with no
   overflow. Re-render and check the page count after every size change — this is the
   layout most likely to silently spill onto page 2.

## 4. Nudging a centered block up or down (`align(horizon)` trailing-space trick)

Touying title slides (and any custom slide using `align(center + horizon)` on a whole
content block) center the block's *total bounding box* within the available region. If the
visible content looks bottom-heavy — a big gap above, a cramped gap below — the fix is
**not** to move the content itself, but to pad the far side:

- Adding empty space (`#v(Xem)`) at the very **end** of the centered content shrinks how
  much room is "left over" below the visible content once centered, which pulls the whole
  block **upward** (the block's total height grows, so centering it consumes more of the
  region symmetrically, and since the added space is invisible at the bottom, the *visible*
  content shifts up relative to where it was).
- Symmetrically, adding space at the very **start** would push the visible content down.

In practice, for a bottom-cramped title slide:

```typst
#title-slide(
  additional-content: [
    _Advisor:_ Prof. Name \
    Institution line
    #v(2.5em)   // <- pulls the whole centered block upward; tune the value empirically
  ]
)
```

Tune the `v()` amount empirically by re-rendering — there's no closed-form target value
since it depends on the theme's exact spacing constants; 1.5–3em is a typical useful range.
This same trick applies to *any* `align(horizon)`-centered block that looks lopsided, not
just title slides.

## 5. Full-width dense table on one slide

Large results tables (many baselines × many metrics) can fit on one slide with aggressive
but still-legible sizing:

```typst
#slide(title: [...])[
  #text(size: 0.52em)[
    #table(
      columns: (auto, auto, ...),   // as many as needed
      inset: 3.2pt,
      align: center,
      stroke: 0.4pt + luma(180),
      fill: (x, y) => if y == 0 { rgb("#059669").lighten(80%) }
                       else if calc.odd(y) { luma(245) } else { white },
      table.header([*Col1*], [*Col2*], ...),
      table.cell(rowspan: 4)[Group A], [...], ...,   // rowspan for merged group labels
      ...
    )
  ]
  #v(0.2em)
  #text(size: 0.85em)[
    #result-block(title: [Key Result])[ One-sentence takeaway. ]
  ]
]
```

Keep `inset` tiny (2.5–4pt) and font very small (0.5–0.55em) only for the table itself;
wrap the takeaway block separately at a more readable size (0.8–0.9em) so the one thing
the audience should remember isn't also microscopic. Verify the takeaway block didn't get
pushed to page 2 (a very common outcome with a table this dense) — add a small `#v()`
before it and/or shrink it slightly if so.
