import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from crownpath.database import init_db
from crownpath.auth import authenticate, create_access_token, create_user, decode_access_token, get_user_by_id, public_user
from crownpath.permissions import has_permission, permissions_for_role
from crownpath.production_config import production_readiness
from crownpath.startup_guard import validate_startup
from crownpath.release_checks import release_checks
from crownpath.recovery import recovery_plan
from crownpath.music_provider import PandoraBusinessAdapter
from crownpath.security_headers import SecurityHeadersMiddleware
from crownpath.audio_service import seed_audio_stations, seed_audio_zones, list_audio_stations, list_audio_zones
from crownpath.playback_controller import seed_devices, list_devices, playback_state

app=FastAPI(title="CrownPath",version="1.5.0-github")
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
class LoginRequest(BaseModel):
    email:EmailStr
    password:str

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

@app.get("/")
def home(): return FileResponse(FRONTEND_DIR/"index.html")

@app.get("/api/health")
def health():
    return {"application":"CrownPath","version":"1.5.0-github","overall":"HEALTHY","environment":"demo" if DEMO_MODE else "configured"}

@app.post("/api/auth/register")
def register(payload:RegisterRequest,response:Response):
    try: user=create_user(payload.name,str(payload.email),payload.password,payload.role)
    except ValueError as exc: raise HTTPException(400,str(exc))
    except Exception: raise HTTPException(409,"Account could not be created.")
    token=create_access_token(user["user_id"])
    response.set_cookie("crownpath_session",token,httponly=True,secure=COOKIE_SECURE,samesite="lax",max_age=1800,path="/")
    return {"authenticated":True,"user":public_user(user)}

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

@app.get("/api/avatar/startup/{role}")
def avatar_startup(role:str):
    role=role.upper()
    messages={"OWNER":"Welcome to CrownPath. I can guide you through operations, Academy, security, audio, and launch readiness.","INSTRUCTOR":"Welcome, Instructor. I can guide your teaching, digital content, and classroom tools.","BARBER":"Welcome to your Barber pathway.","COSMETOLOGY_PRO":"Welcome to your Cosmetology pathway.","HOME_CARE":"Welcome to your Home Care pathway."}
    return {"role":role,"message":messages.get(role,"Welcome to CrownPath."),"guide_enabled":True}

@app.get("/api/academy")
def academy(user=Depends(require_permission("academy.view"))):
    return {"modules":[{"title":"Professional Foundations","status":"READY"},{"title":"Hair & Scalp Science","status":"READY"},{"title":"Digital Learning Lab","status":"READY"},{"title":"Business & Client Experience","status":"READY"}]}

@app.get("/api/digital-content")
def digital_content(user=Depends(require_permission("digital.view"))):
    return {"assets":[{"type":"VIDEO","title":"Hair & Scalp Foundations"},{"type":"3D_MODEL","title":"Interactive Hair Follicle"},{"type":"ANIMATION","title":"Sectioning Demonstration"},{"type":"QUIZ","title":"Knowledge Check"}]}

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
