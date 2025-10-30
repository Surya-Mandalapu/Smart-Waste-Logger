import os
import io
import uuid
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends,HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from passlib.hash import bcrypt
from pydantic import BaseModel
from sqlalchemy.orm import Session
from PIL import Image
from datetime import datetime
from waste_logger_app.utils.dependencies import require_login
from waste_logger_app import model_loader, carbon_utils
from waste_logger_app.database import get_db, WasteLog, Base, engine, SessionLocal
from waste_logger_app.routes import auth
from waste_logger_app.models import user  
from fastapi.exception_handlers import http_exception_handler
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")
app.include_router(auth.router)


# BASE_DIR = os.path.dirname(__file__)
# UPLOAD_DIR = os.path.join(BASE_DIR, "static")
# os.makedirs(UPLOAD_DIR, exist_ok=True)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

carbon_df = carbon_utils.load_carbon_table()


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/login", status_code=303)
    return await http_exception_handler(request, exc)

@app.get("/")
def index(request: Request, user_id: int = Depends(require_login), db: Session = Depends(get_db)):
    username = None
    if user_id:
        db_user = db.query(user.User).filter(user.User.id == user_id).first()
        if db_user:
            username = db_user.username

    # Get dashboard data
    logs = db.query(WasteLog).filter(WasteLog.username == username).order_by(WasteLog.timestamp).all()
    total_co2 = sum(entry.co2_estimate for entry in logs if entry.co2_estimate)
    total_entries = len(logs)
    recyclable_count = sum(1 for entry in logs if entry.recyclable)
    percent_recyclable = (recyclable_count / total_entries * 100) if total_entries else 0

    # Chart data
    co2_trend = {}
    for log in logs:
        date_key = log.timestamp.strftime("%Y-%m-%d")
        co2_trend[date_key] = co2_trend.get(date_key, 0) + log.co2_estimate

    return templates.TemplateResponse("index.html", {
        "request": request,
        "username": username,
        "message": None,
        "error": None,
        "total_co2": round(total_co2, 2),
        "percent_recyclable": round(percent_recyclable, 2),
        "recent_logs": logs[-5:],
        "co2_trend": co2_trend,
    })

# @app.get("/")
# def index(request: Request, user_id: int = Depends(require_login), db: Session = Depends(get_db)):
#     username = None
#     if user_id:
#         db_user = db.query(user.User).filter(user.User.id == user_id).first()
#         if db_user:
#             username = db_user.username
#     message = None
#     error = None

#     return templates.TemplateResponse("index.html", {
#         "request": request,
#         "username": username,
#         "message": message,
#         "error": error,
#     })



@app.post("/classify")
async def classify_image(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db),user_id: int = Depends(require_login)):
    contents = await file.read()
    # image = Image.open(io.BytesIO(contents)).convert("RGB")
    # image_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.jpg")
    # image.save(image_path)
    image = Image.open(io.BytesIO(contents)).convert("RGB")

        

    # Save image to static folder (optional, for display)
    image_filename = f"upload_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.png"
    image_path = os.path.join(STATIC_DIR, image_filename)
    image.save(image_path)

    label, confidence = model_loader.classify_image(contents)
    material, recyclable, co2 = carbon_utils.estimate_impact(label, carbon_df)

    # Save to database
    username = request.session.get("username", "guest")
    # new_entry = WasteLog(label=label, confidence=confidence, material=material, recyclable=recyclable, co2_estimate=co2)
    new_entry = WasteLog(
    label=label,
    confidence=confidence,
    material=material,
    recyclable=recyclable,
    co2_estimate=co2,
    username=username,
    filename=image_filename,

    )
    db.add(new_entry)
    db.commit()

    return templates.TemplateResponse("result.html", {
        "request": request,
        "image_path": f"/static/{os.path.basename(image_path)}",
        "label": label,
        "confidence": f"{confidence:.2%}",
        "material": material,
        "recyclable": recyclable,
        "co2": co2
    })

# @app.get("/log")
# def view_log(request: Request, db: Session = Depends(get_db)):
#     logs = db.query(WasteLog).all()
#     return templates.TemplateResponse("waste_log.html", {"request": request, "logs": logs})
@app.get("/log")
def view_log(request: Request, db: Session = Depends(get_db),user_id: int = Depends(require_login)):
    username = request.session.get("username")
    # logs = db.query(WasteLog).all()
    logs = db.query(WasteLog).filter(WasteLog.username == username).all()
    total_co2 = sum(entry.co2_estimate for entry in logs if entry.co2_estimate)
    total_entries = len(logs)
    recyclable_count = sum(1 for entry in logs if entry.recyclable)
    percent_recyclable = (recyclable_count / total_entries * 100) if total_entries else 0
    return templates.TemplateResponse("waste_log.html", {
        "request": request,
        "logs": logs,
        "total_co2": round(total_co2, 2),
        "percent_recyclable": round(percent_recyclable, 2)
    })

# @app.get("/dashboard")
# def dashboard(request: Request, db: Session = Depends(get_db), user_id: int = Depends(require_login)):
#     username = request.session.get("username")

#     logs = db.query(WasteLog).filter(WasteLog.username == username).order_by(WasteLog.timestamp).all()

#     total_co2 = sum(entry.co2_estimate for entry in logs if entry.co2_estimate)
#     total_entries = len(logs)
#     recyclable_count = sum(1 for entry in logs if entry.recyclable)
#     percent_recyclable = (recyclable_count / total_entries * 100) if total_entries else 0

#     # Prepare CO₂ over time data for chart
#     co2_trend = {}
#     for log in logs:
#         date_key = log.timestamp.strftime("%Y-%m-%d")
#         co2_trend[date_key] = co2_trend.get(date_key, 0) + log.co2_estimate

#     return templates.TemplateResponse("dashboard.html", {
#         "request": request,
#         "total_co2": round(total_co2, 2),
#         "percent_recyclable": round(percent_recyclable, 2),
#         "recent_logs": logs[-5:],
#         "co2_trend": co2_trend,
#     })

@app.get("/public")
def public_dashboard(request: Request, db: Session = Depends(get_db)):
    # Get all users
    users = db.query(user.User).all()

    leaderboard = []

    for u in users:
        logs = db.query(WasteLog).filter(WasteLog.username == u.username).all()
        total_entries = len(logs)
        total_co2 = sum(log.co2_estimate for log in logs if log.co2_estimate)
        recyclable_count = sum(1 for log in logs if log.recyclable)
        recyclable_percent = (recyclable_count / total_entries * 100) if total_entries else 0

        leaderboard.append({
            "username": u.username,
            "total_co2": round(total_co2, 2),
            "recyclable_percent": round(recyclable_percent, 2),
            "total_entries": total_entries
        })
    leaderboard.sort(key=lambda x: (x['total_co2'], -x['recyclable_percent']))

    return templates.TemplateResponse("public_dashboard.html", {
        "request": request,
        "leaderboard": leaderboard
    })
