"""Domain exceptions for evaluation input and execution."""


class EvaluationDataError(ValueError):
    """Raised when evaluation input does not meet the public schema."""


class CandidatePolicyError(EvaluationDataError):
    """Raised when a prediction cannot satisfy a candidate policy."""

    error_code = "candidate-policy-error"

    def __init__(self, candidate_count: int) -> None:
        self.candidate_count = candidate_count
        super().__init__(
            f"candidate policy requires a different candidate count; got "
            f"K={candidate_count}"
        )


class EmptyCandidateError(CandidatePolicyError):
    """Raised when a policy requiring one candidate receives K=0."""

    error_code = "empty-candidates"


class MultipleCandidatesError(CandidatePolicyError):
    """Raised when a policy requiring one candidate receives K>1."""

    error_code = "multiple-candidates"

