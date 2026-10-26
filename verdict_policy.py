from typing import Any, Dict, Tuple
from publisher_identity import publisher_identity


def reconcile_verdict(model_verdict: str, consensus: Dict[str, Any], evidence_sources: list) -> Tuple[str, str]:
    """Conservative evidence-first verdict policy; return (classification, reason)."""
    sources = evidence_sources if isinstance(evidence_sources, list) else []
    publishers = {publisher_identity(s) for s in sources if isinstance(s, dict)}
    direction = str(consensus.get('consensus_direction', 'unknown')).casefold()
    if not sources or len(publishers) < 2:
        return 'Suspicious', 'Insufficient independent evidence: at least two distinct publishers are required for a decisive verdict.'
    if consensus.get('conflict_detected') or direction == 'disputed':
        return 'Suspicious', 'Conflicting evidence was detected; the result is contested and should not be presented as settled.'
    if direction == 'supported':
        return 'Trustworthy', 'The evidence consensus supports the claim across multiple distinct publishers.'
    if direction == 'refuted':
        return 'False', 'The evidence consensus refutes the claim across multiple distinct publishers.'
    return 'Suspicious', 'The retrieved evidence does not establish a sufficiently clear direction for a decisive verdict.'
