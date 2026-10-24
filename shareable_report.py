"""
shareable_report.py — Shareable Evidence Reports & Google ClaimReview Schema
===========================================================================
Generates linkable, publication-ready fact-check report cards with auditable
citations, methodology disclosures, correction mechanism, and official
Google ClaimReview (schema.org) structured JSON-LD data.
"""

import json
from datetime import datetime
from typing import Dict, Any, List


def generate_claim_review_jsonld(analysis_result: Dict[str, Any], canonical_url: str = "https://echomind.ai") -> Dict[str, Any]:
    """
    Generates standard Schema.org ClaimReview JSON-LD markup adhering to Google Fact Check guidelines.
    Ref: https://developers.google.com/search/docs/appearance/structured-data/fact-check
    """
    verdict = analysis_result.get("classification", "Unknown")
    score = analysis_result.get("score", 50)
    claim_text = analysis_result.get("claim", "") or (analysis_result.get("evidence_sources") or [{}])[0].get("title", "Claim Analyzed")

    # Map verdict to standard 1-5 numerical scale
    rating_value = 3
    if verdict == "Trustworthy":
        rating_value = 5
    elif verdict == "False":
        rating_value = 1
    elif verdict == "Suspicious":
        rating_value = 2

    now_iso = datetime.utcnow().strftime("%Y-%m-%d")

    return {
        "@context": "https://schema.org",
        "@type": "ClaimReview",
        "datePublished": now_iso,
        "url": canonical_url,
        "claimReviewed": claim_text,
        "itemReviewed": {
            "@type": "Claim",
            "name": claim_text,
            "appearance": [
                {
                    "@type": "CreativeWork",
                    "url": canonical_url
                }
            ]
        },
        "author": {
            "@type": "Organization",
            "name": "Echo Mind Fact Checker by Thunderwing Falcons",
            "url": "https://echomind.ai",
            "sameAs": "https://github.com/tejashrajukv/Echo-Mind"
        },
        "reviewRating": {
            "@type": "Rating",
            "ratingValue": rating_value,
            "bestRating": 5,
            "worstRating": 1,
            "alternateName": verdict,
            "ratingExplanation": analysis_result.get("explanation", "")
        }
    }


