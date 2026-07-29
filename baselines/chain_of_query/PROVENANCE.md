# Chain-of-Query provenance

- Local source snapshot: `D:\.UIT\KLTN\code\baselines\ChainofQuery`
- Upstream: https://github.com/SongyuanSui/ChainofQuery
- Imported for: Open-ViTabQA baseline evaluation in POMA
- Excluded: `.env`, generated outputs, temporary SQLite databases, caches,
  `ChainOfQuery_paper.pdf`, and `chain/data.zip`
- Fidelity limitation: the public/local snapshot lacks the clause agents
  imported by `utils/pipeline.py`; runs therefore retain and report the
  existing `coq_base_sql_fallback` behavior
- POMA-owned changes: callable adapter, normalized run contract, safe
  resume/overwrite handling, and repository-relative paths
