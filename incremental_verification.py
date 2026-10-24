"""Incremental verification primitives: auditable cache revalidation and conservative claim families."""
from __future__ import annotations
import hashlib, json, re, sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse
import context_memory as memory

DB_PATH = memory.DB_PATH

def _now():
    return datetime.now(timezone.utc).isoformat()

def _conn():
    conn = memory._conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS cache_revalidation_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT, fingerprint TEXT NOT NULL,
      old_verdict TEXT, new_verdict TEXT, old_score REAL, new_score REAL,
      status TEXT NOT NULL, source_count INTEGER NOT NULL DEFAULT 0,
      summary TEXT NOT NULL DEFAULT '', started_at TEXT NOT NULL, finished_at TEXT,
      error_code TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_revalidation_fp ON cache_revalidation_runs(fingerprint, id DESC);
    CREATE TABLE IF NOT EXISTS revalidation_leases (
      fingerprint TEXT PRIMARY KEY, lease_until TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS provenance_nodes (
      id TEXT PRIMARY KEY, investigation_id TEXT, node_type TEXT NOT NULL,
      label TEXT NOT NULL, url TEXT, metadata_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS provenance_edges (
      source_id TEXT NOT NULL, target_id TEXT NOT NULL, relation TEXT NOT NULL,
      created_at TEXT NOT NULL, PRIMARY KEY(source_id,target_id,relation),
      FOREIGN KEY(source_id) REFERENCES provenance_nodes(id) ON DELETE CASCADE,
      FOREIGN KEY(target_id) REFERENCES provenance_nodes(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS correction_reviews (
      id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
      investigation_id TEXT, claim TEXT NOT NULL, evidence_url TEXT NOT NULL,
      rationale TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
      reviewer_note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS user_notifications (
      id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
      investigation_id TEXT, kind TEXT NOT NULL, title TEXT NOT NULL,
      body TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL, read_at TEXT
    );
    """)
    return conn

def verdict(result):
    return str(result.get("classification") or result.get("verdict") or "Unknown")[:100]

def score(result):
    try: return float(result.get("score")) if result.get("score") is not None else None
    except (ValueError, TypeError): return None

def revalidation_history(claim, limit=20):
    fp=memory.fingerprint(claim)
    conn=_conn()
    rows=conn.execute("SELECT * FROM cache_revalidation_runs WHERE fingerprint=? ORDER BY id DESC LIMIT ?",(fp,max(1,min(int(limit),100)))).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def revalidate_expired(limit=10, analyzer=None):
    """Re-fetch evidence for expired cache rows. A lease and run record prevent duplicate workers."""
    if analyzer is None:
        from analysis_engine import analyze_claim
        analyzer=analyze_claim
    candidates=memory.revalidation_candidates(max(1,min(int(limit),100)))
    output=[]
    for item in candidates:
        fp=item["fingerprint"]; now=_now()
        conn=_conn()
        conn.execute("DELETE FROM revalidation_leases WHERE lease_until<=?",(now,))
        lease=conn.execute("SELECT lease_until FROM revalidation_leases WHERE fingerprint=?",(fp,)).fetchone()
        if lease:
            conn.close(); output.append({"fingerprint":fp,"status":"already_running"}); continue
        conn.execute("INSERT OR REPLACE INTO revalidation_leases VALUES(?,?)",(fp,(datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat()))
        cur=conn.execute("INSERT INTO cache_revalidation_runs(fingerprint,status,started_at) VALUES(?,?,?)",(fp,"running",now))
        run_id=cur.lastrowid; conn.commit(); conn.close()
        try:
            fresh=analyzer(item["claim"],save_to_database=False)
            sources=memory._safe_sources(fresh)
            if not sources:
                raise ValueError("no_safe_sources")
            old=memory.get_cached_analysis(item["claim"])
            old_result=(old or {}).get("result") or {}
            old_verdict=verdict(old_result) if old_result else "Expired/unknown"
            old_score=score(old_result) if old_result else None
            new_verdict=verdict(fresh); new_score=score(fresh)
            # Cache only after fresh analysis has returned safe HTTP(S) source URLs.
            memory.cache_analysis(item["claim"],fresh)
            changed=(old_verdict!=new_verdict) or (old_score is not None and new_score is not None and abs(old_score-new_score)>=10)
            summary="Verdict or score changed" if changed else "Fresh evidence checked; no material verdict/score change detected"
            conn=_conn()
            conn.execute("""UPDATE cache_revalidation_runs SET old_verdict=?,new_verdict=?,old_score=?,new_score=?,
                status=?,source_count=?,summary=?,finished_at=? WHERE id=?""",
                (old_verdict,new_verdict,old_score,new_score,"changed" if changed else "unchanged",len(sources),summary,_now(),run_id))
            conn.execute("DELETE FROM revalidation_leases WHERE fingerprint=?",(fp,))
            conn.commit(); conn.close()
            output.append({"fingerprint":fp,"status":"changed" if changed else "unchanged","old_verdict":old_verdict,"new_verdict":new_verdict,"source_count":len(sources)})
        except Exception as exc:
            conn=_conn()
            conn.execute("UPDATE cache_revalidation_runs SET status='failed',error_code=?,summary=?,finished_at=? WHERE id=?",
                         (type(exc).__name__[:80],"Revalidation failed; expired result remains expired.",_now(),run_id))
            conn.execute("DELETE FROM revalidation_leases WHERE fingerprint=?",(fp,))
            conn.commit(); conn.close()
            output.append({"fingerprint":fp,"status":"failed","error":type(exc).__name__})
    return {"processed":len(output),"results":output}

def claim_family_features(claim):
    text=memory.normalize_claim(claim)
    tokens=memory._tokens(text)
    # Preserve numeric/date/negation tokens as material-change signals.
    material=sorted(set(re.findall(r"\b\d+(?:[.,]\d+)?\b",text)) | (tokens & {"not","never","no","only","before","after","until","unless"}))
    return {"normalized":text,"tokens":sorted(tokens),"material_tokens":material}

def claim_family_similarity(a,b):
    fa,fb=claim_family_features(a),claim_family_features(b)
    aa,bb=set(fa["tokens"]),set(fb["tokens"])
    overlap=len(aa&bb)/len(aa|bb) if aa|bb else 0.0
    material_changed=fa["material_tokens"]!=fb["material_tokens"]
    return {"similarity":round(overlap,4),"candidate_family":overlap>=0.28 and len(aa&bb)>=2,
            "material_change":material_changed,"must_reverify":material_changed or overlap<0.85,
            "shared_tokens":sorted(aa&bb),"changed_material_tokens":{"left":fa["material_tokens"],"right":fb["material_tokens"]}}

def evaluate_claim_families(dataset_path=None):
    path=Path(dataset_path) if dataset_path else Path(__file__).parent/"data"/"claim_family_eval.jsonl"
    rows=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip(): rows.append(json.loads(line))
    tp=fp=tn=fn=0
    for row in rows:
        predicted=claim_family_similarity(row["claim_a"],row["claim_b"])["candidate_family"]
        actual=bool(row["same_family"])
        if predicted and actual: tp+=1
        elif predicted: fp+=1
        elif actual: fn+=1
        else: tn+=1
    p=tp/(tp+fp) if tp+fp else 0
    r=tp/(tp+fn) if tp+fn else 0
    return {"dataset":str(path),"n":len(rows),"tp":tp,"fp":fp,"tn":tn,"fn":fn,
            "precision":round(p,4),"recall":round(r,4),"f1":round(2*p*r/(p+r),4) if p+r else 0,
            "note":"Small curated smoke benchmark; not representative of real-world claim distribution."}

def build_provenance_graph(investigation_id, claim, sources):
    """Build claim -> source nodes/edges; source URL must be absolute HTTP(S)."""
    now=_now(); claim_id="claim:"+hashlib.sha256((investigation_id+claim).encode()).hexdigest()[:24]
    safe=[]
    for src in (sources or [])[:100]:
        if not isinstance(src,dict): continue
        url=str(src.get("url") or src.get("link") or "").strip()
        parsed=urlparse(url)
        if parsed.scheme not in ("http","https") or not parsed.netloc: continue
        sid="source:"+hashlib.sha256(url.encode()).hexdigest()[:24]
        safe.append((sid,src,url))
    conn=_conn()
    conn.execute("INSERT OR REPLACE INTO provenance_nodes VALUES(?,?,?,?,?,?,?)",
        (claim_id,investigation_id,"claim",claim[:2000],None,json.dumps({"investigation_id":investigation_id}),now))
    for sid,src,url in safe:
        conn.execute("INSERT OR IGNORE INTO provenance_nodes VALUES(?,?,?,?,?,?,?)",
            (sid,None,"source",str(src.get("title") or src.get("publisher") or url)[:500],url,
             json.dumps({"publisher":str(src.get("publisher") or "")[:200],"published_at":src.get("published_at") or src.get("date"),
                         "stance":str(src.get("stance") or "unknown")[:40]},ensure_ascii=False),now))
        conn.execute("INSERT OR IGNORE INTO provenance_edges VALUES(?,?,?,?)",(claim_id,sid,str(src.get("stance") or "cites")[:40],now))
    conn.commit(); conn.close()
    return get_provenance_graph(investigation_id)

def get_provenance_graph(investigation_id):
    conn=_conn()
    nodes=[dict(r) for r in conn.execute("SELECT * FROM provenance_nodes WHERE investigation_id=? OR id IN (SELECT target_id FROM provenance_edges WHERE source_id IN (SELECT id FROM provenance_nodes WHERE investigation_id=?))",(investigation_id,investigation_id))]
    ids={n["id"] for n in nodes}
    edges=[dict(r) for r in conn.execute("SELECT * FROM provenance_edges") if r["source_id"] in ids and r["target_id"] in ids]
    conn.close()
    for node in nodes:
        try: node["metadata"]=json.loads(node.pop("metadata_json"))
        except Exception: node["metadata"]={}
    return {"nodes":nodes,"edges":edges}

def extract_image_text(image_bytes):
    """Optional local OCR. Requires Pillow + pytesseract and the Tesseract binary."""
    try:
        from PIL import Image
        import pytesseract
        import io
        image=Image.open(io.BytesIO(image_bytes))
        if image.width*image.height > 25_000_000: raise ValueError("Image dimensions exceed safety limit.")
        text=pytesseract.image_to_string(image)
        if not text.strip(): raise ValueError("No readable text found in image.")
        return {"text":text[:30000],"engine":"tesseract","warning":"OCR may misread names, numbers and dates; compare with original image."}
    except ImportError as exc:
        raise RuntimeError("OCR dependencies missing; install Pillow and pytesseract and the Tesseract system binary.") from exc

def detect_language(text):
    """Best-effort language tag, never a translation or evidence claim."""
    try:
        from langdetect import detect
        return detect(text[:5000])
    except Exception:
        # Script-level fallback is intentionally limited.
        if re.search(r"[\u0c80-\u0cff]",text): return "kn"
        if re.search(r"[\u0900-\u097f]",text): return "hi"
        if re.search(r"[\u0b80-\u0bff]",text): return "ta"
        if re.search(r"[\u0c00-\u0c7f]",text): return "te"
        if re.search(r"[\u0980-\u09ff]",text): return "bn"
        return "unknown"

def multilingual_match_candidates(claim, limit=10):
    """Match same-script or explicit cross-language aliases; no machine translation is trusted as evidence."""
    from context_memory import related_investigations, find_alias_matches
    # Only search the current session's private memory when caller supplies its session id.
    return {"language":detect_language(claim),"note":"Automatic translation is not used to infer truth. Use verified aliases or translate then verify the original-language sources."}
