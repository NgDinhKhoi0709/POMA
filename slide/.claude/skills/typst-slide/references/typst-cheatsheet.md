# Typst Syntax Cheatsheet (for people used to LaTeX)

Every entry here caused an actual compile error or silent wrong-rendering bug while
building a real presentation. Check this list first when a `.typ` file fails to compile
or renders text differently than intended.

## Math mode

| LaTeX habit | Typst | Notes |
|---|---|---|
| `\mathbf{x}` | `bold(x)` | |
| `\mathcal{L}` | `cal(L)` | |
| `\bar{L}` / `\overline{L}` | `macron(L)` | |
| `\sqrt{x}` | `sqrt(x)` | |
| `\sum_{i=1}^{n}` | `sum_(i=1)^n` | grouping uses `(...)`, not `{...}` |
| `\geq`, `\leq` | `>=`, `<=` | Typst auto-renders these as ≥ ≤ glyphs |
| `\rightarrow`, `\to` | `->` | |
| `\{=\}`, `\{,\}` (literal braces from a bad paste) | plain `=`, `,` | `{=}`/`{,}` are **not valid Typst** — if you see literal `{=}` text in a render, this is why |
| `\times` (circled, e.g. Kronecker product) | `times.o` | `times.circle` is deprecated, may warn or fail |
| `\gtrsim` / similar exotic relation symbols | usually no direct Typst equivalent (e.g. no `gt.eq.tilde`) | fall back to `>=` or compose from base symbols; don't assume every LaTeX symbol name maps 1:1 |

## Text mode / general syntax

- **`@` is a label reference trigger.** `@` immediately followed by a letter or digit is
  parsed as a cross-reference label, not literal text. `HR@5`, `NDCG@10` etc. in prose or
  table cells **must** be escaped: `HR\@5`. This is easy to miss because the compile error
  ("label `<5>` does not exist") doesn't obviously point at the `@`.
  - When fixing this across a whole file, a scripted global replace is more reliable than
    manual editing (dozens of instances is common in a results table) — e.g. a Python
    pass replacing `@10`→`\@10` and `@5`→`\@5`. **Verify it doesn't also mangle an
    unrelated `@preview` package import line at the top of the file.**
- No backslash commands in text mode either — Typst uses function-call syntax
  (`#function(args)[body]`) throughout, not TeX control sequences.
- Vietnamese (and other non-ASCII) text renders directly with no special encoding setup
  needed, as long as the font has the glyphs.

## Lists

- `+` starts a numbered list item. **Inserting `#v()` or any non-list content between two
  `+` items ends the list and starts a new one, resetting the counter to 1.** This is a
  common silent bug: a numbered list that should read 1, 2, 3 instead shows 1, 1, 2 because
  a spacer was placed between items 1 and 2.
  - Fix: don't interleave spacing with `+` items. If you need custom spacing between
    items, use `#enum(spacing: 1.2em, [item one], [item two], [item three])` instead —
    pass all items as arguments to one `enum()` call so the numbering stays contiguous.

## Images

- `#image("path.pdf")` embeds a PDF vector figure directly — no conversion to PNG/SVG
  needed (confirmed working Typst 0.14+).
- `#image(path, width: X%)` and `#image(path, height: X%)` — pick exactly one; see the
  main SKILL.md §4 and `layout-recipes.md` for the sizing decision.

## Fonts

- Theme templates often `set text(font: (...))` with a font list that includes fonts not
  installed on the compiling machine (e.g. `"Univers"`, `"CMU Sans Serif"`). Typst falls
  back gracefully and prints an `unknown font family` warning — this is **not** a compile
  error and can be ignored; don't chase it as a bug.

## Compile workflow

```
typst compile deck.typ deck.pdf
```

- Exit code and stderr both matter: grep stderr for `error` (case-insensitive) to
  distinguish real failures from the benign font warnings above.
- Typst gives **zero warning for content overflow** (a slide whose content exceeds the
  page height just flows onto a new page silently) — this is not a "gotcha" you fix with
  syntax, it's a structural fact that makes the render-and-look verification loop (main
  SKILL.md §6) mandatory, not optional.
