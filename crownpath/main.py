import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from crownpath.database import init_db, session
from crownpath.models import AuditEvent, InstructorRequest, LearnerLessonStep, LearnerProgress, User
from crownpath.auth import authenticate, create_access_token, create_mfa_challenge, create_user, create_owner, decode_access_token, decode_mfa_challenge, enable_mfa, get_user_by_id, mfa_provisioning_uri, owner_exists, public_user, list_users, set_user_role, set_user_active, start_mfa_setup, verify_mfa_code
from crownpath.permissions import has_permission, permissions_for_role
from crownpath.production_config import production_readiness
from crownpath.startup_guard import validate_startup
from crownpath.release_checks import release_checks
from crownpath.recovery import recovery_plan
from crownpath.music_provider import PandoraBusinessAdapter
from crownpath.security_headers import SecurityHeadersMiddleware
from crownpath.audio_service import seed_audio_stations, seed_audio_zones, list_audio_stations, list_audio_zones
from crownpath.playback_controller import seed_devices, list_devices, playback_state
from crownpath.lesson_content import get_lesson_content
from crownpath.curriculum_models import CurriculumCourse, CurriculumLesson, CurriculumLessonVersion, CurriculumProgram, CurriculumUnit, CurriculumUnitLesson
from crownpath.curriculum_seed import seed_legacy_curriculum

app=FastAPI(title="CrownPath",version="1.15.0-github")
app.add_middleware(SecurityHeadersMiddleware)
startup_status=validate_startup()
BASE_DIR=Path(__file__).resolve().parent.parent
FRONTEND_DIR=BASE_DIR/"frontend"
DEMO_MODE=os.getenv("CROWNPATH_DEMO_MODE","true").lower()=="true"
REQUIRE_HTTPS=os.getenv("CROWNPATH_REQUIRE_HTTPS","false").lower()=="true"
COOKIE_SECURE=REQUIRE_HTTPS or not DEMO_MODE
init_db(); seed_audio_stations(); seed_audio_zones(); seed_devices()
app.mount("/static",StaticFiles(directory=FRONTEND_DIR),name="static")

class RegisterRequest(BaseModel):
    name:str=Field(min_length=2,max_length=100)
    email:EmailStr
    password:str=Field(min_length=12,max_length=128)
    role:str="HOME_CARE"
class OwnerActivateRequest(BaseModel):
    name:str=Field(min_length=2,max_length=100)
    email:EmailStr
    password:str=Field(min_length=12,max_length=128)
    activation_code:str=Field(min_length=6,max_length=64)
class LoginRequest(BaseModel):
    email:EmailStr
    password:str
class MfaVerifyRequest(BaseModel):
    challenge:str=Field(min_length=20,max_length=4096)
    code:str=Field(min_length=6,max_length=8)
class MfaEnableRequest(BaseModel):
    code:str=Field(min_length=6,max_length=8)
class RoleUpdateRequest(BaseModel):
    role:str
    active:bool|None=None
class ActiveUpdateRequest(BaseModel):
    active:bool
class InstructorRequestCreate(BaseModel):
    statement:str=Field(min_length=10,max_length=1000)
class InstructorReviewRequest(BaseModel):
    decision:str
    note:str|None=Field(default=None,max_length=1000)
class CurriculumDecisionRequest(BaseModel):
    note:str|None=Field(default=None,max_length=1000)
class CurriculumVersionCreateRequest(BaseModel):
    content:dict
    note:str|None=Field(default=None,max_length=1000)

def release_flag_enabled(name:str) -> bool:
    return os.getenv(name, "false").strip().lower() == "true"

def role_access_approved(role:str) -> bool:
    role = role.upper()
    if role == "OWNER":
        return True
    if role == "INSTRUCTOR":
        return release_flag_enabled("CROWNPATH_INSTRUCTOR_ACCESS_APPROVED")
    return role in {"HOME_CARE", "BARBER", "COSMETOLOGY_PRO"} and release_flag_enabled("CROWNPATH_LEARNER_ACCESS_APPROVED")

def enrollment_approved() -> bool:
    return release_flag_enabled("CROWNPATH_LEARNER_ACCESS_APPROVED") and release_flag_enabled("CROWNPATH_LEARNER_ENROLLMENT_APPROVED")

