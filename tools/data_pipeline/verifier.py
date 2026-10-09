"""LLM-as-a-Judge Fact Checker to drop hallucinations."""

import re
from typing import Any, Dict, List, Optional, Tuple


class FactChecker:
    """Validates QA pairs using an LLM-as-a-judge consensus check."""

    def __init__(self, llm: Optional[Any] = None, model_path: Optional[str] = None):
        """Initialize the fact checker with an existing LLM instance or model path."""
        self.llm = llm
        self._verdict_cache: Dict[str, bool] = {}
        if self.llm is None and model_path:
            from llama_cpp import Llama
            self.llm = Llama(
                model_path=model_path,
                n_threads=12,
                n_ctx=512,
                verbose=False
            )

    def check_fact(self, question: str, answer: str) -> bool:
        """Evaluate if an answer contains factual inaccuracies. Returns True for PASS, False for FAIL."""
        if not answer or not answer.strip():
            return False

        cache_key = answer.strip()
        if cache_key in self._verdict_cache:
            return self._verdict_cache[cache_key]

        if self.llm is None:
            # Deterministic heuristic verification when no LLM is loaded
            return self._heuristic_check(question, answer)

        prompt = (
            "System: Are there any factual inaccuracies in this answer based on current astronomical consensus? "
            "Reply strictly with PASS or FAIL.\n"
            f"Question: {question.strip()}\n"
            f"Answer: {answer.strip()}\n"
            "Verdict:"
        )

        try:
            output = self.llm(
                prompt,
                max_tokens=4,
                temperature=0.1,
                stop=["\n", ".", " "]
            )
            raw_verdict = output["choices"][0]["text"].strip().upper()
            verdict = self._parse_verdict(raw_verdict)
            self._verdict_cache[cache_key] = verdict
            return verdict
        except Exception as e:
            print(f"[FactChecker] Warning: LLM judge error: {e}. Falling back to heuristic.", flush=True)
            verdict = self._heuristic_check(question, answer)
            self._verdict_cache[cache_key] = verdict
            return verdict

    def _parse_verdict(self, verdict_text: str) -> bool:
        """Parse LLM response into boolean PASS (True) or FAIL (False)."""
        upper = verdict_text.upper()
        if "FAIL" in upper:
            return False
        if "PASS" in upper:
            return True

        # Catch other rejection keywords
        fail_keywords = ["INACCURATE", "FALSE", "INCORRECT", "WRONG", "NO"]
        for kw in fail_keywords:
            if kw in upper:
                return False

        # Default to True if no failure signals detected
        return True

    def _heuristic_check(self, question: str, answer: str) -> bool:
        """Heuristic validation for obvious contradictions or empty statements."""
        lower = answer.lower()
        if "flat earth" in lower or "sun revolves around earth" in lower or "aliens built" in lower:
            return False
        return len(answer.strip()) > 10

    def filter_qa_pairs(self, qa_pairs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Filter a batch of QA pairs, discarding those marked FAIL."""
        passed = []
        stats = {"total": len(qa_pairs), "passed": 0, "failed": 0}

        for item in qa_pairs:
            q = item.get("question_text", "")
            a = item.get("answer_text", "")
            verdict = self.check_fact(q, a)
            if verdict:
                passed.append(item)
                stats["passed"] += 1
            else:
                stats["failed"] += 1

        return passed, stats
