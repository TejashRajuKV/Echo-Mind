from evidence_engine import detect_evidence_stance, gather_evidence_pipeline
from api_decision_engine import build_api_decision, officeholder_search_query


def test_explicit_fact_check_rating_takes_precedence():
    assert detect_evidence_stance('claim', 'Article title', 'Article body', 'False') == 'refutes'
    assert detect_evidence_stance('claim', 'Article title', 'Article body', 'True') == 'supports'


def test_unrelated_news_copy_is_not_automatically_stance_evidence():
    assert detect_evidence_stance('claim about a policy', 'Latest policy update', 'Officials met on Tuesday') == 'neutral'


def test_retrieval_deduplicates_duplicate_urls_and_syndication(monkeypatch):
    # The routing engine skips connectors that have no configured key. These
    # test values only enable the mocked providers; no external request is made.
    monkeypatch.setenv('FREE_NEWS_API_KEY', 'test-news-key')
    first = {'url': 'https://publisher-a.example/story', 'title': 'A matching shared headline', 'publisher': 'Publisher A', 'domain': 'publisher-a.example', 'authority_score': 90, 'stance': 'supports', 'cluster_id': 'same-story'}
    duplicate_url = dict(first)
    lower_authority_mirror = {'url': 'https://publisher-b.example/story', 'title': 'A matching shared headline', 'publisher': 'Publisher B', 'domain': 'publisher-b.example', 'authority_score': 70, 'stance': 'supports', 'cluster_id': 'same-story'}
    monkeypatch.setattr('evidence_engine.query_local_factcheck_db', lambda *args, **kwargs: [first, duplicate_url])
    monkeypatch.setattr('evidence_engine.query_realtime_updater_context', lambda *args, **kwargs: [])
    monkeypatch.setattr('evidence_engine.query_live_news_sources', lambda *args, **kwargs: [lower_authority_mirror])
    result = gather_evidence_pipeline('example claim')
    assert result['total_sources_found'] == 3
    assert result['unique_sources_retained'] == 1
    assert result['sources'][0]['publisher'] == 'Publisher A'
    assert result['sources'][0]['echo_count'] == 1
    assert result['sources'][0]['is_echo_chamber'] is True


def test_officeholder_claim_routes_to_focused_live_news_search():
    decision = build_api_decision('present cm of karnataka is pm modi')
    assert decision['topic'] == 'politics'
    assert decision['time_sensitive'] is True
    assert officeholder_search_query('present cm of karnataka is pm modi') == 'karnataka current chief minister'
    assert decision['live_news_query'] == 'karnataka current chief minister'
    implicit_current = build_api_decision('CM of Karnataka is X')
    assert implicit_current['time_sensitive'] is True


def test_officeholder_search_discards_unrelated_live_articles(monkeypatch):
    monkeypatch.setenv('FREE_NEWS_API_KEY', 'test-news-key')
    monkeypatch.setattr('evidence_engine.query_local_factcheck_db', lambda *args, **kwargs: [])
    monkeypatch.setattr('evidence_engine.query_realtime_updater_context', lambda *args, **kwargs: [])
    monkeypatch.setattr('evidence_engine.query_live_news_sources', lambda *args, **kwargs: [
        {'url': 'https://example.com/cec', 'title': 'CEC row complicates Centre plan',
         'excerpt': 'Election officials discuss delimitation', 'publisher': 'Example',
         'domain': 'example.com', 'stance': 'neutral', 'authority_score': 80,
         'cluster_id': 'cec-story'},
        {'url': 'https://example.org/assam', 'title': 'Assam CM challenges opposition',
         'excerpt': 'Assam chief minister speaks about electoral rolls', 'publisher': 'Example Org',
         'domain': 'example.org', 'stance': 'neutral', 'authority_score': 70,
         'cluster_id': 'assam-story'},
    ])
    result = gather_evidence_pipeline('present cm of karnataka is pm modi')
    assert result['sources'] == []
    assert result['api_decision']['routes']['live_news']['results_found'] == 0


def test_publisher_aliases_and_article_title_hashes_do_not_fake_independence():
    from publisher_identity import publisher_identity
    sources = [
        {'domain': 'economictimes.indiatimes.com', 'publisher': 'The Times of India', 'cluster_id': 'titlehash1'},
        {'domain': 'timesofindia.indiatimes.com', 'publisher': 'The Times of India', 'cluster_id': 'titlehash2'},
    ]
    assert len({publisher_identity(source) for source in sources}) == 1


def test_fact_check_tools_are_not_routed():
    decision = build_api_decision('A claim')
    assert 'google_fact_check' not in decision['routes']
    assert 'live_news' in decision['routes']
