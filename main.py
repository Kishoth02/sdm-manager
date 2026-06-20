from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from services import file_manager as fm
from routes.api import router
from ms_auth import get_auth_url, get_token_from_code
import os
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    fm.startup()
    files = fm.list_files()
    print(f"\n✅ MCQ Manager started")
    print(f"   Library: {len(files)} file(s) loaded")
    if files:
        for f in files:
            marker = " ← active" if f["active"] else ""
            print(f"   • {f['filename']} ({f['count']} MCQs){marker}")
    else:
        print("   Library is empty — drop MCQ files into library/ folder")
    print(f"   UI: http://localhost:8002\n")
    yield

app = FastAPI(title="MCQ Manager API", version="2.0", lifespan=lifespan)

# Session middleware must come before CORS
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "change-this-in-production"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Microsoft Login Routes ──────────────────────────────────────────────────

@app.get("/login")
def login():
    return RedirectResponse(get_auth_url())

@app.get("/auth/callback")
def auth_callback(request: Request, code: str = None):
    if not code:
        return RedirectResponse("/login")
    result = get_token_from_code(code)
    if "id_token_claims" not in result:
        print("AUTH ERROR:", result)
        return {"error": result}
    claims = result["id_token_claims"]
    request.session["user"] = {
        "name": claims.get("name", "User"),
        "username": claims.get("preferred_username", claims.get("oid")),
    }
    return RedirectResponse("/")

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    tenant_subdomain = os.getenv("TENANT_SUBDOMAIN")
    tenant_id = os.getenv("TENANT_ID")
    microsoft_logout_url = (
        f"https://{tenant_subdomain}.ciamlogin.com/{tenant_id}/oauth2/v2.0/logout"
        f"?post_logout_redirect_uri=https://sdm-manager-app.azurewebsites.net/login"
    )
    return RedirectResponse(microsoft_logout_url)

@app.get("/api/me")
def get_me(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return user

# ───────────────────────────────────────────────────────────────────────────

app.include_router(router, prefix="/api")
app.mount("/static", StaticFiles(directory="static"), name="static")

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)