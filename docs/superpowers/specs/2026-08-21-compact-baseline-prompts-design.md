# Compact baseline prompts

## Scope

Simplify all four templates in `baseline/prompts.py` while preserving their experimental strategies: zero-shot, chain-of-thought, task decomposition, and few-shot.

## Output contract

Every strategy must return exactly one JSON object:

```json
{"final_answer": "answer"}
```

`final_answer` is a string when the table supports an answer and JSON `null` otherwise. No reasoning, subproblems, Markdown fences, or surrounding prose may be emitted.

## Prompt behavior

All prompts receive `TABLE_STR` and `QUESTION`, use only table evidence, and request a concise answer. Chain-of-thought and task decomposition perform their named strategy internally without exposing intermediate reasoning. Few-shot retains only short examples needed to demonstrate the output contract.

## API and metadata

Remove prompt-version constants, lookup, resolver, output metadata, and tuple returns. `build_tableqa_prompt(...)` returns only the prompt string. Keep prompt-style validation and per-style schema names, but make all four baseline schemas share the nullable `final_answer` shape to avoid unrelated output-format changes.

## Verification

Update focused baseline tests to assert that every style includes the table, question, and only the `final_answer` contract; verify JSON `null` guidance and absence of prompt-version metadata.
