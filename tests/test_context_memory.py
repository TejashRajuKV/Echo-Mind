import json
from datetime import timedelta

import context_memory as memory


def use_temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(memory, "DB_PATH", tmp_path / "context_memory.db")


def test_exact_claim_cache_hit_and_expiry(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    claim = "Government announces a new scholarship today"
    result = {"classification": "Needs more evidence", "score": 40,
              "sources": [{"title": "Official notice", "url": "https://example.gov.in/notice"}],
              "gamification": {"points": 10}, "session": {"claim_count": 1}}
    memory.cache_analysis(claim, result)
    cached = memory.get_cached_analysis(claim)
    assert cached["fresh"] is True
    assert cached["result"]["classification"] == "Needs more evidence"
    assert "session" not in cached["result"]
    assert "gamification" not in cached["result"]
    assert cached["sources"][0]["url"].startswith("https://")
    conn = memory._conn()
    conn.execute("UPDATE evidence_cache SET expires_at=?", ((memory.utc_now()-timedelta(seconds=1)).isoformat(),))
    conn.commit()
    conn.close()
    expired = memory.get_cached_analysis(claim)
    assert expired["fresh"] is False
    assert expired["result"] is None
    assert expired["requires_revalidation"] is True


def test_related_investigation_is_session_scoped(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    first = memory.record_investigation("session-a", "Government gives 15000 rupees to every student", {
        "classification": "Unverified", "score": 20, "sources": []
    })
    related = memory.related_investigations("session-a", "Government gives 15000 rupees to students")
    assert related
    assert related[0]["id"] == first["id"]
    assert memory.related_investigations("session-b", "Government gives 15000 rupees to students") == []


def test_memory_opt_out_is_persisted_and_clears_private_history(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    memory.record_investigation("s", "A specific claim about a new student grant", {"classification": "Unknown"})
    prefs = memory.set_preferences("s", False, 30)
    assert prefs["enabled"] is False
    assert memory.get_preferences("s")["enabled"] == 0
    assert memory.list_investigations("s") == []
    assert memory.prepare_context("s", "A specific claim about a new student grant")["matches"] == []


def test_private_investigation_events_and_deletion(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    inv = memory.record_investigation("owner", "A test claim with a private note", {"classification": "Unknown"})
    assert memory.record_event("owner", inv["id"], "note", {"text": "Check official gazette"})
    assert not memory.record_event("other", inv["id"], "note", {"text": "should not work"})
    detail = memory.get_investigation("owner", inv["id"])
    assert detail["events"][-1]["payload"]["text"] == "Check official gazette"
    assert memory.delete_investigation("owner", inv["id"])
    assert memory.get_investigation("owner", inv["id"]) is None


def test_cache_rejects_non_http_sources(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    memory.cache_analysis("A claim", {"classification": "Unknown", "sources": [
        {"title": "bad", "url": "javascript:alert(1)"},
        {"title": "good", "url": "https://example.com/article"}
    ]})
    cached = memory.get_cached_analysis("A claim")
    assert [item["title"] for item in cached["sources"]] == ["good"]


def test_similar_claims_do_not_automatically_become_evidence(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    memory.record_investigation("s", "Government announces 15000 rupees for college students", {
        "classification": "False", "score": 15, "sources": []
    })
    context = memory.prepare_context("s", "Government announces 20000 rupees for college students")
    assert context["mode"] == "incremental"
    assert context["matches"]
    assert "not evidence" in context["guidance"]


def test_explicit_cross_language_alias_matches_related_investigation(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    inv = memory.record_investigation("s", "Government scholarship for students", {
        "classification": "Needs more evidence", "sources": []
    })
    memory.add_claim_alias("s", inv["id"], "ವಿದ್ಯಾರ್ಥಿಗಳಿಗೆ ಸರ್ಕಾರದ ವಿದ್ಯಾರ್ಥಿವೇತನ", "Kannada")
    context = memory.prepare_context("s", "ವಿದ್ಯಾರ್ಥಿಗಳಿಗೆ ಸರ್ಕಾರದ ವಿದ್ಯಾರ್ಥಿವೇತನ")
    assert any(item["relation"] == "cross_language_alias" for item in context["matches"])
    assert "not evidence" in context["guidance"]


def test_alias_cannot_be_added_to_another_users_investigation(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    inv = memory.record_investigation("owner", "Private investigation claim", {"classification": "Unknown"})
    try:
        memory.add_claim_alias("attacker", inv["id"], "A different language alias")
    except LookupError:
        pass
    else:
        raise AssertionError("cross-session alias write should be rejected")


def test_workspace_placeholder_is_not_shared_as_a_verdict(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    memory.record_investigation("s", "A manually saved but unverified claim", {
        "classification": "Not yet verified", "score": None, "sources": []
    })
    assert memory.get_cached_analysis("A manually saved but unverified claim") is None
