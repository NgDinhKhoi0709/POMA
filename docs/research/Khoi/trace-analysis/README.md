# trace-analysis — offline POMA output analysis (2026-09-18)

Offline analysis of existing POMA outputs (GitHub `NgDinhKhoi0709/POMA`, HEAD `50e3a217`). No LLM/API calls.
Read `gate_headroom_report.md` first; all numbers are in `gate_headroom_results.json`.

Re-running: clone the repo into a folder named `poma_repo` next to this folder
(the scripts use `REPO = HERE.parent / "poma_repo"` in `common.py`), then run
`q1_integrity.py` -> `build_instances.py` -> `analysis.py` -> `q8_q11.py` -> `refine.py` -> `q1_extra.py`
with `PYTHONIOENCODING=utf-8`.
