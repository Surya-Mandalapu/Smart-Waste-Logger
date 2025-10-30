from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from waste_logger_app.database import get_db
from waste_logger_app.models.user import User
from waste_logger_app.utils.auth import hash_password, verify_password

templates = Jinja2Templates(directory="waste_logger_app/templates")
router = APIRouter()

@router.get("/register")
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
def register_user(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    existing_user = db.query(User).filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Username or email already registered"
        })
    new_user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password)
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse("/login", status_code=303)

@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
def login_user(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...)
):
    user = db.query(User).filter((User.username == username) | (User.email == username)).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid username/email or password"
        })

    request.session["user_id"] = user.id
    request.session["username"] = user.username

    return RedirectResponse("/", status_code=303)

@router.get("/logout")
def logout_user(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)

