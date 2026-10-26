"""Canonical publisher identities for source-independence accounting."""

import re
from urllib.parse import urlparse


MULTI_LABEL_SUFFIXES = {
    "ac.in", "co.in", "com.au", "com.br", "com.cn", "com.sg", "co.nz",
    "co.uk", "gov.in", "net.au", "org.in", "org.uk",
}

PUBLISHER_ALIASES = {
    "the times of india": "times-group",
    "times of india": "times-group",
    "the economic times": "times-group",
    "economic times": "times-group",
}


def publisher_identity(source: dict) -> str:
    """Return a stable organization key, grouping domains owned by one publisher."""
    cluster = str(source.get("cluster_id") or "").strip().casefold()
    # detect_syndication assigns a title hash to every article, including
    # original reporting. Use a cluster as a publisher only when syndication
    # was actually detected (or an explicit wire cluster was supplied).
    if cluster and cluster != "standalone" and (
        source.get("is_syndicated") or source.get("is_echo_chamber") or cluster.startswith("wire:")
    ):
        return f"cluster:{cluster}"

    domain = str(source.get("domain") or "").strip().casefold().removeprefix("www.")
    if not domain:
        url = str(source.get("url") or source.get("link") or "")
        domain = (urlparse(url).hostname or "").casefold().removeprefix("www.")
    if domain.endswith(".indiatimes.com") or domain == "indiatimes.com":
        return "times-group"
    if domain:
        labels = domain.split(".")
        if len(labels) >= 3 and ".".join(labels[-2:]) in MULTI_LABEL_SUFFIXES:
            return ".".join(labels[-3:])
        return ".".join(labels[-2:]) if len(labels) >= 2 else domain

    publisher = re.sub(r"[^a-z0-9]+", " ", str(source.get("publisher") or "").casefold()).strip()
    return PUBLISHER_ALIASES.get(publisher, publisher or "unknown")