def generate_shareable_report_html(analysis_result: Dict[str, Any], claim_text: str, report_id: str = "rpt_001") -> str:
    """
    Generates a clean, standalone, printable and linkable HTML Evidence Report.
    Includes verification date, methodology notice, citations, limitations, and correction policy.
    """
    verdict = analysis_result.get("classification", "Suspicious")
    score = analysis_result.get("score", 50)
    sources = analysis_result.get("evidence_sources", [])
    consensus = analysis_result.get("consensus", {})
    subclaims = analysis_result.get("subclaims", [])
    date_str = datetime.utcnow().strftime("%B %d, %Y")
    jsonld = json.dumps(generate_claim_review_jsonld(analysis_result), indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Echo Mind Evidence Report: {claim_text[:50]}...</title>
    <!-- Google ClaimReview Structured Data -->
    <script type="application/ld+json">
{jsonld}
    </script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: #f8fafc;
            color: #1e293b;
            line-height: 1.6;
            margin: 0;
            padding: 2rem 1rem;
        }}
        .report-card {{
            max-width: 780px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.06);
            border: 1px solid #e2e8f0;
            padding: 2.5rem;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        .brand {{
            font-size: 1.4rem;
            font-weight: 800;
            color: #6366f1;
        }}
        .report-meta {{
            font-size: 0.82rem;
            color: #64748b;
            text-align: right;
        }}
        .claim-quote {{
            font-size: 1.25rem;
            font-weight: 700;
            color: #0f172a;
            background: #f8fafc;
            border-left: 4px solid #6366f1;
            padding: 1rem 1.25rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
        }}
        .verdict-box {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: {'#ecfdf5' if verdict=='Trustworthy' else ('#fef2f2' if verdict=='False' else '#fffbeb')};
            border: 1px solid {'#a7f3d0' if verdict=='Trustworthy' else ('#fecaca' if verdict=='False' else '#fde68a')};
            padding: 1rem 1.5rem;
            border-radius: 10px;
            margin-bottom: 1.5rem;
        }}
        .verdict-text {{
            font-size: 1.4rem;
            font-weight: 800;
            color: {'#065f46' if verdict=='Trustworthy' else ('#991b1b' if verdict=='False' else '#92400e')};
        }}
        .citations-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 0.9rem;
        }}
        .citations-table th, .citations-table td {{
            border: 1px solid #e2e8f0;
            padding: 0.75rem 1rem;
            text-align: left;
        }}
        .citations-table th {{
            background: #f8fafc;
            color: #475569;
        }}
        .footer-notice {{
            margin-top: 2rem;
            padding-top: 1.5rem;
            border-top: 1px solid #e2e8f0;
            font-size: 0.8rem;
            color: #64748b;
            line-height: 1.5;
        }}
        @media print {{
            body {{ background: #fff; padding: 0; }}
            .report-card {{ box-shadow: none; border: none; padding: 0; }}
        }}
    </style>
</head>
<body>
    <div class="report-card">
        <div class="header">
            <div>
                <div class="brand">Echo Mind Evidence Report</div>
                <div style="font-size: 0.85rem; color: #64748b;">AI Fact-Checking & Evidence Intelligence</div>
            </div>
            <div class="report-meta">
                <div>Report ID: <strong>{report_id}</strong></div>
                <div>Date: <strong>{date_str}</strong></div>
            </div>
        </div>

        <div style="font-size: 0.85rem; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 0.35rem;">Analyzed Claim:</div>
        <div class="claim-quote">"{claim_text}"</div>

        <div class="verdict-box">
            <div>
                <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: #64748b;">Official Assessment</div>
                <div class="verdict-text">{verdict}</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: #64748b;">Credibility Score</div>
                <div style="font-size: 1.5rem; font-weight: 900; color: #1e293b;">{score}/100</div>
            </div>
        </div>

        <h3>Reasoning & Context</h3>
        <p>{analysis_result.get('explanation', '')}</p>

        <h3>Auditable Evidence Trail</h3>
        <table class="citations-table">
            <thead>
                <tr>
                    <th>Publisher</th>
                    <th>Stance</th>
                    <th>Domain Authority</th>
                    <th>Date</th>
                    <th>Reference</th>
                </tr>
            </thead>
            <tbody>
                {''.join([f'''
                <tr>
                    <td><strong>{s.get('publisher','Source')}</strong></td>
                    <td><span style="font-weight:700; color: {'#15803d' if s.get('stance')=='supports' else ('#b91c1c' if s.get('stance')=='refutes' else '#64748b')}">{s.get('stance','neutral').upper()}</span></td>
                    <td>{s.get('authority_score', 50)}/100</td>
                    <td>{s.get('date', 'N/A')}</td>
                    <td><a href="{s.get('url', '#')}" target="_blank" rel="noopener">Link</a></td>
                </tr>
                ''' for s in sources]) if sources else '<tr><td colspan="5">No external direct links matched.</td></tr>'}
            </tbody>
        </table>

        <div class="footer-notice">
            <strong>Methodology & Quality Disclosures:</strong>
            Echo Mind employs multi-tier evidence retrieval (Google Fact Check Tools API, primary institutions, and live reporting), domain authority scoring, and atomic claim decomposition. Consensus calculations weigh independent reporting while penalizing syndicated echo chambers.
            <br><br>
            <strong>Correction Policy & Feedback:</strong>
            If you identify a factual error, new evidence, or an updated official clarification, submit a formal correction request directly to our public audit log at <a href="mailto:tejaskvraju@gmail.com">tejaskvraju@gmail.com</a>.
        </div>
    </div>
</body>
</html>
"""


if __name__ == "__main__":
    sample_analysis = {
        "classification": "False",
        "score": 25,
        "explanation": "Extensive scientific consensus from WHO confirms that 5G radio waves cannot transmit biological viruses.",
        "evidence_sources": [
            {"publisher": "WHO", "stance": "refutes", "authority_score": 98, "date": "2024-01-10", "url": "https://who.int"}
        ]
    }
    html = generate_shareable_report_html(sample_analysis, "5G spreads coronavirus")
    print("Generated report HTML, length:", len(html))
