"""Session-scoped notifications for Echo Mind."""
import json
from datetime import datetime, timezone
import context_memory

def _conn():
    conn=context_memory._conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS user_notifications (
      id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
      kind TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
      payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, read_at TEXT
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_session ON user_notifications(session_id,id DESC)")
    return conn

def create(session_id,title,body,kind="info",payload=None):
    if kind not in {"info","verdict_change","new_evidence","correction","system"}:
        raise ValueError("unsupported notification kind")
    payload=payload or {}
    if not isinstance(payload,dict) or len(json.dumps(payload,ensure_ascii=False))>10000:
        raise ValueError("payload must be a small JSON object")
    now=datetime.now(timezone.utc).isoformat()
    conn=_conn()
    cur=conn.execute("INSERT INTO user_notifications(session_id,kind,title,body,payload_json,created_at) VALUES(?,?,?,?,?,?)",
      (session_id,kind,title[:200],body[:4000],json.dumps(payload,ensure_ascii=False),now))
    conn.commit()
    result={"id":cur.lastrowid,"kind":kind,"title":title[:200],"body":body[:4000],"payload":payload,"created_at":now,"read":False}
    conn.close()
    return result

def list_for_session(session_id,limit=50):
    conn=_conn()
    rows=conn.execute("SELECT id,kind,title,body,payload_json,created_at,read_at FROM user_notifications WHERE session_id=? ORDER BY id DESC LIMIT ?",
      (session_id,max(1,min(int(limit),100)))).fetchall()
    conn.close()
    out=[]
    for row in rows:
        item=dict(row)
        item["payload"]=json.loads(item.pop("payload_json"))
        item["read"]=bool(item.pop("read_at"))
        out.append(item)
    return out

def mark_read(session_id,notification_id):
    conn=_conn()
    cur=conn.execute("UPDATE user_notifications SET read_at=? WHERE id=? AND session_id=?",
      (datetime.now(timezone.utc).isoformat(),int(notification_id),session_id))
    conn.commit()
    conn.close()
    return cur.rowcount>0
