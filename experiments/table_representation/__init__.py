"""Experimental table encodings for LLM table QA.

This package does not replace Flatten V1 in the POMA pipeline. It serializes
the same parsed Open-ViTabQA grid into alternative prompt formats so later
runs can compare representation effects.
"""

from .encodings import METHOD_NAMES, EncodedTable, encode_all, encode_table

__all__ = [
    "EncodedTable",
    "METHOD_NAMES",
    "encode_all",
    "encode_table",
]
