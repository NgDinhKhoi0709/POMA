from .what import WhatAgent
from .where import WhereAgent
from .who import WhoAgent
from .when import WhenAgent
from .why import WhyAgent
from .how import HowAgent
from .yesno import YesNoAgent
from .list import ListAgent
from .mathematical_reasoning import MathematicalReasoningAgent
from .multi_conditions import MultiConditionsAgent

SPECIALIST_REGISTRY: dict[str, type] = {
    "What": WhatAgent,
    "Where": WhereAgent,
    "Who": WhoAgent,
    "When": WhenAgent,
    "Why": WhyAgent,
    "How": HowAgent,
    "YesNo": YesNoAgent,
    "List": ListAgent,
    "MathematicalReasoning": MathematicalReasoningAgent,
    "MultiConditions": MultiConditionsAgent,
}

__all__ = [
    "HowAgent",
    "ListAgent",
    "MathematicalReasoningAgent",
    "MultiConditionsAgent",
    "SPECIALIST_REGISTRY",
    "WhatAgent",
    "WhenAgent",
    "WhereAgent",
    "WhoAgent",
    "WhyAgent",
    "YesNoAgent",
]
