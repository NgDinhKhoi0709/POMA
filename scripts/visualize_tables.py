"""
Export Open-ViTabQA tables to static HTML files.

Examples:
    python scripts/visualize_tables.py
    python scripts/visualize_tables.py --limit 10
    python scripts/visualize_tables.py --table-id 55_4 --table-id 99915_2
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set, Tuple

WINDOWS_RESERVED_FILENAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    "com1",
    "com2",
    "com3",
    "com4",
    "com5",
    "com6",
    "com7",
    "com8",
    "com9",
    "lpt1",
    "lpt2",
    "lpt3",
    "lpt4",
    "lpt5",
    "lpt6",
    "lpt7",
    "lpt8",
    "lpt9",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualize tables from dataset/table.json into HTML files.",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="dataset/table.json",
        help="Path to tables JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="dataset/visualize",
        help="Directory where HTML files will be written.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of tables to export after applying filters.",
    )
    parser.add_argument(
        "--table-id",
        action="append",
        default=[],
        help=(
            "Optional table_id filter. Use multiple times or comma-separated values, "
            "for example: --table-id 55_4 --table-id 99915_2"
        ),
    )
    return parser.parse_args()


def load_tables(input_path: Path) -> List[Dict[str, Any]]:
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    raw_tables: Any
    if isinstance(data, dict):
        raw_tables = data.get("table", data)
    else:
        raw_tables = data

    tables: List[Dict[str, Any]] = []

    if isinstance(raw_tables, list):
        for idx, item in enumerate(raw_tables):
            if not isinstance(item, dict):
                continue
            table = dict(item)
            table.setdefault("table_id", f"table_{idx + 1}")
            tables.append(table)
        return tables

    if isinstance(raw_tables, dict):
        for key, value in raw_tables.items():
            if not isinstance(value, dict):
                continue
            table = dict(value)
            table.setdefault("table_id", str(key))
            tables.append(table)
        return tables

    raise ValueError(f"Unsupported table payload type: {type(raw_tables)}")


def parse_table_id_filters(raw_filters: Sequence[str]) -> Set[str]:
    filters: Set[str] = set()
    for item in raw_filters:
        for token in str(item).split(","):
            token = token.strip()
            if token:
                filters.add(token)
    return filters


def sanitize_filename(value: str, fallback: str = "table") -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback

    text = re.sub(r'[<>:"/|?*\x00-\x1F]', "_", text)
    text = text.replace(" ", "_")
    text = re.sub(r"_+", "_", text).strip("._")

    if not text:
        text = fallback

    if text.lower() in WINDOWS_RESERVED_FILENAMES:
        text = f"{text}_table"

    return text[:120]


def uniquify_name(base_name: str, used_names: Dict[str, int]) -> str:
    count = used_names.get(base_name, 0)
    used_names[base_name] = count + 1

    if count == 0:
        return base_name
    return f"{base_name}_dup{count}"


def to_rows(table: Dict[str, Any]) -> List[List[str]]:
    table_dict = table.get("table_dict", {})

    rows: Any = []
    if isinstance(table_dict, dict):
        rows = table_dict.get("table_rows", [])
    elif isinstance(table_dict, list):
        rows = table_dict

    if not isinstance(rows, list):
        return []

    normalized: List[List[str]] = []
    for row in rows:
        if isinstance(row, list):
            normalized.append([str(cell) for cell in row])
        else:
            normalized.append([str(row)])

    return normalized


def render_rows_table(rows: List[List[str]]) -> str:
    if not rows:
        return '<p class="note">No table rows available.</p>'

    header = rows[0]
    body = rows[1:]

    parts: List[str] = []
    parts.append('<table class="fallback-table">')
    parts.append("<thead><tr>")
    for cell in header:
        parts.append(f"<th>{html.escape(cell)}</th>")
    parts.append("</tr></thead>")
    parts.append("<tbody>")

    for row in body:
        parts.append("<tr>")
        for cell in row:
            parts.append(f"<td>{html.escape(cell)}</td>")
        parts.append("</tr>")

    parts.append("</tbody>")
    parts.append("</table>")
    return "".join(parts)


def render_table_page(table: Dict[str, Any]) -> Tuple[str, str]:
    table_id = str(table.get("table_id", ""))
    title = str(table.get("table_title", ""))
    domain = str(table.get("table_domain", ""))

    table_types = table.get("table_type", [])
    if isinstance(table_types, list):
        table_types_text = ", ".join(str(t) for t in table_types) if table_types else "-"
    else:
        table_types_text = str(table_types)

    raw_html = str(table.get("table_html") or "").strip()
    source = "table_html"

    if raw_html:
        table_block = raw_html
    else:
        source = "table_dict"
        table_block = render_rows_table(to_rows(table))

    safe_title = html.escape(title or table_id or "Untitled table")

    page = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title}</title>
  <style>
    :root {{
      --bg: #f4f6fb;
      --panel: #ffffff;
      --text: #14213d;
      --muted: #5a6478;
      --line: #d8dde8;
      --head: #eaf0ff;
      --chip: #eef2f8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, sans-serif;
      color: var(--text);
      background: radial-gradient(circle at top right, #dfe9ff, var(--bg) 35%);
    }}
    .page {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      box-shadow: 0 10px 24px rgba(20, 33, 61, 0.08);
      padding: 16px;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 1.3rem;
      line-height: 1.35;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }}
    .item {{
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      background: #fcfdff;
    }}
    .item b {{
      display: block;
      color: var(--muted);
      font-size: 0.84rem;
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .chip {{
      display: inline-block;
      margin-top: 10px;
      border-radius: 999px;
      background: var(--chip);
      border: 1px solid var(--line);
      padding: 4px 10px;
      font-size: 0.85rem;
      color: var(--muted);
    }}
    .table-wrap {{
      overflow: auto;
      margin-top: 16px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fff;
    }}
    .table-wrap table {{
      border-collapse: collapse;
      width: max-content;
      min-width: 100%;
      font-size: 0.92rem;
    }}
    .table-wrap th,
    .table-wrap td {{
      border: 1px solid var(--line);
      padding: 8px 10px;
      vertical-align: top;
    }}
    .table-wrap th {{
      background: var(--head);
      position: sticky;
      top: 0;
      z-index: 1;
    }}
    .note {{
      margin: 12px 0;
      color: #7a4f00;
      background: #fff8e5;
      border: 1px solid #f7dfa3;
      border-radius: 8px;
      padding: 10px;
    }}
    a {{ color: #174ea6; }}
  </style>
</head>
<body>
  <main class="page">
    <section class="panel">
      <h1>{safe_title}</h1>
      <div class="meta">
        <div class="item"><b>table_id</b>{html.escape(table_id or "-")}</div>
        <div class="item"><b>table_domain</b>{html.escape(domain or "-")}</div>
        <div class="item"><b>table_type</b>{html.escape(table_types_text)}</div>
      </div>
      <span class="chip">Source: {html.escape(source)}</span>
      <div class="table-wrap">
        {table_block}
      </div>
    </section>
  </main>
</body>
</html>
"""

    return page, source


