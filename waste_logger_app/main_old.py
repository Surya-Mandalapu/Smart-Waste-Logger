import os
import io
from PIL import Image
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from passlib.hash import bcrypt
from pydantic import BaseModel
import shutil
import sqlite3
import uuid
import model_loader, carbon_utils
from database import get_db
from sqlalchemy.orm import Session
import traceback
from fastapi.responses import HTMLResponse
from carbon_utils import get_item_data
# from waste_log import read_log, log_item 
# from carbon_utils import estimate_impact, load_carbon_table
# from model_loader import classify_image

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(UPLOAD_DIR, exist_ok=True)

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.post("/classify")
async def classify_image(file: UploadFile = File(...), request: Request = None, db: Session = Depends(get_db)):
    try:
        if file.content_type.split("/")[0] != "image":
            return templates.TemplateResponse("result.html", {
                "request": request,
                "filename": file.filename,
                "label": "Not an image",
                "recyclable": False,
                "co2_kg": None,
                "error": "Please upload a valid image file."
            })

        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

        label = classify_image(image)
        item_data = get_item_data(label)

        recyclable = item_data["recyclable"]
        co2_kg = item_data["co2_kg"]

        # Log to DB if user is logged in
        username = request.session.get("username")
        if username:
            waste_log = WasteLog(
                username=username,
                filename=file.filename,
                label=label,
                recyclable=recyclable,
                co2_kg=co2_kg
            )
            db.add(waste_log)
            db.commit()

        return templates.TemplateResponse("result.html", {
            "request": request,
            "filename": file.filename,
            "label": label,
            "recyclable": recyclable,
            "co2_kg": co2_kg
        })
    except Exception as e:
        error_message = traceback.format_exc()
        print("ERROR IN /classify:", error_message)
        return HTMLResponse(f"<h2>Internal Server Error</h2><pre>{error_message}</pre>", status_code=500)


app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")

DB_PATH = os.path.join(BASE_DIR, "waste_log.db")
carbon_data = carbon_utils.load_carbon_table()

# ----------------------- Database Setup -----------------------
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE,
                            password TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS waste_logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT,
                            label TEXT,
                            material TEXT,
                            recyclable TEXT,
                            co2_kg REAL,
                            image_path TEXT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
init_db()

# ----------------------- Routes -----------------------
@app.get("/")
async def home(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register")
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...)):
    hashed_password = bcrypt.hash(password)
    with sqlite3.connect(DB_PATH) as conn:
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            return RedirectResponse(url="/login", status_code=302)
        except sqlite3.IntegrityError:
            return templates.TemplateResponse("register.html", {"request": request, "error": "Username already exists."})

@app.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username=?", (username,))
        result = cursor.fetchone()
        if result and bcrypt.verify(password, result[0]):
            request.session["user"] = username
            return RedirectResponse(url="/", status_code=302)
        else:
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials."})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

@app.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)

    contents = await file.read()
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    label = model_loader.classify_image(file_path)
    co2_info = carbon_utils.get_carbon_info(label, carbon_data)
    user = request.session["user"]

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''INSERT INTO waste_logs (username, label, material, recyclable, co2_kg, image_path)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (user, label, co2_info["material"], co2_info["recyclable"], co2_info["co2_kg"], filename))
        conn.commit()

    return templates.TemplateResponse("result.html", {
        "request": request,
        "label": label,
        "material": co2_info["material"],
        "recyclable": co2_info["recyclable"],
        "co2_kg": co2_info["co2_kg"],
        "image_url": f"/static/{filename}"
    })

@app.get("/waste_log")
async def waste_log(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT label, material, recyclable, co2_kg, image_path, timestamp FROM waste_logs WHERE username=? ORDER BY timestamp DESC", (request.session["user"],))
        logs = cursor.fetchall()

    total_co2 = sum(row[3] for row in logs)
    return templates.TemplateResponse("waste_log.html", {
        "request": request,
        "logs": logs,
        "total_co2": total_co2
    })