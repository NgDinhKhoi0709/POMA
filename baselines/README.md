# Vendored baselines

This directory contains source snapshots of CoAgt and Chain-of-Query plus
POMA-owned Open-ViTabQA adapters. See each `PROVENANCE.md` for the source and
local modifications.

The available Chain-of-Query snapshot does not publish the clause-agent
modules used by the full paper pipeline. Its adapter therefore retains the
source's `coq_base_sql_fallback` mode and reports that limitation in every run.
