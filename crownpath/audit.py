from datetime import datetime, timezone
from crownpath.database import connect

def now_iso(): return datetime.now(timezone.utc).isoformat()

def record_audit(user_id, action, category, result, resource_type=None, resource_id=None, reason=None):
    con=connect()
    try:
        con.execute("""INSERT INTO audit_events
        (user_id,action,category,resource_type,resource_id,result,reason,created_at)
        VALUES (?,?,?,?,?,?,?,?)""",
        (user_id,action,category,resource_type,resource_id,result,reason,now_iso()))
        con.commit()
    finally: con.close()

def recent_audit(limit=100):
    con=connect()
    try:
        rows=con.execute("SELECT * FROM audit_events ORDER BY audit_id DESC LIMIT ?",(limit,)).fetchall()
        return [dict(r) for r in rows]
    finally: con.close()
