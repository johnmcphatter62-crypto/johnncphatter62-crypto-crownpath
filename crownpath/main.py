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
from crownpath.models import InstructorRequest, LearnerProgress, User
from crownpath.auth import authenticate, create_access_token, create_user, create_owner, decode_access_token, get_user_by_id, owner_exists, public_user, list_users, set_user_role, set_user_active
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

app=FastAPI(title="CrownPath",version="1.11.0-github")
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

def current_user(request:Request):
    token=request.cookies.get("crownpath_session")
    user_id=decode_access_token(token) if token else None
    user=get_user_by_id(user_id) if user_id else None
    if not user or not user["active"]: raise HTTPException(401,"Authentication required.")
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
        ],
        "BARBER":[
            ("barber-foundations","Barbering Foundations"),
            ("barber-hair-scalp","Hair & Scalp Science"),
            ("barber-cutting-grooming","Cutting, Fading & Grooming"),
            ("barber-consultation-safety","Client Consultation & Shop Safety"),
        ],
        "COSMETOLOGY_PRO":[
            ("cosmetology-foundations","Cosmetology Foundations"),
            ("cosmetology-hair-scalp","Hair & Scalp Science"),
            ("cosmetology-chemical-safety","Chemical Services & Product Safety"),
            ("cosmetology-hair-replacement","Hair Replacement & Scalp Application Fundamentals"),
        ],
    }
    return catalogs.get(role,[])

def require_learner(user):
    role=user["role"].upper()
    if role in {"OWNER","INSTRUCTOR"}: raise HTTPException(403,"This feature is for learner pathways.")
    return role

@app.get("/")
def home(): return FileResponse(FRONTEND_DIR/"index.html")

@app.get("/api/health")
def health():
    return {"application":"CrownPath","version":"1.11.0-github","overall":"HEALTHY","environment":"demo" if DEMO_MODE else "configured"}

@app.post("/api/auth/register")
def register(payload:RegisterRequest,response:Response):
    try: user=create_user(payload.name,str(payload.email),payload.password,payload.role)
    except ValueError as exc: raise HTTPException(400,str(exc))
    except Exception: raise HTTPException(409,"Account could not be created.")
    token=create_access_token(user["user_id"])
    response.set_cookie("crownpath_session",token,httponly=True,secure=COOKIE_SECURE,samesite="lax",max_age=1800,path="/")
    return {"authenticated":True,"user":public_user(user)}

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
    if user["mfa_enabled"]: return {"authenticated":False,"mfa_required":True,"user_id":user["user_id"]}
    token=create_access_token(user["user_id"])
    response.set_cookie("crownpath_session",token,httponly=True,secure=COOKIE_SECURE,samesite="lax",max_age=1800,path="/")
    return {"authenticated":True,"user":public_user(user)}

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
        {"type":"QUIZ","title":"Pathway Knowledge Check"},
    ]
    return {"pathway":pathway_names.get(role,role.replace("_"," ").title()),"role":role,"modules":modules,"digital_content":digital,"overall_progress":overall,"next_step":next_item["title"] if next_item else "Pathway lessons complete"}

@app.post("/api/learner/lessons/{lesson_id}/open")
def open_lesson(lesson_id:str,user=Depends(require_permission("academy.view"))):
    role=require_learner(user)
    allowed=dict(learner_catalog(role))
    if lesson_id not in allowed: raise HTTPException(404,"Lesson not found for this pathway.")
    content=get_lesson_content(lesson_id)
    if not content: raise HTTPException(404,"Lesson content is not available yet.")
    db=session(); now=datetime.now(timezone.utc)
    try:
        item=db.scalar(select(LearnerProgress).where(LearnerProgress.user_id==user["user_id"],LearnerProgress.lesson_id==lesson_id))
        if not item:
            item=LearnerProgress(progress_id=f"CP-LP-{uuid.uuid4().hex[:12].upper()}",user_id=user["user_id"],lesson_id=lesson_id,status="IN_PROGRESS",progress_percent=25,opened_at=now,updated_at=now)
            db.add(item)
        elif item.status!="COMPLETED":
            item.status="IN_PROGRESS"; item.progress_percent=max(item.progress_percent,25); item.opened_at=item.opened_at or now; item.updated_at=now
        db.commit(); db.refresh(item)
        return {"lesson":{"lesson_id":lesson_id,"title":allowed[lesson_id],"status":item.status,"progress":item.progress_percent,"content":content}}
    finally: db.close()

