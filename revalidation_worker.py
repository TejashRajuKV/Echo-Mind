"""Scheduled incremental cache revalidation worker.

Run as a separate process alongside Flask:
    python revalidation_worker.py
Use --once for a single bounded pass. Requires the same provider credentials as analysis_engine.
"""
import argparse
import json
import logging
import os
import time
from incremental_verification import revalidate_expired

logging.basicConfig(level=os.environ.get("LOG_LEVEL","INFO"),format="%(asctime)s %(levelname)s %(message)s")
log=logging.getLogger("echo_mind.revalidation")

def run_once(limit):
    result=revalidate_expired(limit=limit)
    log.info("cache revalidation result=%s",json.dumps(result,ensure_ascii=False))
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--once",action="store_true",help="Run one bounded batch and exit")
    parser.add_argument("--interval-seconds",type=int,default=int(os.environ.get("REVALIDATION_INTERVAL_SECONDS","900")))
    parser.add_argument("--batch-size",type=int,default=int(os.environ.get("REVALIDATION_BATCH_SIZE","10")))
    args=parser.parse_args()
    if args.interval_seconds < 60 or not 1 <= args.batch_size <= 100:
        parser.error("interval-seconds must be >= 60 and batch-size must be between 1 and 100")
    if args.once:
        run_once(args.batch_size)
        return
    log.info("worker started interval_seconds=%s batch_size=%s",args.interval_seconds,args.batch_size)
    while True:
        try:
            run_once(args.batch_size)
        except Exception:
            log.exception("worker iteration failed; next scheduled pass will retry")
        time.sleep(args.interval_seconds)

if __name__=="__main__":
    main()