def current_user(request:Request):
    token=request.cookies.get("crownpath_session")
    user_id=decode_access_token(token) if token else None
    user=get_user_by_id(user_id) if user_id else None
    if not user or not user["active"]: raise HTTPException(401,"Authentication required.")
    if not role_access_approved(user["role"]): raise HTTPException(403,"This account is not open during owner testing.")
    return user

def require_permission(permission:str):
    def dependency(user=Depends(current_user)):
        if not has_permission(user,permission): raise HTTPException(403,"Permission denied.")
        return user
    return dependency

def request_dict(item:InstructorRequest):
    return {"request_id":item.request_id,"user_id":item.user_id,"statement":item.statement,"status":item.status,"reviewed_by":item.reviewed_by,"review_note":item.review_note,"reviewed_at":item.reviewed_at,"created_at":item.created_at}

def learner_catalog(role:str):
    catalogs={
        "HOME_CARE":[
            ("home-care-foundations","Client Safety & Home Care Foundations"),
            ("home-care-sanitation","Sanitation & Infection Control"),
            ("home-care-communication","Professional Communication"),
            ("home-care-documentation","Care Documentation"),
            ("wellness-client-experience","Wellness Client Experience & Professional Boundaries"),
            ("avatar-bot-builder-foundations","CrownPath Avatar & Bot Builder Foundations"),
        ],
        "BARBER":[
            ("barber-foundations","Barbering Foundations"),
            ("barber-hair-scalp","Hair & Scalp Science"),
            ("barber-scalp-camera-assessment","Scalp Camera & AI-Assisted Cosmetic Assessment"),
            ("barber-cutting-grooming","Cutting, Fading & Grooming"),
            ("barber-consultation-safety","Client Consultation & Shop Safety"),
            ("wellness-client-experience","Beauty & Wellness Client Experience"),
            ("wellness-fitness-foundations","Fitness, Recovery & General Wellness Foundations"),
            ("avatar-bot-builder-foundations","CrownPath Avatar & Bot Builder Foundations"),
        ],
        "COSMETOLOGY_PRO":[
            ("cosmetology-foundations","Cosmetology Foundations"),
            ("cosmetology-hair-scalp","Hair & Scalp Science"),
            ("cosmetology-scalp-camera-assessment","Scalp Camera & AI-Assisted Cosmetic Assessment"),
            ("cosmetology-chemical-safety","Chemical Services & Product Safety"),
            ("cosmetology-hair-replacement","Non-Surgical Hair Replacement & Scalp Application"),
            ("cosmetology-makeup-artistry","Professional Makeup Artistry"),
            ("cosmetology-nail-care","Manicure & Pedicure Nail Care"),
            ("wellness-massage-foundations","Wellness Massage Foundations & Scope Awareness"),
            ("wellness-fitness-foundations","Fitness, Recovery & General Wellness Foundations"),
            ("wellness-client-experience","Integrated Beauty & Wellness Client Experience"),
            ("avatar-bot-builder-foundations","CrownPath Avatar & Bot Builder Foundations"),
        ],
    }
    return catalogs.get(role,[])

def require_learner(user):
    role=user["role"].upper()
    if role in {"OWNER","INSTRUCTOR"}: raise HTTPException(403,"This feature is for learner pathways.")
    return role

def lesson_for_role(role:str,lesson_id:str):
    allowed=dict(learner_catalog(role))
    if lesson_id not in allowed: raise HTTPException(404,"Lesson not found for this pathway.")
    content=get_lesson_content(lesson_id)
    if not content: raise HTTPException(404,"Lesson content is not available yet.")
    return allowed[lesson_id],content

def completed_step_indexes(db,user_id:str,lesson_id:str):
    rows=db.scalars(select(LearnerLessonStep).where(LearnerLessonStep.user_id==user_id,LearnerLessonStep.lesson_id==lesson_id,LearnerLessonStep.completed==True)).all()
    return sorted({row.step_index for row in rows})

def sync_lesson_progress(db,user_id:str,lesson_id:str,total_steps:int,now:datetime):
    item=db.scalar(select(LearnerProgress).where(LearnerProgress.user_id==user_id,LearnerProgress.lesson_id==lesson_id))
    indexes=completed_step_indexes(db,user_id,lesson_id)
    completed_count=len(indexes)
    progress=round(completed_count/total_steps*100) if total_steps else 0
    if not item:
        item=LearnerProgress(progress_id=f"CP-LP-{uuid.uuid4().hex[:12].upper()}",user_id=user_id,lesson_id=lesson_id,status="IN_PROGRESS",progress_percent=progress,opened_at=now,updated_at=now)
        db.add(item)
    elif item.status!="COMPLETED":
        item.status="IN_PROGRESS"; item.progress_percent=progress; item.opened_at=item.opened_at or now; item.updated_at=now
    if total_steps and completed_count>=total_steps:
        item.status="COMPLETED"; item.progress_percent=100; item.completed_at=item.completed_at or now; item.updated_at=now
    return item,indexes

