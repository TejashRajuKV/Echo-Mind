from evidence_engine import detect_evidence_stance, gather_evidence_pipeline


def test_explicit_fact_check_rating_takes_precedence():
    assert detect_evidence_stance('claim', 'Article title', 'Article body', 'False') == 'refutes'
    assert detect_evidence_stance('claim', 'Article title', 'Article body', 'True') == 'supports'


def test_unrelated_news_copy_is_not_automatically_stance_evidence():
    assert detect_evidence_stance('claim about a policy', 'Latest policy update', 'Officials met on Tuesday') == 'neutral'


def test_retrieval_deduplicates_duplicate_urls_and_syndication(monkeypatch):
    # The routing engine skips connectors that have no configured key. These
    # test values only enable the mocked providers; no external request is made.
    monkeypatch.setenv('GOOGLE_FACT_CHECK_API_KEY', 'test-google-key')
    monkeypatch.setenv('FREE_NEWS_API_KEY', 'test-news-key')
    first = {'url': 'https://publisher-a.example/story', 'title': 'A matching shared headline', 'publisher': 'Publisher A', 'domain': 'publisher-a.example', 'authority_score': 90, 'stance': 'supports', 'cluster_id': 'same-story'}
    duplicate_url = dict(first)
    lower_authority_mirror = {'url': 'https://publisher-b.example/story', 'title': 'A matching shared headline', 'publisher': 'Publisher B', 'domain': 'publisher-b.example', 'authority_score': 70, 'stance': 'supports', 'cluster_id': 'same-story'}
    monkeypatch.setattr('evidence_engine.query_google_fact_check', lambda *args, **kwargs: [first, duplicate_url])
    monkeypatch.setattr('evidence_engine.query_local_factcheck_db', lambda *args, **kwargs: [])
    monkeypatch.setattr('evidence_engine.query_realtime_updater_context', lambda *args, **kwargs: [])
    monkeypatch.setattr('evidence_engine.query_live_news_sources', lambda *args, **kwargs: [lower_authority_mirror])
    result = gather_evidence_pipeline('example claim')
    assert result['total_sources_found'] == 3
    assert result['unique_sources_retained'] == 1
    assert result['sources'][0]['publisher'] == 'Publisher A'
    assert result['sources'][0]['echo_count'] == 1
    assert result['sources'][0]['is_echo_chamber'] is True
