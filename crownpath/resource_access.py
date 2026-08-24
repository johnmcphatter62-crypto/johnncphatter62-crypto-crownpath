import uuid
from datetime import datetime, timezone
from crownpath.database import connect
from crownpath.permissions import has_permission
from crownpath.audit import record_audit

def now_iso(): return datetime.now(timezone.utc).isoformat()

def assign_resource(user_id, resource_type, resource_id, access_level="VIEW"):
    con=connect()
    try:
        con.execute("""INSERT OR IGNORE INTO resource_assignments
        (assignment_id,user_id,resource_type,resource_id,access_level,created_at)
        VALUES (?,?,?,?,?,?)""",
        (f"CP-ASG-{uuid.uuid4().hex[:12].upper()}",user_id,resource_type.upper(),resource_id,access_level.upper(),now_iso()))
        con.commit()
    finally: con.close()

def has_assignment(user_id, resource_type, resource_id, access_level="VIEW"):
    con=connect()
    try:
        row=con.execute("""SELECT 1 FROM resource_assignments
        WHERE user_id=? AND resource_type=? AND resource_id=?
        AND access_level IN (?, 'MANAGE') LIMIT 1""",
        (user_id,resource_type.upper(),resource_id,access_level.upper())).fetchone()
        return row is not None
    finally: con.close()

def can_access_resource(user, permission, resource_type, resource_id, access_level="VIEW"):
    if not has_permission(user,permission):
        record_audit(user['user_id'],'RESOURCE_ACCESS','AUTHORIZATION','DENIED',resource_type,resource_id,f'Missing permission: {permission}')
        return False
    if user['role'].upper()=='OWNER':
        record_audit(user['user_id'],'RESOURCE_ACCESS','AUTHORIZATION','ALLOWED',resource_type,resource_id,'Owner access')
        return True
    if resource_type.upper()=='LEARNER' and resource_id==user['user_id']:
        record_audit(user['user_id'],'RESOURCE_ACCESS','AUTHORIZATION','ALLOWED',resource_type,resource_id,'Self access')
        return True
    if has_assignment(user['user_id'],resource_type,resource_id,access_level):
        record_audit(user['user_id'],'RESOURCE_ACCESS','AUTHORIZATION','ALLOWED',resource_type,resource_id,'Assigned resource')
        return True
    record_audit(user['user_id'],'RESOURCE_ACCESS','AUTHORIZATION','DENIED',resource_type,resource_id,'No object-level assignment')
    return False