@app.post("/api/learner/lessons/{lesson_id}/complete")
def complete_lesson(lesson_id:str,user=Depends(require_permission("academy.view"))):
    role=require_learner(user)
    allowed=dict(learner_catalog(role))
    if lesson_id not in allowed: raise HTTPException(404,"Lesson not found for this pathway.")
    db=session(); now=datetime.now(timezone.utc)
    try:
        item=db.scalar(select(LearnerProgress).where(LearnerProgress.user_id==user["user_id"],LearnerProgress.lesson_id==lesson_id))
        if not item:
            item=LearnerProgress(progress_id=f"CP-LP-{uuid.uuid4().hex[:12].upper()}",user_id=user["user_id"],lesson_id=lesson_id,opened_at=now)
            db.add(item)
        item.status="COMPLETED"; item.progress_percent=100; item.opened_at=item.opened_at or now; item.completed_at=now; item.updated_at=now
        db.commit(); db.refresh(item)
        return {"lesson":{"lesson_id":lesson_id,"title":allowed[lesson_id],"status":item.status,"progress":item.progress_percent}}
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

@app.get("/api/avatar/startup/{role}")
def avatar_startup(role:str):
    role=role.upper(); messages={"OWNER":"Welcome to CrownPath. I can guide you through operations, Academy, security, audio, and launch readiness.","INSTRUCTOR":"Welcome, Instructor. I can guide your teaching, digital content, and classroom tools.","BARBER":"Welcome to your Barber pathway.","COSMETOLOGY_PRO":"Welcome to your Cosmetology pathway.","HOME_CARE":"Welcome to your Home Care pathway."}
    return {"role":role,"message":messages.get(role,"Welcome to CrownPath."),"guide_enabled":True}
@app.get("/api/academy")
def academy(user=Depends(require_permission("academy.view"))): return {"modules":[{"title":"Professional Foundations","status":"READY"},{"title":"Hair & Scalp Science","status":"READY"},{"title":"Digital Learning Lab","status":"READY"},{"title":"Business & Client Experience","status":"READY"}]}
@app.get("/api/digital-content")
def digital_content(user=Depends(require_permission("digital.view"))): return {"assets":[{"type":"VIDEO","title":"Hair & Scalp Foundations"},{"type":"3D_MODEL","title":"Interactive Hair Follicle"},{"type":"ANIMATION","title":"Sectioning Demonstration"},{"type":"QUIZ","title":"Knowledge Check"}]}
@app.get("/api/audio/stations")
def stations(): return {"stations":list_audio_stations(),"notice":"Production playback requires an authorized business music source."}
@app.get("/api/audio/zones")
def zones(): return {"zones":list_audio_zones()}
@app.get("/api/audio/devices")
def devices(): return {"devices":list_devices()}
@app.get("/api/audio/zones/{zone_id}/playback")
def playback(zone_id:str):
    state=playback_state(zone_id)
    if not state: raise HTTPException(404,"Audio zone not found.")
    return state
@app.get("/api/audio/provider")
def audio_provider(): return PandoraBusinessAdapter().status()
@app.get("/api/production/readiness")
def readiness(user=Depends(require_permission("security.manage"))): return production_readiness()
@app.get("/api/release/checks")
def checks(user=Depends(require_permission("security.manage"))): return release_checks()
@app.get("/api/release/recovery-plan")
def recovery(user=Depends(require_permission("security.manage"))): return recovery_plan()
@app.get("/api/startup/status")
def startup(): return startup_status