@app.get("/")
def home(): return FileResponse(FRONTEND_DIR/"index.html")

@app.get("/api/health")
def health():
    return {"application":"CrownPath","version":"1.15.0-github","overall":"HEALTHY","environment":"demo" if DEMO_MODE else "configured"}

@app.post("/api/auth/register")
def register(payload:RegisterRequest,response:Response):
    if not enrollment_approved(): raise HTTPException(403,"Learner enrollment is closed during owner testing.")
    try: user=create_user(payload.name,str(payload.email),payload.password,payload.role)
    except ValueError as exc: raise HTTPException(400,str(exc))
    except Exception: raise HTTPException(409,"Account could not be created.")
    token=create_access_token(user["user_id"])
    response.set_cookie("crownpath_session",token,httponly=True,secure=COOKIE_SECURE,samesite="lax",max_age=1800,path="/")
    return {"authenticated":True,"user":public_user(user)}

@app.get("/api/auth/enrollment/status")
def enrollment_status():
    return {"enabled":enrollment_approved(), "learner_access":release_flag_enabled("CROWNPATH_LEARNER_ACCESS_APPROVED"), "instructor_access":release_flag_enabled("CROWNPATH_INSTRUCTOR_ACCESS_APPROVED")}

@app.get("/api/auth/owner-activation/status")
def owner_activation_status():
    return {"available":not owner_exists() and bool(os.getenv("CROWNPATH_OWNER_EMAIL")) and bool(os.getenv("CROWNPATH_OWNER_ACTIVATION_CODE"))}

@app.post("/api/auth/owner-activation")
def owner_activation(payload:OwnerActivateRequest,response:Response):
    try: user=create_owner(payload.name,str(payload.email),payload.password,payload.activation_code)
    except ValueError as exc: raise HTTPException(400,str(exc))
    token=create_access_token(user["user_id"])
    response.set_cookie("crownpath_session",token,httponly=True,secure=COOKIE_SECURE,samesite="lax",max_age=1800,path="/")
    return {"authenticated":True,"owner_activated":True,"user":public_user(user)}

@app.post("/api/auth/login")
def login(payload:LoginRequest,response:Response):
    user,status=authenticate(str(payload.email),payload.password)
    if status=="LOCKED": raise HTTPException(423,"Account temporarily locked.")
    if not user: raise HTTPException(401,"Invalid sign-in.")
    if not role_access_approved(user["role"]): raise HTTPException(403,"This account is not open during owner testing.")
    if user["mfa_enabled"]:
        return {"authenticated":False,"mfa_required":True,"challenge":create_mfa_challenge(user["user_id"])}
    token=create_access_token(user["user_id"])
    response.set_cookie("crownpath_session",token,httponly=True,secure=COOKIE_SECURE,samesite="lax",max_age=1800,path="/")
    return {"authenticated":True,"user":public_user(user)}

@app.post("/api/auth/mfa/verify")
def mfa_verify(payload:MfaVerifyRequest,response:Response):
    user_id=decode_mfa_challenge(payload.challenge)
    user=get_user_by_id(user_id) if user_id else None
    if not user or not user["active"] or not user["mfa_enabled"]: raise HTTPException(401,"MFA challenge is invalid or expired.")
    if not role_access_approved(user["role"]): raise HTTPException(403,"This account is not open during owner testing.")
    if not verify_mfa_code(user_id,payload.code.strip()): raise HTTPException(401,"Invalid authenticator or recovery code.")
    token=create_access_token(user_id)
    response.set_cookie("crownpath_session",token,httponly=True,secure=COOKIE_SECURE,samesite="lax",max_age=1800,path="/")
    return {"authenticated":True,"user":public_user(get_user_by_id(user_id))}

@app.post("/api/auth/mfa/setup")
def mfa_setup(user=Depends(current_user)):
    if user["mfa_enabled"]: raise HTTPException(409,"Multi-factor authentication is already enabled.")
    secret=start_mfa_setup(user["user_id"])
    uri=mfa_provisioning_uri(user["user_id"],user["email"])
    return {"secret":secret,"provisioning_uri":uri,"message":"Add this account to your authenticator app, then enter the current 6-digit code to confirm."}

