"""Synthetic question variation expander using local LLM."""

import re
from typing import Any, List, Optional


class SyntheticExpander:
    """Expands seed facts into multiple conversational question variations."""

    def __init__(self, llm: Optional[Any] = None, model_path: Optional[str] = None):
        """Initialize the expander with an optional existing LLM instance or model path."""
        self.llm = llm
        if self.llm is None and model_path:
            from llama_cpp import Llama
            self.llm = Llama(
                model_path=model_path,
                n_threads=12,
                n_ctx=512,
                verbose=False
            )

    def generate_variations(self, fact: str, num_variations: int = 3) -> List[str]:
        """Generate question variations mapped to the intent of the seed fact."""
        if not fact or not fact.strip():
            return []

        if self.llm is None:
            # Fallback heuristic generator when running without LLM weights
            return self._heuristic_variations(fact, num_variations)

        stop_token = f"{num_variations + 1}."
        prompt = (
            f"Fact: {fact.strip()}\n"
            f"Generate {num_variations} short questions answered by this fact:\n"
            "1."
        )

        try:
            output = self.llm(
                prompt,
                max_tokens=18 * num_variations,
                temperature=0.6,
                stop=["\n\n", stop_token, "Fact:"]
            )
            raw_text = "1. " + output["choices"][0]["text"].strip()
            questions = self._parse_questions(raw_text)
            if not questions:
                return self._heuristic_variations(fact, num_variations)
            return questions[:num_variations]
        except Exception as e:
            print(f"[SyntheticExpander] Warning: LLM generation error: {e}. Using heuristic fallback.", flush=True)
            return self._heuristic_variations(fact, num_variations)

    def _parse_questions(self, text: str) -> List[str]:
        """Parse numbered or line-separated questions from LLM text."""
        lines = re.split(r"(?:\r?\n|\b\d+[\.\)])", text)
        results = []
        for line in lines:
            cleaned = line.strip(" -*\t\r\n")
            if cleaned and len(cleaned) > 5:
                if not cleaned.endswith("?"):
                    cleaned += "?"
                if cleaned not in results:
                    results.append(cleaned)
        return results

    def _heuristic_variations(self, fact: str, num_variations: int = 3) -> List[str]:
        """Rule-based question variations for deterministic fallback and testing."""
        fact_clean = fact.strip().rstrip(".")
        candidates = [
            f"What should I know about {fact_clean}?",
            f"Can you explain why {fact_clean}?",
            f"Is it true that {fact_clean}?",
            f"Tell me more about {fact_clean}."
        ]
        return candidates[:num_variations]
