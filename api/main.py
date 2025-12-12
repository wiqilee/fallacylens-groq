from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

from fallacylens.detector import FallacyDetector
from fallacylens.models import AnalysisResult


app = FastAPI(
    title="FallacyLens API (Groq Edition)",
    description="AI-powered logical fallacy detection service using Groq LLMs.",
    version="0.4.0",
)

detector = FallacyDetector()


class AnalyzeRequest(BaseModel):
    text: str


class FallacySpanResponse(BaseModel):
    start: int
    end: int
    text: str
    fallacy_type: str
    confidence: float
    severity: int
    explanation: str
    suggestion: Optional[str] = None


class AnalyzeResponse(BaseModel):
    original_text: str
    clarity_score: float
    persuasion_score: float
    reliability_score: float
    has_fallacies: bool
    fallacies: List[FallacySpanResponse]


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze a single piece of text and return detected fallacies + scores."""
    result: AnalysisResult = detector.analyze(req.text)

    clarity = getattr(result, "clarity_score", 50.0)
    persuasion = getattr(result, "persuasion_score", 50.0)
    reliability = getattr(result, "reliability_score", 50.0)

    fallacies = [
        FallacySpanResponse(
            start=f.start,
            end=f.end,
            text=f.text,
            fallacy_type=f.fallacy_type,
            confidence=f.confidence,
            severity=f.severity,
            explanation=f.explanation,
            suggestion=f.suggestion,
        )
        for f in result.fallacies
    ]

    return AnalyzeResponse(
        original_text=result.original_text,
        clarity_score=clarity,
        persuasion_score=persuasion,
        reliability_score=reliability,
        has_fallacies=result.has_fallacies,
        fallacies=fallacies,
    )