@app.post("/api/auth/mfa/enable")
def mfa_enable(payload:MfaEnableRequest,user=Depends(current_user)):
    if user["mfa_enabled"]: raise HTTPException(409,"Multi-factor authentication is already enabled.")
    recovery_codes=enable_mfa(user["user_id"],payload.code.strip())
    if not recovery_codes: raise HTTPException(400,"Authenticator code could not be verified.")
    return {"mfa_enabled":True,"recovery_codes":recovery_codes,"user":public_user(get_user_by_id(user["user_id"]))}

@app.post("/api/auth/logout")
def logout(response:Response):
    response.delete_cookie("crownpath_session",path="/"); return {"authenticated":False}

@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    data=public_user(user); data["permissions"]=sorted(permissions_for_role(user["role"])); return data

@app.get("/api/learner/dashboard")
def learner_dashboard(user=Depends(require_permission("academy.view"))):
    role=require_learner(user)
    pathway_names={"HOME_CARE":"Home Care","BARBER":"Barber","COSMETOLOGY_PRO":"Cosmetology Pro"}
    catalog=learner_catalog(role)
    db=session()
    try:
        saved={item.lesson_id:item for item in db.scalars(select(LearnerProgress).where(LearnerProgress.user_id==user["user_id"])).all()}
        modules=[]
        for lesson_id,title in catalog:
            progress=saved.get(lesson_id)
            modules.append({"lesson_id":lesson_id,"title":title,"status":progress.status if progress else "NOT_STARTED","progress":progress.progress_percent if progress else 0})
        overall=round(sum(item["progress"] for item in modules)/len(modules)) if modules else 0
        next_item=next((item for item in modules if item["status"]!="COMPLETED"),None)
    finally: db.close()
    digital=[
        {"type":"VIDEO","title":"Orientation & Professional Standards"},
        {"type":"3D_MODEL","title":"Interactive Hair & Scalp Anatomy"} if role!="HOME_CARE" else {"type":"INTERACTIVE","title":"Safe Home Care Environment"},
        {"type":"ANIMATION","title":"Practical Skills Demonstration"},
        {"type":"AI_GUIDE","title":"CrownPath Avatar & Bot Learning Guide"},
        {"type":"QUIZ","title":"Pathway Knowledge Check"},
    ]
    return {"pathway":pathway_names.get(role,role.replace("_"," ").title()),"role":role,"modules":modules,"digital_content":digital,"overall_progress":overall,"next_step":next_item["title"] if next_item else "Pathway lessons complete"}

@app.post("/api/learner/lessons/{lesson_id}/open")
def open_lesson(lesson_id:str,user=Depends(require_permission("academy.view"))):
    role=require_learner(user)
    title,content=lesson_for_role(role,lesson_id)
    total_steps=len(content.get("steps",[]))
    db=session(); now=datetime.now(timezone.utc)
    try:
        item,indexes=sync_lesson_progress(db,user["user_id"],lesson_id,total_steps,now)
        db.commit(); db.refresh(item)
        return {"lesson":{"lesson_id":lesson_id,"title":title,"status":item.status,"progress":item.progress_percent,"content":content,"completed_steps":indexes,"total_steps":total_steps}}
    finally: db.close()

@app.post("/api/learner/lessons/{lesson_id}/steps/{step_index}/complete")
def complete_lesson_step(lesson_id:str,step_index:int,user=Depends(require_permission("academy.view"))):
    role=require_learner(user)
    title,content=lesson_for_role(role,lesson_id)
    total_steps=len(content.get("steps",[]))
    if step_index<1 or step_index>total_steps: raise HTTPException(404,"Lesson step not found.")
    db=session(); now=datetime.now(timezone.utc)
    try:
        step=db.scalar(select(LearnerLessonStep).where(LearnerLessonStep.user_id==user["user_id"],LearnerLessonStep.lesson_id==lesson_id,LearnerLessonStep.step_index==step_index))
        if not step:
            step=LearnerLessonStep(step_progress_id=f"CP-LS-{uuid.uuid4().hex[:12].upper()}",user_id=user["user_id"],lesson_id=lesson_id,step_index=step_index,completed=True,completed_at=now,updated_at=now)
            db.add(step); db.flush()
        elif not step.completed:
            step.completed=True; step.completed_at=now; step.updated_at=now; db.flush()
        item,indexes=sync_lesson_progress(db,user["user_id"],lesson_id,total_steps,now)
        db.commit(); db.refresh(item)
        return {"lesson":{"lesson_id":lesson_id,"title":title,"status":item.status,"progress":item.progress_percent,"completed_steps":indexes,"completed_step_count":len(indexes),"total_steps":total_steps}}
    finally: db.close()