def render_index_page(records: List[Dict[str, str]]) -> str:
    rows: List[str] = []
    for rec in records:
        rows.append(
            "<tr>"
            f"<td><a href=\"{html.escape(rec['file_name'])}\">{html.escape(rec['table_id'])}</a></td>"
            f"<td>{html.escape(rec['table_title'])}</td>"
            f"<td>{html.escape(rec['table_domain'])}</td>"
            f"<td>{html.escape(rec['table_type'])}</td>"
            f"<td>{html.escape(rec['source'])}</td>"
            "</tr>"
        )

    table_rows_html = "".join(rows)

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Open-ViTabQA Table Visualizations</title>
  <style>
    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, sans-serif;
      background: #f2f4fa;
      color: #14213d;
    }}
    .page {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 24px;
    }}
    .panel {{
      background: #fff;
      border: 1px solid #d8dde8;
      border-radius: 12px;
      padding: 18px;
      box-shadow: 0 10px 24px rgba(20, 33, 61, 0.08);
    }}
    h1 {{ margin-top: 0; }}
    .sub {{ color: #5a6478; margin-bottom: 12px; }}
    .table-wrap {{ overflow: auto; border: 1px solid #d8dde8; border-radius: 10px; }}
    table {{ border-collapse: collapse; width: 100%; min-width: 860px; }}
    th, td {{ border: 1px solid #d8dde8; padding: 8px 10px; text-align: left; }}
    th {{ background: #eaf0ff; position: sticky; top: 0; }}
    a {{ color: #174ea6; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <main class="page">
    <section class="panel">
      <h1>Open-ViTabQA Table Visualizations</h1>
      <p class="sub">Total exported tables: {len(records)}</p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>table_id</th>
              <th>table_title</th>
              <th>table_domain</th>
              <th>table_type</th>
              <th>source</th>
            </tr>
          </thead>
          <tbody>
            {table_rows_html}
          </tbody>
        </table>
      </div>
    </section>
  </main>
</body>
</html>
"""


def export_tables(
    tables: List[Dict[str, Any]],
    output_dir: Path,
    limit: int | None,
    table_id_filters: Set[str],
) -> Tuple[int, int, int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)

    used_names: Dict[str, int] = {}
    records: List[Dict[str, str]] = []

    exported = 0
    fallback_count = 0
    skipped = 0
    errors = 0

    for idx, table in enumerate(tables):
        table_id = str(table.get("table_id") or f"table_{idx + 1}")

        if table_id_filters and table_id not in table_id_filters:
            skipped += 1
            continue

        if limit is not None and exported >= limit:
            break

        try:
            page_html, source = render_table_page(table)
            if source == "table_dict":
                fallback_count += 1

            base_name = sanitize_filename(table_id)
            unique_name = uniquify_name(base_name, used_names)
            file_name = f"{unique_name}.html"

            output_path = output_dir / file_name
            output_path.write_text(page_html, encoding="utf-8")

            table_title = str(table.get("table_title") or "")
            table_domain = str(table.get("table_domain") or "")
            table_type = table.get("table_type", [])
            table_type_text = ", ".join(str(t) for t in table_type) if isinstance(table_type, list) else str(table_type)

            records.append(
                {
                    "table_id": table_id,
                    "file_name": file_name,
                    "table_title": table_title,
                    "table_domain": table_domain,
                    "table_type": table_type_text or "-",
                    "source": source,
                }
            )
            exported += 1
        except Exception as exc:  # pragma: no cover - defensive for dirty data
            errors += 1
            print(f"[WARN] Failed to export table_id={table_id!r}: {exc}")

    records.sort(key=lambda rec: rec["table_id"])
    index_html = render_index_page(records)
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")

    return exported, fallback_count, skipped, errors


def main() -> int:
    args = parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        return 1

    try:
        tables = load_tables(input_path)
    except Exception as exc:
        print(f"[ERROR] Could not load tables from {input_path}: {exc}")
        return 1

    if not tables:
        print("[ERROR] No tables were found in the input data.")
        return 1

    table_id_filters = parse_table_id_filters(args.table_id)

    exported, fallback_count, skipped, errors = export_tables(
        tables=tables,
        output_dir=output_dir,
        limit=args.limit,
        table_id_filters=table_id_filters,
    )

    print("\n=== Visualization Export Summary ===")
    print(f"Input file     : {input_path}")
    print(f"Output folder  : {output_dir}")
    print(f"Loaded tables  : {len(tables)}")
    if table_id_filters:
        print(f"Filter table_id: {len(table_id_filters)} item(s)")
    print(f"Exported files : {exported} table page(s) + index.html")
    print(f"Fallback count : {fallback_count}")
    print(f"Skipped tables : {skipped}")
    print(f"Error count    : {errors}")

    if exported == 0:
        print("[WARN] No table pages exported. Check your filters or input format.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
