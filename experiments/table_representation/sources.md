# Crawled sources (2026-09-17)

Browser and HTML fetches used for `REPORT.md`. Screenshots live in `screenshots/`. Numbers quoted in the report come from the paper HTML/PDF text, not from screenshot OCR.

## Primary papers (opened in browser)

| Paper | Venue / date | URL | Local screenshot |
|---|---|---|---|
| Table Meets LLM (Sui et al.) | WSDM 2024 | https://arxiv.org/abs/2305.13062 | `screenshots/table_meets_llm_table2.webp` |
| Table Meets LLM HTML | same | https://arxiv.org/html/2305.13062v5 | same |
| SpreadsheetLLM (Tian, Zhao, Dong et al.) | arXiv 2024 | https://arxiv.org/abs/2407.09025 | `screenshots/spreadsheetllm_abs.webp` |
| TableLlama (Zhang et al.) | NAACL 2024 | https://arxiv.org/abs/2311.09206 | — |
| Chain-of-Table (Wang et al.) | ICLR 2024 | https://arxiv.org/abs/2401.04398 | `screenshots/chain_of_table_abs.webp` |
| TABVERSE (Ahsan et al.) | arXiv 2026 | https://arxiv.org/abs/2606.09578 | — |
| TABVERSE project page | 2026 | https://mbzuai-nlp.github.io/TABVERSE/ | `screenshots/tabverse_homepage.webp` |
| Tabular Representation, Noisy Operators (Singha et al.) | arXiv 2023 | https://arxiv.org/abs/2310.10358 | `screenshots/singha_tabular_representation.webp` |
| LLM for Table Processing survey (Lu et al.) | FCS / arXiv 2024 | https://arxiv.org/html/2402.05121v3 | `screenshots/survey_text_representation.webp` |
| Tabular Data Understanding survey (Wu, Ritter, Xu) | arXiv 2025 | https://arxiv.org/html/2508.00217v1 | — |
| arXiv search: table representation LLM serialization | 2026-09-17 | https://arxiv.org/search/?query=table+representation+LLM+serialization&searchtype=all | `screenshots/arxiv_search_table_representation.webp` |

## Additional papers fetched as HTML/PDF

| Paper | URL |
|---|---|
| TAPAS (Herzig et al., ACL 2020) | https://aclanthology.org/2020.acl-main.398.pdf |
| TaBERT (Yin et al., ACL 2020) | https://aclanthology.org/2020.acl-main.745.pdf |
| TAPEX tokenizer / linearizer | https://huggingface.co/docs/transformers/model_doc/tapex |
| TUTA (Wang et al., 2020) | https://arxiv.org/pdf/2010.12537 |
| TableFormer (Yang et al., ACL 2022) | https://aclanthology.org/2022.acl-long.40.pdf |
| OmniTab (Jiang et al., NAACL 2022) | https://arxiv.org/html/2207.03637 |
| Binder (Cheng et al., 2023) | https://arxiv.org/pdf/2210.02875v2 |
| StructGPT (Jiang et al., EMNLP 2023) | https://aclanthology.org/2023.emnlp-main.574/ |
| Rethinking Tabular Data Understanding (Liu, Wang, Chen, NAACL 2024) | https://aclanthology.org/2024.naacl-long.26.pdf |
| TQA-Bench / serialization format study | https://openreview.net/pdf?id=hxEHr5gJBY |
| Open-ViTabQA dataset card | https://github.com/DuzDao/Open-ViTabQA |
| Open-ViTabQA (Dao et al., KBS 2025) | https://doi.org/10.1016/j.knosys.2025.114391 |
| Improving Agents: 11 table formats | https://www.improvingagents.com/blog/best-input-data-format-for-llms/ |
| Semantic Scholar search | https://www.semanticscholar.org/search?q=table%20serialization%20LLM%20markdown%20HTML&sort=relevance |

## Table shrinking / pruning papers (2026-09-17)

| Paper | URL |
|---|---|
| TAP4LLM (Sui et al., EMNLP 2024 Findings) | https://aclanthology.org/2024.findings-emnlp.603.pdf |
| DATER (Ye et al., 2023) | https://arxiv.org/pdf/2301.13808 |
| StructGPT (Jiang et al., EMNLP 2023) | https://aclanthology.org/2023.emnlp-main.574.pdf |
| ATF Adaptive Table Filtering (2025) | https://arxiv.org/html/2506.23463 |
| TableRAG (Chen et al., 2024) | https://arxiv.org/pdf/2410.04739 |
| TabSQLify (Nahid & Rafiei, NAACL 2024) | https://arxiv.org/html/2404.10150v1 |
| ITR Inner Table Retriever (Lin et al., ACL 2023) | https://aclanthology.org/2023.acl-long.551/ |
| CABINET (ICLR 2024) | https://proceedings.iclr.cc/paper_files/paper/2024/file/19a42d5885e25e51852aca8144e5af0d-Paper-Conference.pdf |
| TabTrim (ACL 2026) | https://aclanthology.org/2026.acl-long.591/ |
| STR / TripletQL (2026) | https://arxiv.org/html/2605.31550v1 |
| TaBERT content snapshot (Yin et al., ACL 2020) | https://aclanthology.org/2020.acl-main.745.pdf |

## Access notes

- Crawl date: 2026-09-17.
- Table Meets LLM Table 2 numbers were copied from the arXiv HTML, then checked against the browser screenshot of the same table.
- TABVERSE findings were taken from the project page text, not from a PDF table that was only partially visible.
- Elsevier / Knowledge-Based Systems full text for Open-ViTabQA was not open in the browser; Flatten V1 is documented from this repository and from `paper/jit-article.tex`.
