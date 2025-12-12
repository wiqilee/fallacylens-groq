import os
import json
from typing import List, Optional

from groq import Groq

from .models import AnalysisResult, FallacySpan


class FallacyDetector:
    """
    Fallacy detector that calls a Groq LLM under the hood.

    The Groq model is prompted to return a strict JSON structure describing
    the detected fallacies plus global clarity, persuasion, and reliability scores.

    How to configure your API key (local development):

    1. Go to https://console.groq.com and create an API key.
    2. EITHER:
       - Set an environment variable named GROQ_API_KEY, **or**
       - (Local only) replace the string "YOUR_GROQ_API_KEY_HERE" below with your real key.

    IMPORTANT:
    - Do NOT commit your real API key to GitHub. Before pushing, always
      remove any hard-coded keys and rely on the environment variable.
    """

    # You can change this to any Groq-supported model ID.
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(self, model: Optional[str] = None, min_confidence: float = 0.4):
        self.model = model or self.DEFAULT_MODEL
        self.min_confidence = min_confidence

        # 1) Try to read from environment variable
        api_key = os.getenv("GROQ_API_KEY")

        # 2) Optional: local-only fallback (replace with your key on your own machine).
        if not api_key:
            api_key = "YOUR_GROQ_API_KEY_HERE"

        # 3) Final safety check: if still not set or still placeholder, raise error.
        if not api_key or api_key == "YOUR_GROQ_API_KEY_HERE":
            raise RuntimeError(
                "GROQ_API_KEY is not set.\n"
                "Set the GROQ_API_KEY environment variable OR edit "
                "fallacylens/detector.py and replace 'YOUR_GROQ_API_KEY_HERE' "
                "with your actual Groq API key for local use."
            )

        self.client = Groq(api_key=api_key)

    # --------------------------------------------------------------------- #
    # Core analysis
    # --------------------------------------------------------------------- #

    def _build_prompt(self, text: str) -> str:
        """
        Build an instruction prompt asking the model for JSON only.

        We ask for:
        - list of fallacies
        - clarity_score (0–100)
        - persuasion_score (0–100)
        - reliability_score (0–100)
        """
        schema_description = {
            "type": "object",
            "properties": {
                "fallacies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "start": {"type": "integer"},
                            "end": {"type": "integer"},
                            "confidence": {"type": "number"},
                            "severity": {"type": "integer"},
                            "explanation": {"type": "string"},
                            "suggestion": {"type": "string"},
                        },
                        "required": [
                            "type",
                            "start",
                            "end",
                            "confidence",
                            "severity",
                            "explanation",
                        ],
                    },
                },
                "clarity_score": {
                    "type": "number",
                    "description": "Overall clarity of the text, from 0 to 100.",
                },
                "persuasion_score": {
                    "type": "number",
                    "description": "Overall persuasive strength of the text, from 0 to 100.",
                },
                "reliability_score": {
                    "type": "number",
                    "description": "How fact-based / reliable the argument appears, from 0 to 100.",
                },
            },
            "required": [
                "fallacies",
                "clarity_score",
                "persuasion_score",
                "reliability_score",
            ],
        }

        return (
            "You are a logical fallacy and argument quality analysis engine.\n"
            "Given an input text, you MUST respond with valid JSON only, no prose.\n\n"
            "You must:\n"
            "1) Detect any logical fallacies (e.g., Ad Hominem, Bandwagon, Slippery Slope,\n"
            "   Strawman, Hasty Generalization, False Cause, Circular Reasoning, etc.).\n"
            "2) For each fallacy, return character indices (0-based, [start, end)) and\n"
            "   a severity between 1 (minor) and 5 (severe).\n"
            "3) Provide three global scores (0–100):\n"
            "   - clarity_score: how clear and easy to follow the text is.\n"
            "   - persuasion_score: how persuasive and convincing the text is.\n"
            "   - reliability_score: how factual, fair and well-grounded the argument is.\n\n"
            "Use the following JSON schema (do not include comments in your output):\n"
            f"{json.dumps(schema_description, indent=2)}\n\n"
            "Now analyze the following text and return ONLY a JSON object with this structure.\n"
            f"TEXT:\n{text}"
        )

    def _call_groq(self, prompt: str) -> dict:
        """
        Call Groq Chat Completions API and return parsed JSON.

        If the model responds with invalid JSON, we fall back to a safe
        empty result instead of crashing.
        """
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict JSON API. You only output valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=1024,
        )

        content = completion.choices[0].message.content.strip()

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = {
                "fallacies": [],
                "clarity_score": 50,
                "persuasion_score": 50,
                "reliability_score": 50,
            }

        if not isinstance(data, dict):
            data = {
                "fallacies": [],
                "clarity_score": 50,
                "persuasion_score": 50,
                "reliability_score": 50,
            }

        # Normalize missing keys
        if "fallacies" not in data or not isinstance(data["fallacies"], list):
            data["fallacies"] = []
        if "clarity_score" not in data:
            data["clarity_score"] = 50
        if "persuasion_score" not in data:
            data["persuasion_score"] = 50
        if "reliability_score" not in data:
            data["reliability_score"] = 50

        return data

    def _data_to_result(self, text: str, data: dict) -> AnalysisResult:
        """Convert JSON data from the model into an AnalysisResult instance."""
        fallacies: List[FallacySpan] = []

        for item in data.get("fallacies", []):
            try:
                f_type = str(item.get("type", "")).strip() or "Unknown"
                start = int(item.get("start", 0))
                end = int(item.get("end", len(text)))
                confidence = float(item.get("confidence", 0.0))
                severity = int(item.get("severity", 1))
                explanation = str(item.get("explanation", "")).strip()
                suggestion = item.get("suggestion")
            except (TypeError, ValueError):
                # Skip malformed entries.
                continue

            if confidence < self.min_confidence:
                continue

            # Clamp indices to valid range.
            start = max(0, min(start, len(text)))
            end = max(start, min(end, len(text)))
            span_text = text[start:end]

            fallacies.append(
                FallacySpan(
                    start=start,
                    end=end,
                    text=span_text,
                    fallacy_type=f_type,
                    confidence=confidence,
                    severity=max(1, min(severity, 5)),
                    explanation=explanation,
                    suggestion=str(suggestion).strip() if suggestion else None,
                )
            )

        result = AnalysisResult(original_text=text, fallacies=fallacies)
        # Extra attributes for UI and API
        result.clarity_score = float(data.get("clarity_score", 50.0))
        result.persuasion_score = float(data.get("persuasion_score", 50.0))
        result.reliability_score = float(data.get("reliability_score", 50.0))
        return result

    def analyze(self, text: str) -> AnalysisResult:
        """Analyze a single text using the default Groq model and return a structured result."""
        prompt = self._build_prompt(text)
        data = self._call_groq(prompt)
        return self._data_to_result(text, data)

    def analyze_batch(self, texts: List[str]) -> List[AnalysisResult]:
        """Convenience method for analyzing multiple texts sequentially."""
        return [self.analyze(t) for t in texts]

    def analyze_with_model_name(self, text: str, model_name: str) -> AnalysisResult:
        """
        Analyze using a specific Groq model name (for multi-model comparison).

        This temporarily switches `self.model`, calls analyze(), then restores it.
        """
        prev_model = self.model
        try:
            self.model = model_name
            return self.analyze(text)
        finally:
            self.model = prev_model

    # --------------------------------------------------------------------- #
    # Shared helpers for advanced features
    # --------------------------------------------------------------------- #

    @staticmethod
    def _summarize_fallacies(fallacies: List[FallacySpan]) -> str:
        """Return a plain-text summary list of detected fallacies."""
        if not fallacies:
            return (
                "No clear logical fallacies were detected; focus on general clarity, "
                "evidence, and fairness."
            )
        lines = []
        for f in fallacies:
            lines.append(
                f"- {f.fallacy_type} (severity {f.severity}/5, "
                f"confidence {f.confidence:.2f}): {f.explanation}"
            )
        return "\n".join(lines)

    # --------------------------------------------------------------------- #
    # Argument rewriting
    # --------------------------------------------------------------------- #

    def _build_rewrite_prompt(
        self,
        text: str,
        fallacies: Optional[List[FallacySpan]] = None,
    ) -> str:
        """
        Build a prompt asking the model to rewrite the argument to be clearer,
        more balanced, and with fewer logical fallacies.
        """
        fallacy_summary = self._summarize_fallacies(fallacies or [])

        return (
            "You are an expert writing coach and logician.\n\n"
            "Your task is to rewrite the following argument so that:\n"
            "- It keeps the same main point and intended conclusion.\n"
            "- It removes or softens logical fallacies and unfair attacks.\n"
            "- It becomes clearer, more balanced, and more persuasive in a healthy way.\n"
            "- It avoids ad hominem attacks and overgeneralizations.\n\n"
            "You will be given:\n"
            "1) The original argument text.\n"
            "2) A summary of detected logical fallacies and reasoning issues.\n\n"
            "IMPORTANT:\n"
            "- Do NOT explain your changes.\n"
            "- Do NOT output JSON or bullet points.\n"
            "- ONLY output the improved argument as continuous text.\n\n"
            f"DETECTED ISSUES:\n{fallacy_summary}\n\n"
            f"ORIGINAL ARGUMENT:\n{text}\n\n"
            "NOW OUTPUT ONLY THE IMPROVED ARGUMENT:"
        )

    def rewrite_argument(
        self,
        text: str,
        fallacies: Optional[List[FallacySpan]] = None,
    ) -> str:
        """
        Rewrite an argument to improve clarity and reduce logical fallacies.

        Returns a single string containing the improved argument.
        """
        prompt = self._build_rewrite_prompt(text, fallacies)

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful, neutral writing assistant. "
                        "You improve arguments without changing their core meaning."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=1024,
        )

        rewritten = completion.choices[0].message.content.strip()
        return rewritten

    # --------------------------------------------------------------------- #
    # Teacher feedback mode
    # --------------------------------------------------------------------- #

    def teacher_feedback(self, analysis: AnalysisResult) -> dict:
        """
        Generate teacher-style feedback (strengths, areas to improve, grade).

        Returns a dict with keys:
        - strengths: list[str]
        - improvements: list[str]
        - overall_comment: str
        - grade: str
        """
        text = analysis.original_text
        fallacy_summary = self._summarize_fallacies(analysis.fallacies)

        scores_summary = (
            f"- Clarity score: {getattr(analysis, 'clarity_score', 50.0):.1f}/100\n"
            f"- Persuasion score: {getattr(analysis, 'persuasion_score', 50.0):.1f}/100\n"
            f"- Reliability score: {getattr(analysis, 'reliability_score', 50.0):.1f}/100\n"
        )

        schema = {
            "type": "object",
            "properties": {
                "strengths": {"type": "array", "items": {"type": "string"}},
                "improvements": {"type": "array", "items": {"type": "string"}},
                "overall_comment": {"type": "string"},
                "grade": {"type": "string"},
            },
            "required": ["strengths", "improvements", "overall_comment", "grade"],
        }

        prompt = (
            "You are an English teacher and critical thinking instructor.\n\n"
            "You will receive a student's argumentative paragraph, along with an analysis "
            "of logical fallacies and overall scores.\n\n"
            "Your job is to give concise, constructive feedback as if you were grading "
            "an assignment.\n"
            "Use the following JSON schema (no comments, no extra keys):\n"
            f"{json.dumps(schema, indent=2)}\n\n"
            "TEXT:\n"
            f"{text}\n\n"
            "ANALYSIS SUMMARY:\n"
            f"{scores_summary}\n"
            "DETECTED ISSUES:\n"
            f"{fallacy_summary}\n\n"
            "Now respond ONLY with a JSON object that follows the schema above."
        )

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict JSON API. You only output valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=768,
        )

        content = completion.choices[0].message.content.strip()
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = {}

        strengths = data.get("strengths") or []
        improvements = data.get("improvements") or []
        overall_comment = data.get("overall_comment") or "No detailed feedback was generated."
        grade = data.get("grade") or "N/A"

        # Ensure types
        strengths = [str(s) for s in strengths]
        improvements = [str(s) for s in improvements]
        overall_comment = str(overall_comment)
        grade = str(grade)

        return {
            "strengths": strengths,
            "improvements": improvements,
            "overall_comment": overall_comment,
            "grade": grade,
        }

    # --------------------------------------------------------------------- #
    # Persuasion optimizer
    # --------------------------------------------------------------------- #

    def optimize_persuasion(self, analysis: AnalysisResult) -> dict:
        """
        Suggest improvements to make the argument more persuasive (but still honest).

        Returns a dict with keys:
        - improved_text: str
        - strategy_notes: list[str]
        """
        text = analysis.original_text
        fallacy_summary = self._summarize_fallacies(analysis.fallacies)

        scores_summary = (
            f"- Clarity: {getattr(analysis, 'clarity_score', 50.0):.1f}/100\n"
            f"- Persuasion: {getattr(analysis, 'persuasion_score', 50.0):.1f}/100\n"
            f"- Reliability: {getattr(analysis, 'reliability_score', 50.0):.1f}/100\n"
        )

        schema = {
            "type": "object",
            "properties": {
                "improved_text": {"type": "string"},
                "strategy_notes": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["improved_text", "strategy_notes"],
        }

        prompt = (
            "You are a rhetoric and communication coach.\n\n"
            "Given an argument and its analysis, your job is to:\n"
            "- Make it more persuasive for a neutral, reasonable reader.\n"
            "- Keep it honest, fact-respecting, and non-manipulative.\n"
            "- Avoid logical fallacies and emotional manipulation.\n\n"
            "You must return JSON ONLY, following this schema:\n"
            f"{json.dumps(schema, indent=2)}\n\n"
            "ORIGINAL TEXT:\n"
            f"{text}\n\n"
            "CURRENT SCORES:\n"
            f"{scores_summary}\n"
            "DETECTED ISSUES:\n"
            f"{fallacy_summary}\n\n"
            "Now respond ONLY with a JSON object that follows the schema above."
        )

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict JSON API. You only output valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=1024,
        )

        content = completion.choices[0].message.content.strip()
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = {}

        improved_text = data.get("improved_text") or text
        strategy_notes = data.get("strategy_notes") or []

        improved_text = str(improved_text)
        strategy_notes = [str(s) for s in strategy_notes]

        return {
            "improved_text": improved_text,
            "strategy_notes": strategy_notes,
        }

    # --------------------------------------------------------------------- #
    # Bias detector
    # --------------------------------------------------------------------- #

    def analyze_bias(self, text: str) -> dict:
        """
        Analyze potential bias in the given text.

        Returns a dict with keys:
        - fairness_score: float (0–100, higher = more fair and balanced)
        - bias_summary: str
        - spans: list[dict] with keys: start, end, label, explanation, excerpt
        """
        schema = {
            "type": "object",
            "properties": {
                "fairness_score": {"type": "number"},
                "bias_summary": {"type": "string"},
                "spans": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "integer"},
                            "end": {"type": "integer"},
                            "label": {"type": "string"},
                            "explanation": {"type": "string"},
                        },
                        "required": ["start", "end", "label", "explanation"],
                    },
                },
            },
            "required": ["fairness_score", "bias_summary", "spans"],
        }

        prompt = (
            "You are a careful content and bias reviewer.\n\n"
            "Your job is to:\n"
            "- Detect passages that may appear biased, unfair, or overly one-sided.\n"
            "- Focus on potential stereotyping, demeaning language, or lack of balance.\n"
            "- Avoid labeling the author themselves; only discuss the text.\n\n"
            "Rate the text with a fairness_score from 0 to 100:\n"
            "- 0 = extremely biased and unfair.\n"
            "- 100 = highly fair, balanced, and respectful.\n\n"
            "Return JSON ONLY, following this schema:\n"
            f"{json.dumps(schema, indent=2)}\n\n"
            "TEXT TO REVIEW:\n"
            f"{text}\n\n"
            "Now respond ONLY with a JSON object that follows the schema above."
        )

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict JSON API. You only output valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1024,
        )

        content = completion.choices[0].message.content.strip()
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = {}

        fairness_score = float(data.get("fairness_score") or 60.0)
        bias_summary = str(data.get("bias_summary") or "No detailed bias summary was generated.")
        spans_raw = data.get("spans") or []
        spans: List[dict] = []

        for item in spans_raw:
            try:
                start = int(item.get("start", 0))
                end = int(item.get("end", len(text)))
                label = str(item.get("label", "Possible bias")).strip()
                explanation = str(item.get("explanation", "")).strip()
            except (TypeError, ValueError):
                continue

            # Clamp indices
            start = max(0, min(start, len(text)))
            end = max(start, min(end, len(text)))

            spans.append(
                {
                    "start": start,
                    "end": end,
                    "label": label,
                    "explanation": explanation,
                    "excerpt": text[start:end],
                }
            )

        return {
            "fairness_score": fairness_score,
            "bias_summary": bias_summary,
            "spans": spans,
        }
