from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from services import file_manager as fm
from routes.api import router
import os

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve uploaded files so frontend can fetch them for conversion
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)


# Updated by Azure Pipeline practice - Kishoth