# OpenRouter JSON Schema support for GSA

Checked: 2026-07-29.

## Conclusion

OpenRouter has JSON-Schema structured outputs on compatible provider endpoints. For the proposed `GroundedSingleAnswerAgent` (GSA), the safe primary path is `POST /api/v1/chat/completions` with `response_format.type = "json_schema"`, a strict schema, and `provider.require_parameters = true`.

Current OpenRouter model metadata distinguishes the two planned backbones:

- `google/gemma-3-4b-it` advertises both `response_format` and `structured_outputs`; OpenRouter's model page also explicitly describes it as supporting structured outputs.
- `qwen/qwen3-8b` advertises `response_format`, but **not** `structured_outputs`. Therefore OpenRouter does not currently provide official metadata evidence that this slug supports strict JSON-Schema enforcement. `response_format` alone can mean output-format support (for example JSON-object mode), while `structured_outputs` is the metadata capability OpenRouter defines as JSON-Schema enforcement.

Do not assume that sending a schema to Qwen3-8B makes it strict. For a same-backbone experiment, use application-side validation and a documented retry/fallback policy for both models, and record whether native schema enforcement was available.

## Chat Completions request

OpenRouter documents this wire shape:

```json
{
  "model": "google/gemma-3-4b-it",
  "messages": [
    {
      "role": "user",
      "content": "..."
    }
  ],
  "temperature": 0,
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "grounded_single_answer",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "final_answer": {"type": "string"},
          "decision": {
            "type": "string",
            "enum": ["selected", "corrected", "synthesized", "null"]
          },
          "supporting_evidence": {
            "type": "array",
            "items": {"type": "string"}
          },
          "reason": {"type": "string"}
        },
        "required": [
          "final_answer",
          "decision",
          "supporting_evidence",
          "reason"
        ],
        "additionalProperties": false
      }
    }
  },
  "provider": {
    "require_parameters": true
  }
}
```

The documented result is JSON text in `choices[0].message.content`, so the client must still parse it and validate it against the same schema. OpenRouter also documents streaming support, but a non-streaming GSA call is simpler to validate and audit.

Source: [OpenRouter Structured Outputs](https://openrouter.ai/docs/guides/features/structured-outputs).

## What `strict: true` does—and does not guarantee

OpenRouter recommends `strict: true`, but explicitly warns that enforcement varies by provider endpoint. A provider with native strict mode may enforce the schema exactly; another may translate it into its own structured-output format or treat it as a strong hint. Strict modes may also accept only a subset of JSON Schema.

Accordingly:

1. Keep the schema simple: object, scalar fields, enum, array of strings, every property required, and `additionalProperties: false`.
2. Validate client-side even when the provider advertises `structured_outputs`.
3. Log parse/validation failures and retries as experiment metadata.
4. Do not silently switch to a stronger model to repair output, because that would violate the same-backbone design.

Source: [OpenRouter Structured Outputs — model support and strict-mode caveat](https://openrouter.ai/docs/guides/features/structured-outputs).

## Discovering model and provider support

OpenRouter says structured-output support is determined **per endpoint**, not merely per model, and may change. Its recommended routing sequence is:

1. inspect the model/provider's supported parameters;
2. send the schema request;
3. set `provider.require_parameters: true` so routing is limited to endpoints that support the requested parameters.

Programmatic model-level discovery:

```text
GET https://openrouter.ai/api/v1/models
GET https://openrouter.ai/api/v1/models?supported_parameters=structured_outputs
GET https://openrouter.ai/api/v1/model/{author}/{slug}
```

Programmatic provider-endpoint discovery (requires authentication):

```text
GET https://openrouter.ai/api/v1/models/{author}/{slug}/endpoints
```

OpenRouter defines `supported_parameters` values separately:

- `response_format`: output-format specification;
- `structured_outputs`: JSON-Schema enforcement.

Sources: [OpenRouter Models guide](https://openrouter.ai/docs/guides/overview/models), [List model endpoints](https://openrouter.ai/docs/api/api-reference/endpoints/list-endpoints), and the live [Models API](https://openrouter.ai/api/v1/models).

### Live metadata for the planned backbones

The live Models API returned:

| Model | `response_format` | `structured_outputs` | Interpretation |
|---|---:|---:|---|
| `google/gemma-3-4b-it` | yes | yes | Official metadata supports attempting strict JSON Schema. |
| `qwen/qwen3-8b` | yes | no | Official metadata supports response formatting, but not a claim of strict schema enforcement. |

The Gemma model page independently says the model includes structured-output capability. Sources: [Gemma 3 4B model page](https://openrouter.ai/google/gemma-3-4b-it) and [live Models API](https://openrouter.ai/api/v1/models).

Because capability metadata and provider inventory are mutable, save a timestamped copy of the relevant model/endpoint metadata with each experimental run.

## Responses API

OpenRouter also exposes the beta, stateless `POST /api/v1/responses` endpoint and describes it as using the OpenResponses format. Its API reference includes a top-level `text` object for output configuration. OpenRouter's official Python SDK types put JSON Schema under `text.format`:

```json
{
  "model": "google/gemma-3-4b-it",
  "input": "...",
  "temperature": 0,
  "text": {
    "format": {
      "type": "json_schema",
      "name": "grounded_single_answer",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "final_answer": {"type": "string"},
          "decision": {
            "type": "string",
            "enum": ["selected", "corrected", "synthesized", "null"]
          },
          "supporting_evidence": {
            "type": "array",
            "items": {"type": "string"}
          },
          "reason": {"type": "string"}
        },
        "required": [
          "final_answer",
          "decision",
          "supporting_evidence",
          "reason"
        ],
        "additionalProperties": false
      }
    }
  },
  "provider": {
    "require_parameters": true
  }
}
```

The official SDK schema defines the fields `type`, `name`, `description`, `schema`, and `strict`. OpenRouter's Responses API is currently beta and may introduce breaking changes, so Chat Completions is the lower-risk choice for the immediate experiments unless the repository already standardizes on Responses.

Sources: [OpenRouter Responses API overview](https://openrouter.ai/docs/api/reference/responses/overview), [OpenRouter create-response reference](https://openrouter.ai/docs/api/api-reference/responses/create-responses), [official `TextExtendedConfig` SDK type](https://github.com/OpenRouterTeam/python-sdk/blob/main/src/openrouter/components/textextendedconfig.py), [official JSON-Schema format type](https://github.com/OpenRouterTeam/python-sdk/blob/main/src/openrouter/components/formatjsonschemaconfig.py), and [official Responses request type](https://github.com/OpenRouterTeam/python-sdk/blob/main/src/openrouter/components/responsesrequest.py).

## Recommended experimental policy

- Use the same GSA schema, prompt, temperature, token limit, parser, validator, and retry count for POMA and every baseline.
- Use same-backbone GSA: Qwen run → Qwen GSA; Gemma run → Gemma GSA.
- For Gemma, request native JSON Schema with `require_parameters: true`.
- For Qwen3-8B, first make a small capability probe. If OpenRouter rejects `json_schema` when parameters are required, fall back to `json_object` or prompt-only JSON plus the **same** client validator/retry policy, and report this asymmetry.
- Report at least: native-schema availability, valid-on-first-attempt rate, retry rate, terminal invalid rate, and GSA decision distribution.
- Treat response-healing as a separate ablation if used. OpenRouter describes it as a plugin that can repair malformed non-streaming JSON; enabling it only for one backbone would add another model-dependent intervention.

Source for response healing: [OpenRouter Response Healing](https://openrouter.ai/docs/guides/features/plugins/response-healing).