@app.post("/api/learner/lessons/{lesson_id}/complete")
def complete_lesson(lesson_id:str,user=Depends(require_permission("academy.view"))):
    role=require_learner(user)
    title,content=lesson_for_role(role,lesson_id)
    total_steps=len(content.get("steps",[]))
    db=session(); now=datetime.now(timezone.utc)
    try:
        existing=set(completed_step_indexes(db,user["user_id"],lesson_id))
        for index in range(1,total_steps+1):
            if index not in existing:
                db.add(LearnerLessonStep(step_progress_id=f"CP-LS-{uuid.uuid4().hex[:12].upper()}",user_id=user["user_id"],lesson_id=lesson_id,step_index=index,completed=True,completed_at=now,updated_at=now))
        db.flush()
        item,indexes=sync_lesson_progress(db,user["user_id"],lesson_id,total_steps,now)
        db.commit(); db.refresh(item)
        return {"lesson":{"lesson_id":lesson_id,"title":title,"status":item.status,"progress":item.progress_percent,"completed_steps":indexes,"total_steps":total_steps}}
    finally: db.close()

@app.post("/api/instructor-requests")
def submit_instructor_request(payload:InstructorRequestCreate,user=Depends(current_user)):
    if user["role"] in {"OWNER","INSTRUCTOR"}: raise HTTPException(400,"This account does not need an Instructor request.")
    db=session()
    try:
        pending=db.scalar(select(InstructorRequest).where(InstructorRequest.user_id==user["user_id"],InstructorRequest.status=="PENDING"))
        if pending: raise HTTPException(409,"An Instructor request is already pending.")
        item=InstructorRequest(request_id=f"CP-IR-{uuid.uuid4().hex[:12].upper()}",user_id=user["user_id"],statement=payload.statement.strip(),status="PENDING",created_at=datetime.now(timezone.utc))
        db.add(item); db.commit(); db.refresh(item)
        return {"request":request_dict(item)}
    finally: db.close()

@app.get("/api/instructor-requests/me")
def my_instructor_requests(user=Depends(current_user)):
    db=session()
    try:
        items=db.scalars(select(InstructorRequest).where(InstructorRequest.user_id==user["user_id"]).order_by(InstructorRequest.created_at.desc())).all()
        return {"requests":[request_dict(item) for item in items]}
    finally: db.close()

@app.get("/api/owner/instructor-requests")
def owner_instructor_requests(user=Depends(require_permission("staff.manage"))):
    db=session()
    try:
        items=db.scalars(select(InstructorRequest).order_by(InstructorRequest.created_at.desc())).all()
        result=[]
        for item in items:
            applicant=db.get(User,item.user_id)
            data=request_dict(item)
            data["applicant"]={"name":applicant.name,"email":applicant.email,"role":applicant.role,"active":applicant.active} if applicant else None
            result.append(data)
        return {"requests":result}
    finally: db.close()

@app.patch("/api/owner/instructor-requests/{request_id}")
def owner_review_instructor_request(request_id:str,payload:InstructorReviewRequest,user=Depends(require_permission("staff.manage"))):
    decision=payload.decision.strip().upper()
    if decision not in {"APPROVE","DENY"}: raise HTTPException(400,"Decision must be APPROVE or DENY.")
    db=session()
    try:
        item=db.get(InstructorRequest,request_id)
        if not item: raise HTTPException(404,"Instructor request not found.")
        if item.status!="PENDING": raise HTTPException(409,"Instructor request has already been reviewed.")
        applicant=db.get(User,item.user_id)
        if not applicant: raise HTTPException(404,"Applicant account not found.")
        if applicant.role=="OWNER": raise HTTPException(400,"Owner account cannot be changed here.")
        item.status="APPROVED" if decision=="APPROVE" else "DENIED"
        item.reviewed_by=user["user_id"]
        item.review_note=(payload.note or "").strip() or None
        item.reviewed_at=datetime.now(timezone.utc)
        if decision=="APPROVE": applicant.role="INSTRUCTOR"; applicant.track="INSTRUCTOR"; applicant.active=True
        db.commit(); db.refresh(item)
        return {"request":request_dict(item),"applicant":public_user(get_user_by_id(applicant.user_id))}
    finally: db.close()

