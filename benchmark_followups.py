"""Opt-in follow-up performance and quality evaluation.

Input JSONL records require claim and expected_verdict labels supplied by a human.
Run without --live to measure local context lookup only; --live invokes real analysis providers.
"""
import argparse
import json
import statistics
import time
from pathlib import Path
import context_memory
from incremental_verification import revalidation_history

def percentile(values, p):
    if not values:
        return None
    ordered=sorted(values)
    return round(ordered[min(len(ordered)-1, max(0, int((len(ordered)-1)*p)))], 2)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("dataset", help="Human-labelled JSONL file with claim and expected_verdict fields")
    parser.add_argument("--session", default="benchmark-session")
    parser.add_argument("--live", action="store_true", help="Run live provider analysis; may incur latency/cost")
    args=parser.parse_args()
    rows=[json.loads(line) for line in Path(args.dataset).read_text(encoding="utf-8").splitlines() if line.strip()]
    lookup_ms=[]; live_ms=[]; agreements=[]; source_counts=[]
    analyzer=None
    if args.live:
        from analysis_engine import analyze_claim
        analyzer=analyze_claim
    for row in rows:
        claim=row.get("claim")
        expected=row.get("expected_verdict")
        if not isinstance(claim,str) or not claim.strip() or not isinstance(expected,str):
            raise ValueError("Every record must include non-empty claim and expected_verdict strings")
        start=time.perf_counter()
        context_memory.prepare_context(args.session,claim)
        lookup_ms.append((time.perf_counter()-start)*1000)
        if analyzer:
            start=time.perf_counter()
            result=analyzer(claim,save_to_database=False)
            live_ms.append((time.perf_counter()-start)*1000)
            agreements.append(str(result.get("classification","Unknown")).casefold()==expected.casefold())
            sources=result.get("evidence_sources",result.get("sources",[]))
            source_counts.append(len(sources) if isinstance(sources,list) else 0)
    output={"records":len(rows),"context_lookup_ms":{"median":round(statistics.median(lookup_ms),2) if lookup_ms else None,
        "p95":percentile(lookup_ms,.95)},"live_analysis_run":bool(analyzer),
        "warning":"Context lookup is not a substitute for fresh verification. Quality agreement is meaningful only when labels are independent and the dataset is representative."}
    if analyzer:
        output["fresh_analysis_ms"]={"median":round(statistics.median(live_ms),2) if live_ms else None,"p95":percentile(live_ms,.95)}
        output["label_agreement_pct"]=round(sum(agreements)/len(agreements)*100,2) if agreements else None
        output["mean_source_count"]=round(statistics.mean(source_counts),2) if source_counts else 0
    print(json.dumps(output,indent=2))

if __name__=="__main__":
    main()
