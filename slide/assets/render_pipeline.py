"""Dựng SVG cho slide từ file draw.io: hình và nhãn lấy từ memxam-pipeline.drawio, đường nối lấy
đúng các điểm draw.io tự định tuyến (edges.json, xuất từ app.diagrams.net). SVG chỉ dùng <text>,
không có foreignObject, để Typst hiển thị được.

python slide/assets/render_pipeline.py
"""

from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).parent
SRC, EDGES, OUT = HERE / "memxam-pipeline.drawio", HERE / "memxam-pipeline.edges.json", HERE / "memxam-pipeline.svg"
FONT = "Arial, Helvetica, sans-serif"


def style(s: str) -> dict[str, str]:
    out = {}
    for part in (s or "").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
        elif part:
            out[part] = "1"
    return out


def lines(value: str) -> list[list[tuple[str, bool, bool]]]:
    """Nhãn HTML của draw.io → các dòng, mỗi dòng là các đoạn (chữ, đậm, nghiêng)."""
    out = []
    for raw in re.split(r"<br\s*/?>", value):
        segs, bold, ital = [], False, False
        for tok in re.split(r"(</?[bi]>)", raw):
            if tok in ("<b>", "</b>"):
                bold = tok == "<b>"
            elif tok in ("<i>", "</i>"):
                ital = tok == "<i>"
            elif tok:
                segs.append((html.unescape(re.sub(r"<[^>]+>", "", tok)), bold, ital))
        out.append(segs)
    return out


def text_block(cx: float, cy: float, value: str, size: float, color: str, italic: bool, anchor: str = "middle") -> str:
    ls = lines(value)
    lh = size * 1.3
    y0 = cy - lh * (len(ls) - 1) / 2 + size * 0.35
    parts = []
    for i, segs in enumerate(ls):
        spans = "".join(
            f'<tspan font-weight="{"bold" if b else "normal"}" font-style="{"italic" if (it or italic) else "normal"}">'
            f"{html.escape(t)}</tspan>" for t, b, it in segs)
        parts.append(f'<text x="{cx}" y="{y0 + i * lh:.1f}" text-anchor="{anchor}" font-family="{FONT}" '
                     f'font-size="{size}" fill="{color}">{spans}</text>')
    return "".join(parts)


def main() -> None:
    root = ET.parse(SRC).getroot().find(".//root")
    edges = json.loads(EDGES.read_text(encoding="utf-8"))
    cells = {c.get("id"): c for c in root.iter("mxCell")}
    body = ['<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#000"/></marker></defs>',
            '<rect x="0" y="0" width="1630" height="570" fill="#ffffff"/>']
    labels = []
    for cid, c in cells.items():
        st, g = style(c.get("style")), c.find("mxGeometry")
        if c.get("vertex") == "1" and g is not None:
            x, y, w, h = (float(g.get(k, 0)) for k in ("x", "y", "width", "height"))
            fill = st.get("fillColor", "none")
            stroke = st.get("strokeColor", "#000000") if st.get("strokeColor") != "none" else "none"
            dash = ' stroke-dasharray="6 4"' if st.get("dashed") == "1" else ""
            if "text" in st:
                pass
            elif st.get("shape") == "cylinder3":
                ry = 10
                body.append(f'<path d="M{x},{y + ry} A{w / 2},{ry} 0 0 1 {x + w},{y + ry} L{x + w},{y + h - ry} '
                            f'A{w / 2},{ry} 0 0 1 {x},{y + h - ry} Z" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>'
                            f'<path d="M{x},{y + ry} A{w / 2},{ry} 0 0 0 {x + w},{y + ry}" fill="none" stroke="{stroke}" stroke-width="1.2"/>')
                y, h = y + 2 * ry, h - 2 * ry
            elif "rhombus" in st:
                body.append(f'<path d="M{x + w / 2},{y} L{x + w},{y + h / 2} L{x + w / 2},{y + h} L{x},{y + h / 2} Z" '
                            f'fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
            else:
                r = 0 if st.get("rounded") != "1" else (6 if cid == "frame" else min(w, h) * 0.15)
                body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" '
                            f'stroke="{stroke}" stroke-width="1.2"{dash}/>')
            if c.get("value"):
                size = float(st.get("fontSize", 11)) + 1
                color = st.get("fontColor", "#000000")
                italic = st.get("fontStyle") == "2"
                if st.get("align") == "left":
                    labels.append(text_block(x, y + h / 2, c.get("value"), size, color, italic, "start"))
                else:
                    labels.append(text_block(x + w / 2, y + h / 2, c.get("value"), size, color, italic))
        elif c.get("edge") == "1" and cid in edges:
            pts = " ".join(f"{px},{py}" for px, py in edges[cid]["p"])
            if st.get("endArrow") == "none":
                body.append(f'<polyline points="{pts}" fill="none" stroke="#999999" stroke-width="1" stroke-dasharray="6 4"/>')
            else:
                body.append(f'<polyline points="{pts}" fill="none" stroke="#000000" stroke-width="1.3" marker-end="url(#ar)"/>')
            if c.get("value") and edges[cid]["l"]:
                lx, ly = edges[cid]["l"]
                txt = html.unescape(re.sub(r"<[^>]+>", "", c.get("value")))
                wbox = len(txt) * 6.2 + 8
                labels.append(f'<rect x="{lx - wbox / 2:.1f}" y="{ly - 8}" width="{wbox:.1f}" height="16" fill="#ffffff"/>'
                              + text_block(lx, ly, c.get("value"), 11, "#000000", True))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 10 1610 550" width="1610" height="550">'
           + "".join(body) + "".join(labels) + "</svg>")
    OUT.write_text(svg, encoding="utf-8")
    print(OUT, len(svg))


if __name__ == "__main__":
    main()