@app.get("/api/owner/users")
def owner_users(user=Depends(require_permission("staff.manage"))): return {"users":[public_user(item) for item in list_users()]}
@app.patch("/api/owner/users/{user_id}/role")
def owner_update_role(user_id:str,payload:RoleUpdateRequest,user=Depends(require_permission("staff.manage"))):
    try: updated=set_user_role(user_id,payload.role,payload.active)
    except ValueError as exc: raise HTTPException(400,str(exc))
    return {"user":public_user(updated)}
@app.patch("/api/owner/users/{user_id}/active")
def owner_update_active(user_id:str,payload:ActiveUpdateRequest,user=Depends(require_permission("staff.manage"))):
    try: updated=set_user_active(user_id,payload.active)
    except ValueError as exc: raise HTTPException(400,str(exc))
    return {"user":public_user(updated)}


@app.post("/api/owner/curriculum/seed")
def owner_seed_curriculum(user=Depends(require_permission("academy.manage"))):
    """Import the legacy CrownPath catalog into the database hierarchy.

    This action is idempotent and never approves or publishes curriculum.
    """
    return {"created": seed_legacy_curriculum(), "published": False}

@app.get("/api/owner/curriculum")
def owner_curriculum(user=Depends(require_permission("academy.manage"))):
    db=session()
    try:
        programs=db.scalars(select(CurriculumProgram).order_by(CurriculumProgram.title)).all()
        result=[]
        for program in programs:
            courses=db.scalars(select(CurriculumCourse).where(CurriculumCourse.program_id==program.program_id).order_by(CurriculumCourse.sequence)).all()
            course_items=[]
            for course in courses:
                units=db.scalars(select(CurriculumUnit).where(CurriculumUnit.course_id==course.course_id).order_by(CurriculumUnit.sequence)).all()
                unit_items=[]
                for unit in units:
                    assignments=db.scalars(select(CurriculumUnitLesson).where(CurriculumUnitLesson.unit_id==unit.unit_id).order_by(CurriculumUnitLesson.sequence)).all()
                    lesson_items=[]
                    for assignment in assignments:
                        lesson=db.get(CurriculumLesson,assignment.lesson_id)
                        if lesson:
                            lesson_items.append({"lesson_id":lesson.lesson_id,"title":lesson.title,"sequence":assignment.sequence,"required":assignment.required,"status":lesson.status,"active_version":lesson.active_version})
                    unit_items.append({"unit_id":unit.unit_id,"title":unit.title,"sequence":unit.sequence,"lessons":lesson_items})
                course_items.append({"course_id":course.course_id,"title":course.title,"slug":course.slug,"status":course.status,"sequence":course.sequence,"units":unit_items})
            result.append({"program_id":program.program_id,"title":program.title,"slug":program.slug,"status":program.status,"courses":course_items})
        return {"programs":result}
    finally: db.close()

@app.get("/api/owner/curriculum/lessons/{lesson_id}/versions")
def owner_curriculum_versions(lesson_id:str,user=Depends(require_permission("academy.manage"))):
    db=session()
    try:
        lesson=db.get(CurriculumLesson,lesson_id)
        if not lesson: raise HTTPException(404,"Curriculum lesson not found.")
        versions=db.scalars(select(CurriculumLessonVersion).where(CurriculumLessonVersion.lesson_id==lesson_id).order_by(CurriculumLessonVersion.version.desc())).all()
        return {"lesson":{"lesson_id":lesson.lesson_id,"title":lesson.title,"status":lesson.status,"active_version":lesson.active_version},"versions":[{"version_id":v.version_id,"version":v.version,"source_type":v.source_type,"approved":v.approved,"approved_by":v.approved_by,"approved_at":v.approved_at,"created_at":v.created_at} for v in versions]}
    finally: db.close()


