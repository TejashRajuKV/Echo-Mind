"""Safe HTML shareable evidence report generator."""
import html
import json
from datetime import datetime
from urllib.parse import urlparse
from typing import Dict, Any


def _text(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _safe_url(value: Any) -> str:
    raw = str(value or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return raw


def generate_claim_review_jsonld(analysis_result: Dict[str, Any], canonical_url: str = "https://github.com/TejashRajuKV/Echo-Mind") -> Dict[str, Any]:
    verdict = str(analysis_result.get("classification", "Unknown"))
    claim_text = str(analysis_result.get("claim", "") or "Claim analyzed")
    rating_value = {"Trustworthy": 5, "False": 1, "Suspicious": 2}.get(verdict, 3)
    canonical = _safe_url(canonical_url) or "https://github.com/TejashRajuKV/Echo-Mind"
    return {
        "@context": "https://schema.org",
        "@type": "ClaimReview",
        "datePublished": datetime.utcnow().strftime("%Y-%m-%d"),
        "url": canonical,
        "claimReviewed": claim_text,
        "itemReviewed": {"@type": "Claim", "name": claim_text, "appearance": [{"@type": "CreativeWork", "url": canonical}]},
        "author": {"@type": "Organization", "name": "Echo Mind Fact Checker by Thunderwing Falcons", "url": "https://github.com/TejashRajuKV/Echo-Mind"},
        "reviewRating": {
            "@type": "Rating", "ratingValue": rating_value, "bestRating": 5, "worstRating": 1,
            "alternateName": verdict, "ratingExplanation": str(analysis_result.get("explanation", "")),
        },
    }


def generate_shareable_report_html(analysis_result: Dict[str, Any], claim_text: str, report_id: str = "rpt_001") -> str:
    verdict = str(analysis_result.get("classification", "Suspicious"))
    score = analysis_result.get("score", 50)
    try:
        score = max(0, min(100, int(float(score))))
    except (TypeError, ValueError, OverflowError):
        score = 50
    sources = analysis_result.get("evidence_sources", [])
    if not isinstance(sources, list):
        sources = []
    consensus = analysis_result.get("consensus", {})
    if not isinstance(consensus, dict):
        consensus = {}
    safe_verdict = _text(verdict)
    color, bg = {
        "Trustworthy": ("#065f46", "#ecfdf5"),
        "False": ("#991b1b", "#fef2f2"),
        "Suspicious": ("#92400e", "#fffbeb"),
    }.get(verdict, ("#334155", "#f1f5f9"))
    schema = generate_claim_review_jsonld({
        "claim": claim_text, "classification": verdict, "score": score,
        "explanation": analysis_result.get("explanation", ""),
    })
    # Prevent a user-controlled string from terminating the JSON-LD script element.
    jsonld = json.dumps(schema, ensure_ascii=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    rows = []
    for source in sources[:50]:
        if not isinstance(source, dict):
            continue
        url = _safe_url(source.get("url"))
        link = f'<a href="{_text(url)}" target="_blank" rel="noopener noreferrer">Open source</a>' if url else "No safe external URL"
        stance = str(source.get("stance", "neutral")).upper()
        stance_color = "#15803d" if stance.lower() == "supports" else ("#b91c1c" if stance.lower() == "refutes" else "#64748b")
        rows.append("<tr>" +
            f"<td>{_text(source.get('publisher', 'Source'))}</td>" +
            f'<td style="color:{stance_color}">{_text(stance)}</td>' +
            f"<td>{_text(source.get('authority_score', 50))}/100</td>" +
            f"<td>{_text(source.get('date', 'N/A'))}</td>" +
            f"<td>{link}</td></tr>")
    if not rows:
        rows.append('<tr><td colspan="5">No external direct links matched.</td></tr>')
    explanation = _text(analysis_result.get("explanation", "No explanation was supplied."))
    direction = _text(consensus.get("status", "Insufficient evidence"))
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Echo Mind Evidence Report: """ + _text(claim_text[:80]) + """</title>
<script type="application/ld+json">""" + jsonld + """</script>
<style>
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:#f8fafc;color:#1e293b;line-height:1.6;margin:0;padding:2rem 1rem}
main{max-width:850px;margin:auto;background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:2rem;box-shadow:0 8px 25px #0f172a0d}
h1{font-size:1.5rem} .claim{white-space:pre-wrap;overflow-wrap:anywhere;background:#f8fafc;border-left:4px solid #6366f1;padding:1rem}
.verdict{background:""" + bg + """;color:""" + color + """;padding:1rem;border-radius:10px;font-weight:800}
table{border-collapse:collapse;width:100%;font-size:.9rem}td,th{border:1px solid #e2e8f0;padding:.65rem;text-align:left;overflow-wrap:anywhere}
footer{margin-top:2rem;border-top:1px solid #e2e8f0;padding-top:1rem;color:#64748b;font-size:.85rem}
</style></head><body><main>
<h1>Echo Mind Evidence Report</h1><p>Report ID: <strong>""" + _text(report_id) + """</strong> · Generated """ + _text(datetime.utcnow().strftime("%B %d, %Y")) + """</p>
<h2>Claim reviewed</h2><div class="claim">""" + _text(claim_text) + """</div>
<p class="verdict">Assessment: """ + safe_verdict + """ · Evidence score: """ + _text(score) + """/100</p>
<h2>Reasoning and context</h2><p>""" + explanation + """</p>
<p>Evidence status: """ + direction + """</p>
<h2>Evidence trail</h2><table><thead><tr><th>Publisher</th><th>Stance</th><th>Authority</th><th>Date</th><th>Reference</th></tr></thead><tbody>""" + "".join(rows) + """</tbody></table>
<footer><strong>Limitations:</strong> Automated assessments can be incomplete or wrong. Stance tags and authority scores are heuristic signals, not proof. Check the linked original sources and current official information before acting. ClaimReview structured data does not imply eligibility for search features or independent editorial review.</footer>
</main></body></html>"""


if __name__ == "__main__":
    demo = generate_shareable_report_html({"classification": "Suspicious", "score": 50, "evidence_sources": []}, "Example claim")
    print("Generated safe report HTML, length:", len(demo))
