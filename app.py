from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from passlib.context import CryptContext
from itsdangerous import URLSafeSerializer, BadSignature

from db import engine, init_db, User, CheckHistory

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
cookie_signer = URLSafeSerializer("CHANGE_ME_TO_A_LONG_RANDOM_SECRET", salt="auth")


def analyser_depense(revenu: float, fixes: float, depense: float, jours: int):
    budget_rest = revenu - fixes
    budget_jour = budget_rest / jours if jours > 0 else 0

    if budget_jour <= 0:
        return budget_jour, "danger", "Your available budget is too low or the remaining days are invalid."

    if depense <= budget_jour:
        return budget_jour, "ok", "This expense fits your normal pace."
    elif depense <= budget_jour * 1.3:
        return budget_jour, "caution", "Careful — this tightens the rest of your month."
    else:
        return budget_jour, "danger", "This puts serious pressure on your month."


def set_auth_cookie(resp: Response, user_id: int):
    token = cookie_signer.dumps({"user_id": user_id})
    resp.set_cookie(
        "qbc_auth",
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30,
        path="/",
    )


def get_user_id_from_request(request: Request):
    token = request.cookies.get("qbc_auth")
    if not token:
        return None
    try:
        data = cookie_signer.loads(token)
        return int(data.get("user_id"))
    except (BadSignature, ValueError, TypeError):
        return None


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user_id = get_user_id_from_request(request)
    return templates.TemplateResponse("index.html", {"request": request, "result": None, "user_id": user_id})


@app.post("/check", response_class=HTMLResponse)
def check(
    request: Request,
    period: str = Form("monthly"),
    income: float = Form(...),
    fixed: float = Form(...),
    today: float = Form(...),
    days_left: int = Form(...),
):
    budget_jour, etat, message = analyser_depense(income, fixed, today, days_left)

    user_id = get_user_id_from_request(request)
    if user_id:
        with Session(engine) as session:
            session.add(CheckHistory(
                user_id=user_id,
                net_income=income,
                fixed_expenses=fixed,
                today_expense=today,
                days_left=days_left,
                daily_budget=float(budget_jour),
                status=etat,
                message=message,
            ))
            session.commit()

    result = {
        "daily_budget": round(budget_jour, 2),
        "status": etat,
        "message": message,
    }
    return templates.TemplateResponse("index.html", {"request": request, "result": result, "user_id": user_id})


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@app.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    email = email.strip().lower()
    if len(password) > 72:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Password is too long (max 72 characters)."},
        )
    pw_hash = pwd_context.hash(password)

    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing:
            return templates.TemplateResponse("register.html", {"request": request, "error": "Email already used."})

        user = User(email=email, password_hash=pw_hash)
        session.add(user)
        session.commit()
        session.refresh(user)

    resp = RedirectResponse(url="/dashboard", status_code=303)
    set_auth_cookie(resp, user.id)
    return resp


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    email = email.strip().lower()
    if len(password) > 72:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials."})

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user or not pwd_context.verify(password, user.password_hash):
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials."})

    resp = RedirectResponse(url="/dashboard", status_code=303)
    set_auth_cookie(resp, user.id)
    return resp


@app.get("/logout")
def logout():
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie("qbc_auth", path="/")
    return resp


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    with Session(engine) as session:
        history = session.exec(
            select(CheckHistory)
            .where(CheckHistory.user_id == user_id)
            .order_by(CheckHistory.created_at.desc())
            .limit(15)
        ).all()

    ok_count = sum(1 for h in history if h.status == "ok")
    caution_count = sum(1 for h in history if h.status == "caution")
    danger_count = sum(1 for h in history if h.status == "danger")

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "history": history,
            "stats": {"ok": ok_count, "caution": caution_count, "danger": danger_count},
        },
    )