@app.post("/api/owner/curriculum/lessons/{lesson_id}/versions")
def owner_create_curriculum_version(lesson_id:str,payload:CurriculumVersionCreateRequest,user=Depends(require_permission("academy.manage"))):
    """Create a new unapproved draft without changing the active version."""
    db=session()
    try:
        lesson=db.get(CurriculumLesson,lesson_id)
        if not lesson: raise HTTPException(404,"Curriculum lesson not found.")
        versions=db.scalars(select(CurriculumLessonVersion).where(CurriculumLessonVersion.lesson_id==lesson_id).order_by(CurriculumLessonVersion.version.desc())).all()
        next_version=(versions[0].version if versions else 0)+1
        item=CurriculumLessonVersion(
            version_id=f"CP-LV-{uuid.uuid4().hex[:12].upper()}",lesson_id=lesson_id,version=next_version,
            content_json=json.dumps(payload.content),source_type="CROWNPATH_OWNER_EDIT",approved=False,
        )
        db.add(item)
        record_curriculum_audit(db,user["user_id"],"CURRICULUM_VERSION_CREATED",lesson_id,"SUCCESS",(payload.note or "").strip() or None)
        db.commit()
        return {"lesson_id":lesson_id,"version":next_version,"approved":False,"published":False,"active_version":lesson.active_version}
    finally: db.close()

@app.put("/api/owner/curriculum/lessons/{lesson_id}/versions/{version}")
def owner_update_curriculum_draft(lesson_id:str,version:int,payload:CurriculumVersionCreateRequest,user=Depends(require_permission("academy.manage"))):
    db=session()
    try:
        lesson=db.get(CurriculumLesson,lesson_id)
        if not lesson: raise HTTPException(404,"Curriculum lesson not found.")
        item=db.scalar(select(CurriculumLessonVersion).where(CurriculumLessonVersion.lesson_id==lesson_id,CurriculumLessonVersion.version==version))
        if not item: raise HTTPException(404,"Curriculum lesson version not found.")
        if item.approved: raise HTTPException(409,"Approved curriculum versions are immutable. Create a new draft to make changes.")
        if lesson.status=="PUBLISHED" and lesson.active_version==version: raise HTTPException(409,"The active published version cannot be edited. Create a new draft.")
        item.content_json=json.dumps(payload.content); item.source_type="CROWNPATH_OWNER_EDIT"
        record_curriculum_audit(db,user["user_id"],"CURRICULUM_VERSION_UPDATED",lesson_id,"SUCCESS",(payload.note or "").strip() or None)
        db.commit()
        return {"lesson_id":lesson_id,"version":version,"saved":True,"approved":False,"active_version":lesson.active_version}
    finally: db.close()

@app.get("/api/owner/curriculum/lessons/{lesson_id}/versions/{version}/content")
def owner_curriculum_version_content(lesson_id:str,version:int,user=Depends(require_permission("academy.manage"))):
    db=session()
    try:
        item=db.scalar(select(CurriculumLessonVersion).where(CurriculumLessonVersion.lesson_id==lesson_id,CurriculumLessonVersion.version==version))
        if not item: raise HTTPException(404,"Curriculum lesson version not found.")
        return {"lesson_id":lesson_id,"version":version,"content":json.loads(item.content_json)}
    finally: db.close()

def record_curriculum_audit(db,user_id:str,action:str,lesson_id:str,result:str,reason:str|None=None):
    db.add(AuditEvent(user_id=user_id,action=action,category="CURRICULUM",resource_type="LESSON",resource_id=lesson_id,result=result,reason=reason))

@app.post("/api/owner/curriculum/lessons/{lesson_id}/versions/{version}/approve")
def owner_approve_curriculum_version(lesson_id:str,version:int,payload:CurriculumDecisionRequest,user=Depends(require_permission("academy.manage"))):
    db=session()
    try:
        lesson=db.get(CurriculumLesson,lesson_id)
        if not lesson: raise HTTPException(404,"Curriculum lesson not found.")
        item=db.scalar(select(CurriculumLessonVersion).where(CurriculumLessonVersion.lesson_id==lesson_id,CurriculumLessonVersion.version==version))
        if not item: raise HTTPException(404,"Curriculum lesson version not found.")
        if item.approved: raise HTTPException(409,"This lesson version is already approved.")
        item.approved=True; item.approved_by=user["user_id"]; item.approved_at=datetime.now(timezone.utc)
        record_curriculum_audit(db,user["user_id"],"CURRICULUM_VERSION_APPROVED",lesson_id,"SUCCESS",(payload.note or "").strip() or None)
        db.commit()
        return {"lesson_id":lesson_id,"version":version,"approved":True,"published":lesson.status=="PUBLISHED"}
    finally: db.close()

