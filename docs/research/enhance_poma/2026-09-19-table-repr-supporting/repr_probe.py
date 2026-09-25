"""Scratch prototype (not repo code): candidate table serializations + Qwen3 token cost on the 200-question subset."""
import json, sys, statistics, unicodedata, collections
from pathlib import Path
sys.path.insert(0, r"D:\.UIT\KLTN\github\POMA")
from bs4 import BeautifulSoup
from preprocessing.parser import HTMLTableParser
from preprocessing.representation import FlattenedTable

ROOT = Path(r"D:\.UIT\KLTN\github\POMA")


def grid(table):
    parsed = HTMLTableParser().parse(table["table_html"])
    n_head = len(parsed.headers)
    cells = parsed.headers + parsed.rows
    rows = [[unicodedata.normalize("NFC", str(c.value or "").strip()) for c in r] for r in cells]
    mask = [[bool(c.is_header) for c in r] for r in cells]
    return rows, mask, n_head


def split_banner(rows, n_head):
    """Header rows whose cells are all identical (full-width banner) are hoisted out as caption lines."""
    banners, head = [], []
    for r in rows[:n_head]:
        if len(r) > 1 and len(set(r)) == 1 and r[0]:
            banners.append(r[0])
        else:
            head.append(r)
    return banners, head, rows[n_head:]


def header_path(head, ncols):
    if not head:
        return [f"Cột {j+1}" for j in range(ncols)]
    out = []
    for j in range(ncols):
        parts = []
        for r in head:
            v = r[j] if j < len(r) else ""
            if v and (not parts or parts[-1] != v):
                parts.append(v)
        out.append(" / ".join(parts) or f"Cột {j+1}")
    return out


def v1(t):
    return FlattenedTable.from_table_data(t).to_string()


def pipe_plain(t):  # V1 without <header> tag, header rows kept as-is
    rows, mask, n = grid(t)
    return "\n".join("|".join(r) for r in rows)


def _prep(t):
    rows, mask, n = grid(t)
    ncols = max((len(r) for r in rows), default=0)
    banners, head, body = split_banner(rows, n)
    keys = header_path(head, ncols)
    cap = [f"Chú thích: {b}" for b in banners]
    return cap, keys, body


def pipe_path(t):  # header-path collapse, no tag
    cap, keys, body = _prep(t)
    return "\n".join(cap + ["|".join(keys)] + ["|".join(r) for r in body])


def markdown(t):
    cap, keys, body = _prep(t)
    lines = cap + ["| " + " | ".join(keys) + " |", "| " + " | ".join("---" for _ in keys) + " |"]
    lines += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(lines)


def markdown_kv(t):
    cap, keys, body = _prep(t)
    out = list(cap)
    for i, r in enumerate(body, 1):
        out.append(f"## Hàng {i}")
        out += [f"{k}: {v}" for k, v in zip(keys, r)]
        out.append("")
    return "\n".join(out).strip()


def row_anchor(t):  # StructLM / TableLlama style col:/row i:
    cap, keys, body = _prep(t)
    lines = cap + ["col : | " + " | ".join(keys)]
    lines += [f"row {i} : | " + " | ".join(r) for i, r in enumerate(body, 1)]
    return "\n".join(lines)


def json_cols(t):
    cap, keys, body = _prep(t)
    return "\n".join(cap + [json.dumps({"columns": keys, "data": body}, ensure_ascii=False)])


def html_span(t):
    """Span-faithful HTML from the same parsed cell values as V1 (origin cells only, plain tags)."""
    parsed = HTMLTableParser().parse(t["table_html"])
    out = ["<table>"]
    for row in parsed.headers + parsed.rows:
        cells = []
        for c in row:
            if getattr(c, "merged_from", None) is not None:
                continue
            tag = "th" if c.is_header else "td"
            attrs = (f' rowspan="{c.rowspan}"' if c.rowspan > 1 else "") + (f' colspan="{c.colspan}"' if c.colspan > 1 else "")
            cells.append(f"<{tag}{attrs}>{unicodedata.normalize('NFC', str(c.value or '').strip())}</{tag}>")
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</table>")
    return "".join(out)


ARMS = {
    "V1_flatten": v1,
    "pipe_plain_notag": pipe_plain,
    "pipe_header_path": pipe_path,
    "markdown": markdown,
    "markdown_kv": markdown_kv,
    "row_anchor": row_anchor,
    "json_cols": json_cols,
    "html_span": html_span,
}

if __name__ == "__main__":
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", local_files_only=True)
    qas = json.loads((ROOT / "outputs/d04/qas_test_200.json").read_text(encoding="utf-8"))["qas"]
    tables = {str(t["table_id"]): t for t in json.loads((ROOT / "dataset/table.json").read_text(encoding="utf-8"))["table"]}
    per_q = {a: [] for a in ARMS}
    samples = {}
    for q in qas:
        t = tables[str(q["table_id"])]
        for a, f in ARMS.items():
            s = f(t)
            per_q[a].append(len(tok.encode(s, add_special_tokens=False)))
            samples.setdefault((a, q["table_id"]), s)
    base = per_q["V1_flatten"]
    rep = {}
    for a, v in per_q.items():
        srt = sorted(v)
        rep[a] = {
            "mean": round(statistics.mean(v)), "median": statistics.median(v), "p90": srt[int(0.9 * len(srt))], "max": max(v),
            "x_V1_mean": round(sum(v) / sum(base), 3), "total_tokens": sum(v),
        }
    print(json.dumps(rep, indent=1))
    tid = "3_1"
    for a in ARMS:
        print("=====", a); print(samples[(a, tid)][:700])
    json.dump(rep, open(Path(__file__).with_name("token_cost.json"), "w"), indent=1)
