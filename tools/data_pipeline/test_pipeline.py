"""Comprehensive test suite for the knowledge data pipeline."""

import os
import shutil
import tempfile
import pytest

from expander import SyntheticExpander
from verifier import FactChecker
from storage import KnowledgeStorage
from build_db import read_seed_csv, run_pipeline


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_csv(temp_dir):
    csv_file = os.path.join(temp_dir, "test_seed.csv")
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write("intent_category,seed_fact,citation_source\n")
        f.write("Solar System,Jupiter has 95 known moons.,NASA JPL\n")
        f.write("Cosmology,The universe is 13.8 billion years old.,ESA Planck\n")
        f.write("Black Holes,The event horizon prevents light escape.,EHT\n")
    return csv_file


def test_seed_csv_reading(sample_csv):
    """Test reading and parsing of the seed CSV."""
    records = read_seed_csv(sample_csv)
    assert len(records) == 3
    assert records[0]["intent_category"] == "Solar System"
    assert "95 known moons" in records[0]["seed_fact"]
    assert records[0]["citation_source"] == "NASA JPL"


def test_seed_csv_50_facts():
    """Verify that the production seed_facts.csv contains exactly 50 seed facts."""
    csv_path = os.path.join(os.path.dirname(__file__), "seed_facts.csv")
    assert os.path.exists(csv_path)
    records = read_seed_csv(csv_path)
    assert len(records) == 50
    for r in records:
        assert r["intent_category"]
        assert len(r["seed_fact"]) > 10
        assert r["citation_source"]


def test_synthetic_expander_heuristic():
    """Test SyntheticExpander rule-based generation when no LLM is loaded."""
    expander = SyntheticExpander()
    variations = expander.generate_variations("Jupiter is a gas giant.", num_variations=3)
    assert len(variations) == 3
    for v in variations:
        assert isinstance(v, str)
        assert len(v) > 5
        assert v.endswith("?") or v.endswith(".")


def test_synthetic_expander_with_mock_llm():
    """Test SyntheticExpander with mock callable output."""
    def mock_llm(prompt, **kwargs):
        return {
            "choices": [{
                "text": "How big is Jupiter? 2. Is Jupiter a planet? 3. What is Jupiter made of?"
            }]
        }

    expander = SyntheticExpander(llm=mock_llm)
    variations = expander.generate_variations("Jupiter is large.", num_variations=2)
    assert len(variations) == 2
    assert "How big is Jupiter?" in variations[0]


def test_fact_checker_verdicts():
    """Test FactChecker verdict parsing for PASS and FAIL."""
    def pass_llm(prompt, **kwargs):
        return {"choices": [{"text": " PASS"}]}

    def fail_llm(prompt, **kwargs):
        return {"choices": [{"text": " FAIL: Inaccurate"}]}

    pass_checker = FactChecker(llm=pass_llm)
    assert pass_checker.check_fact("How big is Earth?", "Earth has a diameter of 12742 km.") is True

    fail_checker = FactChecker(llm=fail_llm)
    assert fail_checker.check_fact("Is Earth flat?", "Earth is flat.") is False


def test_fact_checker_filtering():
    """Test batch filtering of QA pairs."""
    checker = FactChecker()
    qa_list = [
        {"question_text": "Q1", "answer_text": "The Sun is a yellow dwarf star at the center of our solar system."},
        {"question_text": "Q2", "answer_text": "The flat earth is supported by giant turtles."},
        {"question_text": "Q3", "answer_text": "Short"}
    ]
    passed, stats = checker.filter_qa_pairs(qa_list)
    assert stats["total"] == 3
    assert stats["passed"] == 1
    assert stats["failed"] == 2
    assert len(passed) == 1
    assert "Sun is a yellow dwarf" in passed[0]["answer_text"]


def test_knowledge_storage_ingestion_and_search(temp_dir):
    """Test vector storage, schema creation, ingestion, and search."""
    db_path = os.path.join(temp_dir, "lancedb")
    storage = KnowledgeStorage(db_path=db_path, table_name="test_astronomy")

    records = [
        {
            "id": "1",
            "intent_category": "Solar System",
            "question_text": "How many moons does Jupiter have?",
            "answer_text": "Jupiter has 95 known moons.",
            "citation_source": "NASA JPL"
        },
        {
            "id": "2",
            "intent_category": "Cosmology",
            "question_text": "What is the age of the universe?",
            "answer_text": "The universe is roughly 13.8 billion years old.",
            "citation_source": "ESA Planck"
        }
    ]

    count = storage.ingest(records)
    assert count == 2

    # Query Jupiter
    res = storage.search("Jupiter moons count", top_k=1)
    assert len(res) == 1
    assert res[0]["intent_category"] == "Solar System"
    assert "95 known moons" in res[0]["answer_text"]
    assert res[0]["citation_source"] == "NASA JPL"


def test_pipeline_end_to_end_mock(sample_csv, temp_dir):
    """Test full pipeline execution end-to-end."""
    db_path = os.path.join(temp_dir, "pipeline_lancedb")
    result = run_pipeline(
        csv_path=sample_csv,
        output_db=db_path,
        table_name="astronomy_knowledge",
        variations_per_fact=2,
        use_mock_llm=True,
        verify_query="Tell me about Jupiter"
    )

    assert result["seed_count"] == 3
    assert result["generated_count"] == 6
    assert result["approved_count"] == 6
    assert result["ingested_count"] == 6
    assert len(result["search_results"]) > 0
    assert "Jupiter" in result["search_results"][0]["answer_text"] or "universe" in result["search_results"][0]["answer_text"]
