import context_memory as memory
import incremental_verification as iv

def test_claim_family_numeric_change_requires_reverification():
    result = iv.claim_family_similarity(
        "Government announces 15000 rupees for students",
        "Government announces 20000 rupees for students"
    )
    assert result["candidate_family"]
    assert result["material_change"]
    assert result["must_reverify"]

def test_labelled_claim_family_fixture_has_examples():
    result = iv.evaluate_claim_families()
    assert result["n"] >= 20
    assert 0 <= result["precision"] <= 1
    assert 0 <= result["recall"] <= 1

def test_language_detection_has_fallback():
    assert iv.detect_language("ವಿದ್ಯಾರ್ಥಿಗಳಿಗೆ ಸರ್ಕಾರದ ವಿದ್ಯಾರ್ಥಿವೇತನ") == "kn"


def use_temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(memory, "DB_PATH", tmp_path / "context_memory.db")
    monkeypatch.setattr(iv, "DB_PATH", tmp_path / "context_memory.db")

def test_provenance_graph_links_only_http_sources(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    graph = iv.build_provenance_graph("inv-test", "A claim", [
        {"title": "Official", "url": "https://example.gov.in/notice", "stance": "supports"},
        {"title": "Bad URL", "url": "javascript:alert(1)"}
    ])
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1
    source = next(node for node in graph["nodes"] if node["node_type"] == "source")
    assert source["url"] == "https://example.gov.in/notice"

def test_revalidation_failure_keeps_expired_cache_stale(monkeypatch, tmp_path):
    from datetime import timedelta
    use_temp_db(monkeypatch, tmp_path)
    claim = "A grant announced today"
    memory.cache_analysis(claim, {"classification": "Suspicious", "score": 40,
        "sources": [{"title": "Old source", "url": "https://example.com/old"}]})
    conn = memory._conn()
    conn.execute("UPDATE evidence_cache SET expires_at=?", ((memory.utc_now()-timedelta(seconds=2)).isoformat(),))
    conn.commit()
    conn.close()
    result = iv.revalidate_expired(1, analyzer=lambda *args, **kwargs: {"classification": "Unknown", "sources": []})
    assert result["results"][0]["status"] == "failed"
    assert memory.get_cached_analysis(claim)["fresh"] is False
    assert iv.revalidation_history(claim)[0]["status"] == "failed"

def test_revalidation_records_verdict_drift(monkeypatch, tmp_path):
    from datetime import timedelta
    use_temp_db(monkeypatch, tmp_path)
    claim = "A grant announced today"
    memory.cache_analysis(claim, {"classification": "Suspicious", "score": 40,
        "sources": [{"title": "Old source", "url": "https://example.com/old"}]})
    conn = memory._conn()
    conn.execute("UPDATE evidence_cache SET expires_at=?", ((memory.utc_now()-timedelta(seconds=2)).isoformat(),))
    conn.commit()
    conn.close()
    fresh = {"classification": "False", "score": 12,
        "sources": [{"title": "Official source", "url": "https://example.gov.in/new"}]}
    result = iv.revalidate_expired(1, analyzer=lambda *args, **kwargs: fresh)
    assert result["results"][0]["status"] == "changed"
    assert iv.revalidation_history(claim)[0]["old_verdict"] == "Suspicious"
    assert iv.revalidation_history(claim)[0]["new_verdict"] == "False"
    assert memory.get_cached_analysis(claim)["fresh"] is True
