from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FallacySpan:
    """Represents a single detected fallacy span in the text."""

    start: int
    end: int
    text: str
    fallacy_type: str
    confidence: float
    severity: int
    explanation: str
    suggestion: Optional[str] = None


@dataclass
class AnalysisResult:
    """Result object for a single analyzed text."""

    original_text: str
    fallacies: List[FallacySpan]

    @property
    def has_fallacies(self) -> bool:
        return len(self.fallacies) > 0
