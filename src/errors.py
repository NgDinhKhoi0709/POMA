"""POMA runtime exception hierarchy."""

from __future__ import annotations


class POMAError(RuntimeError):
    """Base error for fail-fast runtime failures."""

    default_message = "POMA runtime failure"

    def __init__(
        self,
        message: str | None = None,
        *,
        stage: str | None = None,
        qa_id: str | None = None,
    ) -> None:
        self.detail = message or self.default_message
        self.stage = stage
        self.qa_id = qa_id
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        context: list[str] = []
        if self.stage:
            context.append(f"stage={self.stage}")
        if self.qa_id:
            context.append(f"qa_id={self.qa_id}")
        if not context:
            return self.detail
        return f"[{' '.join(context)}] {self.detail}"


class InputDataError(POMAError):
    default_message = "Invalid input data"


class LLMContractError(POMAError):
    default_message = "Invalid LLM response contract"


class RoutingError(POMAError):
    default_message = "Invalid routing configuration"


class SpecialistExecutionError(POMAError):
    default_message = "Specialist execution failed"


class NoAnswerError(POMAError):
    default_message = "Pipeline produced no answer"


def enrich_error(
    error: Exception,
    *,
    stage: str | None = None,
    qa_id: str | None = None,
    error_cls: type[POMAError] | None = None,
) -> POMAError:
    """Return a POMA error enriched with stage and qa_id context."""

    resolved_stage = stage or getattr(error, "stage", None)
    resolved_qa_id = qa_id or getattr(error, "qa_id", None)

    if isinstance(error, POMAError):
        cls = error_cls or type(error)
        if (
            isinstance(error, cls)
            and error.stage == resolved_stage
            and error.qa_id == resolved_qa_id
        ):
            return error
        return cls(error.detail, stage=resolved_stage, qa_id=resolved_qa_id)

    cls = error_cls or POMAError
    return cls(str(error), stage=resolved_stage, qa_id=resolved_qa_id)
