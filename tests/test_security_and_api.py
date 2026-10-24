import html
import pytest
import app as app_module
from shareable_report import generate_shareable_report_html
from verdict_policy import reconcile_verdict

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, 'SESSION_DB_PATH', tmp_path / 'sessions.db')
    monkeypatch.setattr(app_module, '_rate_counts', {})
    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as test_client:
        yield test_client

def test_verdict_policy_abstains_without_two_publishers():
    verdict, reason = reconcile_verdict('Trustworthy', {'consensus_direction': 'supported'}, [{'publisher': 'One Publisher'}])
    assert verdict == 'Suspicious'
    assert 'Insufficient independent evidence' in reason

def test_verdict_policy_abstains_on_conflict():
    verdict, _ = reconcile_verdict('Trustworthy', {'consensus_direction': 'disputed', 'conflict_detected': True}, [{'publisher': 'A'}, {'publisher': 'B'}])
    assert verdict == 'Suspicious'

def test_verdict_policy_accepts_multi_publisher_direction():
    verdict, _ = reconcile_verdict('False', {'consensus_direction': 'supported'}, [{'publisher': 'A'}, {'publisher': 'B'}])
    assert verdict == 'Trustworthy'

def test_report_escapes_untrusted_claim_and_explanation():
    payload = '<' + 'img src=x onerror=alert(1)' + '>'
    report = generate_shareable_report_html({'classification': 'Suspicious', 'explanation': payload, 'evidence_sources': []}, payload)
    assert payload not in report
    assert html.escape(payload) in report

def test_analyze_rejects_bad_json_shape(client):
    response = client.post('/analyze', data='[]', content_type='application/json')
    assert response.status_code == 400

def test_analyze_rejects_blank_or_oversized_claim(client, monkeypatch):
    monkeypatch.setattr(app_module, 'MAX_CLAIM_LENGTH', 8)
    assert client.post('/analyze', json={'claim': '   '}).status_code == 400
    assert client.post('/analyze', json={'claim': '123456789'}).status_code == 400

def test_monitor_subscribe_validates_types_without_500(client):
    response = client.post('/monitor/subscribe', json={'claim': [], 'score': 'not-a-number'})
    assert response.status_code == 400

def test_report_endpoint_escapes_query_claim(client, monkeypatch):
    monkeypatch.setattr(app_module, 'analyze_claim', lambda *args, **kwargs: {'classification': 'Suspicious', 'score': 50, 'explanation': 'Not enough evidence', 'evidence_sources': []})
    payload = '<' + 'script>alert(1)' + '</' + 'script>'
    response = client.get('/report', query_string={'claim': payload})
    assert response.status_code == 200
    assert payload not in response.get_data(as_text=True)

def test_session_history_isolated_by_session_header(client, monkeypatch):
    monkeypatch.setattr(app_module, 'analyze_claim', lambda claim, *args, **kwargs: {'classification': 'Suspicious', 'score': 50, 'personalization': {'category': 'general'}, 'gamification': {'points': 10, 'badges': []}})
    client.post('/analyze', json={'claim': 'claim one'}, headers={'X-Session-ID': 'session-user-aaaa1111'})
    client.post('/analyze', json={'claim': 'claim two'}, headers={'X-Session-ID': 'session-user-bbbb2222'})
    first = client.get('/history', headers={'X-Session-ID': 'session-user-aaaa1111'}).get_json()['history']
    second = client.get('/history', headers={'X-Session-ID': 'session-user-bbbb2222'}).get_json()['history']
    assert [item['claim'] for item in first] == ['claim one']
    assert [item['claim'] for item in second] == ['claim two']

def test_consensus_does_not_overstate_one_publisher():
    from verification_engine import evaluate_conflict_and_consensus
    result = evaluate_conflict_and_consensus([{
        'publisher': 'Publisher A', 'domain': 'publisher-a.example',
        'stance': 'supports', 'authority_score': 100, 'cluster_id': 'a',
    }])
    assert result['consensus_direction'] == 'unknown'
    assert result['independent_publisher_count'] == 1
    assert 'Insufficient' in result['status']


def test_rate_limit_returns_429(client, monkeypatch):
    monkeypatch.setattr(app_module, 'MAX_REQUESTS_PER_HOUR', 1)
    assert client.get('/history').status_code == 200
    assert client.get('/history').status_code == 429


def test_document_endpoint_rejects_wrong_types(client):
    assert client.post('/document/analyze', json=[]).status_code == 400
    assert client.post('/document/analyze', json={'text': [], 'title': 'x'}).status_code == 400


def test_correction_endpoint_rejects_unsafe_url(client):
    response = client.post('/correction', json={
        'claim_text': 'Claim', 'evidence_url': 'javascript:alert(1)', 'rationale': 'Evidence'
    })
    assert response.status_code == 400


def test_health_route_lists_monitor_notification_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert '/monitor/notifications' in response.get_json()['endpoints']
