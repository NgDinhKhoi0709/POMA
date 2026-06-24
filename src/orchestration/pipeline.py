"""
Main orchestration pipeline.

Implements the flow:
  Input -> QuestionRefiner -> Router -> Parallel(specialists)
        -> AnswerNormalization -> Final Answer

Supports selective stage execution via the ``stages`` parameter. When a
stage is skipped, its output is loaded from a ``prior_trace`` dict (saved
from a previous run) so that later stages can still consume it.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from src.agents.answer_normalization import AnswerNormalizationAgent
from src.agents.question_refiner import QuestionRefinerAgent
from src.agents.router import RouterAgent
from src.agents.specialists import SPECIALIST_REGISTRY
from src.contracts.request import QARequest
from src.contracts.responses import EvidenceItem, RefinedQuery, SpecialistResult
from src.contracts.trace import PipelineTrace
from src.errors import (
    InputDataError,
    LLMContractError,
    NoAnswerError,
    RoutingError,
    SpecialistExecutionError,
    enrich_error,
)
from src.orchestration.parallel_executor import ParallelExecutor
from src.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

STAGE_ORDER = ["refiner", "specialists", "normalization"]


def _require_dict(value: Any, *, context: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise InputDataError(f"{context} must be an object")
    return value


def _require_trace_field(data: Dict[str, Any], key: str, *, context: str) -> Any:
    if key not in data:
        raise InputDataError(f"{context} is missing field: {key}")
    return data[key]


def _require_trace_string(value: Any, *, context: str, allow_none: bool = False) -> Optional[str]:
    if value is None:
        if allow_none:
            return None
        raise InputDataError(f"{context} must be a non-empty string")
    if not isinstance(value, str) or not value.strip():
        raise InputDataError(f"{context} must be a non-empty string")
    return value.strip()


def _require_trace_list_of_strings(value: Any, *, context: str) -> List[str]:
    if not isinstance(value, list):
        raise InputDataError(f"{context} must be a list")
    items: List[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise InputDataError(f"{context} entries must be non-empty strings")
        items.append(item.strip())
    return items


def _load_refined_from_trace(step: Dict[str, Any]) -> RefinedQuery:
    data = _require_dict(step, context="Prior trace step '1_question_refiner'")
    normalized_question = _require_trace_string(
        _require_trace_field(data, "normalized_question", context="Prior trace step '1_question_refiner'"),
        context="Prior trace field 'normalized_question'",
    )
    hints = _require_trace_list_of_strings(
        _require_trace_field(data, "hints", context="Prior trace step '1_question_refiner'"),
        context="Prior trace field 'hints'",
    )
    target = _require_trace_string(
        _require_trace_field(data, "target", context="Prior trace step '1_question_refiner'"),
        context="Prior trace field 'target'",
        allow_none=True,
    )
    constraints = _require_trace_list_of_strings(
        _require_trace_field(data, "constraints", context="Prior trace step '1_question_refiner'"),
        context="Prior trace field 'constraints'",
    )

    return RefinedQuery(
        normalized_question=normalized_question,
        hints=hints,
        target=target,
        constraints=constraints,
    )


def _load_router_from_trace(step: Dict[str, Any]) -> List[str]:
    data = _require_dict(step, context="Prior trace step '2_router'")
    return _require_trace_list_of_strings(
        _require_trace_field(data, "specialist_names", context="Prior trace step '2_router'"),
        context="Prior trace field 'specialist_names'",
    )


def _load_specialists_from_trace(steps: List[Dict[str, Any]]) -> List[SpecialistResult]:
    if not isinstance(steps, list):
        raise InputDataError("Prior trace step '3_specialists' must be a list")

    results: List[SpecialistResult] = []
    for step in steps:
        data = _require_dict(step, context="Prior trace specialist entry")
        raw_evidence = _require_trace_field(
            data,
            "evidence",
            context="Prior trace specialist entry",
        )
        if not isinstance(raw_evidence, list):
            raise InputDataError("Prior trace specialist evidence must be a list")

        evidence: List[EvidenceItem] = []
        for item in raw_evidence:
            item_dict = _require_dict(item, context="Prior trace evidence entry")
            text = _require_trace_string(
                _require_trace_field(item_dict, "text", context="Prior trace evidence entry"),
                context="Prior trace evidence text",
            )
            evidence.append(
                EvidenceItem(
                    text=text,
                    row_index=item_dict.get("row_index"),
                    col=item_dict.get("col"),
                )
            )

        confidence_raw = _require_trace_field(
            data,
            "confidence",
            context="Prior trace specialist entry",
        )
        try:
            confidence = float(confidence_raw)
        except (TypeError, ValueError) as exc:
            raise InputDataError(
                "Prior trace specialist confidence must be numeric"
            ) from exc

        answer_raw = _require_trace_field(
            data,
            "answer",
            context="Prior trace specialist entry",
        )
        if answer_raw is not None and not isinstance(answer_raw, (str, int, float, bool)):
            raise InputDataError("Prior trace specialist answer must be a scalar or null")

        reason_raw = data.get("reason")
        reason: Optional[str] = None
        if reason_raw is not None:
            if not isinstance(reason_raw, (str, int, float, bool)):
                raise InputDataError("Prior trace specialist reason must be a scalar string")
            reason_text = str(reason_raw).strip()
            if reason_text:
                reason = reason_text

        results.append(
            SpecialistResult(
                agent_name=_require_trace_string(
                    _require_trace_field(data, "agent_name", context="Prior trace specialist entry"),
                    context="Prior trace specialist agent_name",
                ),
                answer=_canonicalize_specialist_answer(answer_raw),
                evidence=evidence,
                confidence=confidence,
                reason=reason,
            )
        )
    return results


def _run_specialist_task(
    agent: Any,
    refined: RefinedQuery,
    table_flattened: str,
    *,
    allow_abstain_on_failure: bool,
) -> SpecialistResult:
    try:
        return agent.run(refined, table_flattened)
    except (LLMContractError, SpecialistExecutionError) as exc:
        if not allow_abstain_on_failure:
            raise
        agent_name = getattr(agent, "name", agent.__class__.__name__)
        logger.warning(
            "Specialist %s failed and will abstain because other routed specialists remain: %s",
            agent_name,
            exc,
        )
        return SpecialistResult(
            agent_name=agent_name,
            answer="Null",
            evidence=[],
            confidence=0.0,
            reason=f"Specialist failed and abstained: {exc}",
        )


def _load_normalization_from_trace(step: Dict[str, Any]) -> Dict[str, List[str]]:
    data = _require_dict(step, context="Prior trace step '4_answer_normalization'")
    raw_answers = _require_trace_list_of_strings(
        _require_trace_field(data, "raw_answers", context="Prior trace step '4_answer_normalization'"),
        context="Prior trace field 'raw_answers'",
    )
    normalized_answers = _require_trace_list_of_strings(
        _require_trace_field(data, "normalized_answers", context="Prior trace step '4_answer_normalization'"),
        context="Prior trace field 'normalized_answers'",
    )
    return {
        "raw_answers": raw_answers,
        "normalized_answers": normalized_answers,
    }


def _is_explicit_null_answer(answer: Optional[str]) -> bool:
    if answer is None:
        return False
    return str(answer).strip().lower() == "null"


def _is_nullish_answer(answer: Optional[str]) -> bool:
    if answer is None:
        return True
    text = str(answer).strip()
    return not text or text.lower() == "null"


def _canonicalize_specialist_answer(answer: Any) -> str:
    if answer is None:
        return "Null"
    text = str(answer).strip()
    if not text:
        return "Null"
    if text.lower() == "null":
        return "Null"
    return text


def _collect_stage_answers(
    specialist_results: List[SpecialistResult],
) -> tuple[List[str], bool]:
    answers: List[str] = []
    seen: set[str] = set()
    explicit_null = False

    for result in specialist_results:
        if _is_explicit_null_answer(result.answer):
            explicit_null = True
            continue
        if _is_nullish_answer(result.answer):
            continue
        text = str(result.answer).strip()
        if text not in seen:
            seen.add(text)
            answers.append(text)

    return answers, explicit_null


def _collect_normalization_raw_answers(
    specialist_results: List[SpecialistResult],
) -> List[str]:
    answers: List[str] = []
    seen: set[str] = set()

    for result in specialist_results:
        if _is_explicit_null_answer(result.answer):
            text = "Null"
        elif _is_nullish_answer(result.answer):
            continue
        else:
            text = str(result.answer).strip()
        if text not in seen:
            seen.add(text)
            answers.append(text)

    return answers


def _resolve_specialists_stage_answer(
    specialist_results: List[SpecialistResult],
    *,
    qa_id: Optional[str],
) -> List[str]:
    answers, explicit_null = _collect_stage_answers(specialist_results)
    if answers:
        return answers
    if explicit_null:
        return ["Null"]
    raise NoAnswerError(
        "Specialists stage produced no concrete answers",
        stage="specialists",
        qa_id=qa_id,
    )


def _last_requested_stage(stages: Set[str]) -> str:
    return STAGE_ORDER[max(STAGE_ORDER.index(stage) for stage in stages)]


def _qa_id_from_request(request: QARequest) -> Optional[str]:
    qa_id = request.metadata.get("qa_id")
    if qa_id is None:
        return None
    text = str(qa_id).strip()
    return text or None


def _serialize_error(error: Exception) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "type": type(error).__name__,
        "message": getattr(error, "detail", str(error)),
        "formatted_message": str(error),
    }
    stage = getattr(error, "stage", None)
    qa_id = getattr(error, "qa_id", None)
    if stage:
        payload["stage"] = stage
    if qa_id:
        payload["qa_id"] = qa_id
    return payload


def run_pipeline(
    request: QARequest,
    stages: Optional[Set[str]] = None,
    prior_trace: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute the multi-agent pipeline and return answer + trace."""

    llm = LLMClient()
    trace = PipelineTrace()
    qa_id = _qa_id_from_request(request)
    set_qa_id = getattr(llm, "set_qa_id", None)
    if callable(set_qa_id):
        set_qa_id(qa_id)
    run_all = stages is None
    prior = (prior_trace or {}).get("steps", {})

    def _attach_trace(error: Exception) -> None:
        get_call_logs = getattr(llm, "get_call_logs", None)
        trace.llm_calls = get_call_logs() if callable(get_call_logs) else []
        trace.error = _serialize_error(error)
        setattr(error, "trace_payload", trace.to_dict())

    def _raise_with_trace(exc: Exception, *, stage: str) -> None:
        error = enrich_error(exc, stage=stage, qa_id=qa_id)
        _attach_trace(error)
        raise error from exc

    if not run_all:
        max_idx = max(STAGE_ORDER.index(stage) for stage in stages)
        needed = set(STAGE_ORDER[: max_idx + 1])
    else:
        needed = set(STAGE_ORDER)

    def _should_run(stage: str) -> bool:
        return run_all or stage in stages

    def _load_from_prior(stage: str, *keys: str) -> bool:
        if _should_run(stage) or stage not in needed:
            return False

        missing = [key for key in keys if key not in prior]
        if missing:
            missing_text = ", ".join(missing)
            raise InputDataError(
                f"Missing prior trace step(s) for stage '{stage}': {missing_text}",
                stage=stage,
                qa_id=qa_id,
            )
        return True

    refined: Optional[RefinedQuery] = None
    agent_names: Optional[List[str]] = None

    if _should_run("refiner"):
        try:
            from src.config.settings import get_settings
            settings = get_settings()
            
            # Decide active hints source based on settings toggle/request metadata.
            if request.metadata.get("hint_source") == "precomputed":
                active_hints = request.hints
                logger.info("Using precomputed predicted hints: %s", active_hints)
            elif getattr(settings, "use_agent_hints", False):
                from src.agents.hint_predictor import HintPredictorAgent
                predictor = HintPredictorAgent(llm=llm)
                active_hints = predictor.run(
                    question=request.question,
                    table_flattened=request.table_flattened,
                )
                logger.info("Using HintPredictorAgent predicted hints: %s", active_hints)
            else:
                active_hints = request.hints
                logger.info("Using dataset raw hints: %s", active_hints)

            refiner = QuestionRefinerAgent(llm=llm)
            refined = refiner.run(
                question=request.question,
                hints=active_hints,
            )
            logger.info("Refined: hints=%s, target=%s", refined.hints, refined.target)
            trace.question_refiner = {
                "normalized_question": refined.normalized_question,
                "hints": refined.hints,
                "target": refined.target,
                "constraints": refined.constraints,
            }


            agent_names = RouterAgent.route(refined.hints)
            if not agent_names:
                raise RoutingError("Router produced no specialist agents")
            logger.info("Routed to specialists: %s", agent_names)
            trace.router = {"specialist_names": agent_names}
        except Exception as exc:
            _raise_with_trace(exc, stage="refiner")
    elif _load_from_prior("refiner", "1_question_refiner", "2_router"):
        try:
            refined = _load_refined_from_trace(prior["1_question_refiner"])
            agent_names = _load_router_from_trace(prior["2_router"])
            if not agent_names:
                raise RoutingError("Prior trace router step produced no specialist agents")
            logger.info("Loaded refiner from prior trace: hints=%s", refined.hints)
            trace.question_refiner = prior["1_question_refiner"]
            trace.router = prior["2_router"]
        except Exception as exc:
            _raise_with_trace(exc, stage="refiner")

    specialist_results: Optional[List[SpecialistResult]] = None
    raw_answers: Optional[List[str]] = None

    if _should_run("specialists"):
        if refined is None or agent_names is None:
            raise InputDataError(
                "Specialists stage requires refined query and routed specialist names",
                stage="specialists",
                qa_id=qa_id,
            )
        try:
            specialist_agents = _instantiate_specialists(agent_names, llm)
            allow_abstain_on_failure = len(specialist_agents) > 1
            tasks = [
                (
                    lambda agent=agent: _run_specialist_task(
                        agent,
                        refined,
                        request.table_flattened,
                        allow_abstain_on_failure=allow_abstain_on_failure,
                    )
                )
                for agent in specialist_agents
            ]

            executor = ParallelExecutor()
            results = executor.run(tasks)
            specialist_results = []
            for result in results:
                if not isinstance(result, SpecialistResult):
                    raise SpecialistExecutionError(
                        "Specialist task returned an invalid result type"
                    )
                specialist_results.append(result)

            logger.info("Parallel done: %d specialist results", len(specialist_results))
            trace.specialists = [
                {
                    "agent_name": result.agent_name,
                    "answer": result.answer,
                    "evidence": PipelineTrace.serialize_evidence(result.evidence),
                    "confidence": result.confidence,
                    "reason": result.reason,
                }
                for result in specialist_results
            ]
            raw_answers = _collect_normalization_raw_answers(specialist_results)
        except Exception as exc:
            _raise_with_trace(exc, stage="specialists")
    elif _load_from_prior("specialists", "3_specialists"):
        try:
            specialist_results = _load_specialists_from_trace(prior["3_specialists"])
            raw_answers = _collect_normalization_raw_answers(specialist_results)
            logger.info("Loaded %d specialist results from prior trace", len(specialist_results))
            trace.specialists = [
                {
                    "agent_name": result.agent_name,
                    "answer": result.answer,
                    "evidence": PipelineTrace.serialize_evidence(result.evidence),
                    "confidence": result.confidence,
                    "reason": result.reason,
                }
                for result in specialist_results
            ]
        except Exception as exc:
            _raise_with_trace(exc, stage="specialists")

    final_answers: Optional[List[str]] = None

    if _should_run("normalization"):
        if refined is None or specialist_results is None:
            raise InputDataError(
                "Normalization stage requires refined query and specialist results",
                stage="normalization",
                qa_id=qa_id,
            )
        try:
            normalizer = AnswerNormalizationAgent(llm=llm)
            final_answers = normalizer.run_many(
                answers=[result.answer for result in specialist_results],
                question=refined.normalized_question,
                target=refined.target,
                specialist_names_by_answer=[
                    result.agent_name for result in specialist_results
                ],
            )
            logger.info("Final answers: %s", final_answers)
            trace.answer_normalization = {
                "raw_answers": raw_answers or [],
                "normalized_answers": final_answers,
            }
        except Exception as exc:
            error = enrich_error(exc, stage="normalization", qa_id=qa_id)
            trace.answer_normalization = {
                "raw_answers": raw_answers or [],
                "normalized_answers": [],
                "error": _serialize_error(error),
            }
            _attach_trace(error)
            raise error from exc
    elif _load_from_prior("normalization", "4_answer_normalization"):
        try:
            normalization_step = _load_normalization_from_trace(prior["4_answer_normalization"])
            final_answers = normalization_step["normalized_answers"]
            logger.info("Loaded normalized answers from prior trace: %s", final_answers)
            trace.answer_normalization = normalization_step
        except Exception as exc:
            _raise_with_trace(exc, stage="normalization")

    if run_all:
        if final_answers is None:
            raise NoAnswerError(
                "Full pipeline did not produce normalized answers",
                stage="normalization",
                qa_id=qa_id,
            )
        answer = final_answers
    else:
        last_stage = _last_requested_stage(stages)
        if last_stage == "refiner":
            answer = []
        elif last_stage == "specialists":
            if specialist_results is None:
                raise NoAnswerError(
                    "Specialists stage did not produce results",
                    stage="specialists",
                    qa_id=qa_id,
                )
            answer = _resolve_specialists_stage_answer(
                specialist_results,
                qa_id=qa_id,
            )
        else:
            if final_answers is None:
                raise NoAnswerError(
                    "Normalization stage did not produce answers",
                    stage="normalization",
                    qa_id=qa_id,
                )
            answer = final_answers

    get_call_logs = getattr(llm, "get_call_logs", None)
    trace.llm_calls = get_call_logs() if callable(get_call_logs) else []
    
    return {
        "answer": answer,
        "trace": trace.to_dict(),
        "prompt_tokens": getattr(llm, "total_prompt_tokens", 0),
        "completion_tokens": getattr(llm, "total_completion_tokens", 0),
        "total_tokens": getattr(llm, "total_total_tokens", 0),
        "cost_usd": getattr(llm, "total_cost_usd", 0.0),
    }


def _instantiate_specialists(agent_names: List[str], llm: LLMClient) -> list:
    agents = []
    for name in agent_names:
        cls = SPECIALIST_REGISTRY.get(name)
        if cls is None:
            raise RoutingError(f"Unknown specialist: {name}")
        agents.append(cls(llm=llm))
    return agents