@app.post("/api/owner/curriculum/lessons/{lesson_id}/versions/{version}/publish")
def owner_publish_curriculum_version(lesson_id:str,version:int,payload:CurriculumDecisionRequest,user=Depends(require_permission("academy.manage"))):
    db=session()
    try:
        lesson=db.get(CurriculumLesson,lesson_id)
        if not lesson: raise HTTPException(404,"Curriculum lesson not found.")
        item=db.scalar(select(CurriculumLessonVersion).where(CurriculumLessonVersion.lesson_id==lesson_id,CurriculumLessonVersion.version==version))
        if not item: raise HTTPException(404,"Curriculum lesson version not found.")
        if not item.approved:
            record_curriculum_audit(db,user["user_id"],"CURRICULUM_VERSION_PUBLISH_BLOCKED",lesson_id,"DENIED","Version must be approved before publication.")
            db.commit()
            raise HTTPException(409,"Approve this lesson version before publishing it.")
        lesson.active_version=version; lesson.status="PUBLISHED"
        record_curriculum_audit(db,user["user_id"],"CURRICULUM_VERSION_PUBLISHED",lesson_id,"SUCCESS",(payload.note or "").strip() or None)
        db.commit()
        return {"lesson_id":lesson_id,"version":version,"approved":True,"published":True}
    finally: db.close()

@app.get("/api/avatar/startup/{role}")
def avatar_startup(role:str):
    role=role.upper(); messages={"OWNER":"Welcome to CrownPath. I can guide you through operations, Academy, security, audio, Avatar & Bot Builder, and launch readiness.","INSTRUCTOR":"Welcome, Instructor. I can guide your teaching, digital content, Avatar & Bot Builder, and classroom tools.","BARBER":"Welcome to your Barber pathway. Your CrownPath guide can support lessons, scalp-camera education, practical skills, and bot-builder training.","COSMETOLOGY_PRO":"Welcome to your Cosmetology pathway. Your CrownPath guide can support beauty, scalp, makeup, nails, wellness, and bot-builder lessons.","HOME_CARE":"Welcome to your Home Care pathway. Your CrownPath guide can support safety, communication, client experience, and bot-builder lessons."}
    return {"role":role,"message":messages.get(role,"Welcome to CrownPath."),"guide_enabled":True}
@app.get("/api/academy")
def academy(user=Depends(require_permission("academy.view"))): return {"modules":[{"title":"Professional Foundations","status":"READY"},{"title":"Hair, Scalp & Imaging Science","status":"READY"},{"title":"Beauty, Grooming & Practical Skills","status":"READY"},{"title":"Wellness, Massage & Fitness Foundations","status":"READY"},{"title":"Avatar & Bot Builder Lab","status":"READY"},{"title":"Business & Client Experience","status":"READY"}]}
@app.get("/api/digital-content")
def digital_content(user=Depends(require_permission("digital.view"))): return {"assets":[{"type":"VIDEO","title":"Hair & Scalp Foundations"},{"type":"3D_MODEL","title":"Interactive Hair Follicle"},{"type":"ANIMATION","title":"Beauty & Grooming Skills Demonstration"},{"type":"AI_GUIDE","title":"Avatar & Bot Builder Learning Lab"},{"type":"QUIZ","title":"Knowledge Check"}]}
@app.get("/api/audio/stations")
def stations(user=Depends(require_permission("audio.view"))): return {"stations":list_audio_stations(),"notice":"Production playback requires an authorized business music source."}
@app.get("/api/audio/zones")
def zones(user=Depends(require_permission("audio.view"))): return {"zones":list_audio_zones()}
@app.get("/api/audio/devices")
def devices(user=Depends(require_permission("audio.view"))): return {"devices":list_devices()}
@app.get("/api/audio/zones/{zone_id}/playback")
def playback(zone_id:str,user=Depends(require_permission("audio.view"))):
    state=playback_state(zone_id)
    if not state: raise HTTPException(404,"Audio zone not found.")
    return state
@app.get("/api/audio/provider")
def audio_provider(user=Depends(require_permission("audio.view"))): return PandoraBusinessAdapter().status()
@app.get("/api/production/readiness")
def readiness(user=Depends(require_permission("security.manage"))): return production_readiness()
@app.get("/api/release/checks")
def checks(user=Depends(require_permission("security.manage"))): return release_checks()
@app.get("/api/release/recovery-plan")
def recovery(user=Depends(require_permission("security.manage"))): return recovery_plan()
@app.get("/api/startup/status")
def startup(): return startup_status
