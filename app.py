from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from passlib.context import CryptContext
from itsdangerous import URLSafeSerializer, BadSignature
from urllib.parse import urlencode
import statistics
import secrets
import time
import os
import logging

from db import engine, init_db, User, CheckHistory, Profile, HealthScoreHistory
from plans import PLANS

try:
    import stripe
except Exception:
    stripe = None

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
STRIPE_PRICE_ID_MONTHLY = os.getenv("STRIPE_PRICE_ID_MONTHLY", "")
STRIPE_PRICE_ID_YEARLY = os.getenv("STRIPE_PRICE_ID_YEARLY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
STRIPE_PORTAL_RETURN_URL = os.getenv("STRIPE_PORTAL_RETURN_URL", f"{APP_BASE_URL}/billing")
PRO_PAYWALL_ENABLED = os.getenv("PRO_PAYWALL_ENABLED", "false").lower() == "true"
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
cookie_signer = URLSafeSerializer("CHANGE_ME_TO_A_LONG_RANDOM_SECRET", salt="auth")
csrf_signer = URLSafeSerializer("CHANGE_ME_TO_A_LONG_RANDOM_SECRET", salt="csrf")

logging.basicConfig(level=logging.INFO)
login_attempts = {}


def _now():
    return time.time()


def is_rate_limited(ip: str, limit: int = 5, window_seconds: int = 600):
    now = _now()
    attempts = login_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < window_seconds]
    login_attempts[ip] = attempts
    return len(attempts) >= limit


def is_rate_limited_key(key: str, limit: int = 5, window_seconds: int = 600):
    now = _now()
    attempts = login_attempts.get(key, [])
    attempts = [t for t in attempts if now - t < window_seconds]
    login_attempts[key] = attempts
    return len(attempts) >= limit


def record_attempt(key: str):
    attempts = login_attempts.get(key, [])
    attempts.append(_now())
    login_attempts[key] = attempts


def record_login_failure(ip: str):
    attempts = login_attempts.get(ip, [])
    attempts.append(_now())
    login_attempts[ip] = attempts


def clear_login_failures(ip: str):
    if ip in login_attempts:
        del login_attempts[ip]


def analyser_depense(revenu: float, fixes: float, depense: float, jours: int):
    budget_rest = revenu - fixes
    budget_jour = budget_rest / jours if jours > 0 else 0

    if budget_jour <= 0:
        return budget_jour, "danger", "Funds are low — careful planning helps here."

    if depense <= budget_jour:
        return budget_jour, "ok", "You’re on track."
    elif depense <= budget_jour * 1.3:
        return budget_jour, "caution", "You still have funds — just stay mindful."
    else:
        return budget_jour, "danger", "Funds are low — careful planning helps here."


def set_auth_cookie(resp: Response, user_id: int):
    token = cookie_signer.dumps({"user_id": user_id})
    secure_cookie = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    resp.set_cookie(
        "qbc_auth",
        token,
        httponly=True,
        samesite="lax",
        secure=secure_cookie,
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


def get_or_set_csrf_token(request: Request):
    token = request.cookies.get("qbc_csrf")
    if token:
        try:
            csrf_signer.loads(token)
            return token
        except BadSignature:
            pass
    token = csrf_signer.dumps(secrets.token_urlsafe(16))
    return token


def set_csrf_cookie(resp: Response, token: str):
    secure_cookie = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    resp.set_cookie(
        "qbc_csrf",
        token,
        httponly=False,
        samesite="lax",
        secure=secure_cookie,
        max_age=60 * 60 * 6,
        path="/",
    )


def validate_csrf(request: Request, form_token: str):
    cookie_token = request.cookies.get("qbc_csrf")
    if not form_token or not cookie_token:
        return False
    if form_token != cookie_token:
        return False
    try:
        csrf_signer.loads(form_token)
    except BadSignature:
        return False
    return True


def render_template(template: str, context: dict):
    request = context.get("request")
    token = get_or_set_csrf_token(request) if request else None
    if token:
        context["csrf_token"] = token
    context["paywall_enabled"] = PRO_PAYWALL_ENABLED
    resp = templates.TemplateResponse(template, context)
    if token:
        set_csrf_cookie(resp, token)
    return resp


def get_plan_state_for_user(user_id: int | None):
    if not user_id:
        return "free"

    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if user and user.plan:
            return user.plan
    return "free"


def require_pro(user_id: int | None):
    return get_plan_state_for_user(user_id) == "pro"


def pro_guard(request: Request, user_id: int, active_page: str):
    if not PRO_PAYWALL_ENABLED:
        return None
    if require_pro(user_id):
        return None
    return templates.TemplateResponse(
        "upgrade_required.html",
        {"request": request, "active_page": active_page, "plan_state": get_plan_state_for_user(user_id)},
    )


def demo_history():
    return [
        CheckHistory(
            user_id=0,
            net_income=3200,
            fixed_expenses=1900,
            today_expense=85,
            days_left=12,
            daily_budget=108.3,
            status="ok",
            message="On track.",
        ),
        CheckHistory(
            user_id=0,
            net_income=3200,
            fixed_expenses=1900,
            today_expense=140,
            days_left=10,
            daily_budget=108.3,
            status="caution",
            message="Slightly above pace.",
        ),
        CheckHistory(
            user_id=0,
            net_income=3200,
            fixed_expenses=1900,
            today_expense=165,
            days_left=9,
            daily_budget=108.3,
            status="danger",
            message="Drift detected.",
        ),
    ]


def get_recent_history(user_id: int, limit: int = 15):
    with Session(engine) as session:
        history = session.exec(
            select(CheckHistory)
            .where(CheckHistory.user_id == user_id)
            .order_by(CheckHistory.created_at.desc())
            .limit(limit)
        ).all()
    if DEMO_MODE and not history:
        return demo_history()
    return history


def compute_health_score(history: list[CheckHistory]):
    if not history:
        return 62, {"trend": 0, "breakdown": {}, "risk": "moderate"}

    drifts = []
    cushions = []
    budgets = []
    fixed_ratios = []
    runway_ratios = []
    ok = 0
    caution = 0
    danger = 0

    for h in history:
        budgets.append(float(h.daily_budget or 0))
        if h.status == "ok":
            ok += 1
        elif h.status == "caution":
            caution += 1
        else:
            danger += 1

        income = float(h.net_income or 0)
        fixed = float(h.fixed_expenses or 0)
        if income > 0:
            cushions.append(max(0.0, min(1.0, (income - fixed) / income)))
            fixed_ratios.append(max(0.0, min(1.0, fixed / income)))

        if h.daily_budget and h.today_expense is not None:
            if h.daily_budget > 0:
                drifts.append((float(h.today_expense) - float(h.daily_budget)) / float(h.daily_budget))
            if income - fixed > 0 and h.days_left > 0:
                runway = (float(h.daily_budget) * float(h.days_left)) / max(1.0, (income - fixed))
                runway_ratios.append(max(0.0, min(1.0, runway)))

    total = max(1, ok + caution + danger)
    stability = ok / total
    shock = (ok + caution) / total
    avg_drift = sum(abs(d) for d in drifts) / max(1, len(drifts))
    acceleration = max(0.0, 1.0 - min(1.0, avg_drift))
    cushion = sum(cushions) / max(1, len(cushions))
    fixed_ratio = sum(fixed_ratios) / max(1, len(fixed_ratios)) if fixed_ratios else 0.0
    runway_ratio = sum(runway_ratios) / max(1, len(runway_ratios)) if runway_ratios else cushion

    if len(budgets) > 2 and statistics.mean(budgets) > 0:
        cv = statistics.pstdev(budgets) / statistics.mean(budgets)
        consistency = max(0.0, 1.0 - min(1.0, cv))
    else:
        consistency = stability

    goal_alignment = (ok + (caution * 0.5)) / total

    affordability = max(0.0, 1.0 - fixed_ratio)
    buffer = max(0.0, min(1.0, (cushion + runway_ratio) / 2))
    weights = {
        "stability": 0.2,
        "acceleration": 0.18,
        "buffer": 0.18,
        "affordability": 0.14,
        "goal_alignment": 0.12,
        "consistency": 0.1,
        "shock": 0.08,
    }

    score = (
        stability * weights["stability"]
        + acceleration * weights["acceleration"]
        + buffer * weights["buffer"]
        + affordability * weights["affordability"]
        + goal_alignment * weights["goal_alignment"]
        + consistency * weights["consistency"]
        + shock * weights["shock"]
    ) * 100

    score = max(0, min(100, int(round(score))))

    recent = history[:5]
    previous = history[5:10]
    recent_score = score
    if previous:
        prev_score, _ = compute_health_score(previous)
        trend = recent_score - prev_score
    else:
        trend = 0

    breakdown = {
        "stability": int(round(stability * 100)),
        "acceleration": int(round(acceleration * 100)),
        "cushion": int(round(cushion * 100)),
        "buffer": int(round(buffer * 100)),
        "affordability": int(round(affordability * 100)),
        "runway": int(round(runway_ratio * 100)),
        "goal_alignment": int(round(goal_alignment * 100)),
        "consistency": int(round(consistency * 100)),
        "shock": int(round(shock * 100)),
    }

    if score >= 75:
        risk = "low"
    elif score >= 55:
        risk = "moderate"
    else:
        risk = "high"

    return score, {"trend": trend, "breakdown": breakdown, "risk": risk}


def health_label(score: int):
    if score >= 75:
        return "Steady"
    if score >= 55:
        return "Building"
    return "Alert"


def health_reason(history: list[CheckHistory], breakdown: dict):
    reasons = []
    if breakdown.get("cushion", 0) < 40:
        reasons.append("Low cushion ratio")
    if breakdown.get("affordability", 0) < 45:
        reasons.append("Fixed expenses are heavy")
    if breakdown.get("runway", 0) < 45:
        reasons.append("Short runway vs days left")
    if breakdown.get("acceleration", 0) < 45:
        reasons.append("High drift acceleration")
    if breakdown.get("consistency", 0) < 50:
        reasons.append("Irregular budget pattern")
    if not reasons:
        reasons.append("Stable rhythm and pace")
    return "; ".join(reasons[:2])


def companion_insights(health_meta: dict):
    tips = []
    b = health_meta.get("breakdown", {})
    if b.get("cushion", 0) < 40:
        tips.append("Increase your cash buffer by setting a small weekly transfer.")
    if b.get("acceleration", 0) < 45:
        tips.append("Today’s spend is drifting above pace—try a soft cap for 48 hours.")
    if b.get("consistency", 0) < 50:
        tips.append("Your rhythm varies a lot—consider a simpler weekly plan.")
    if not tips:
        tips.append("Your rhythm looks steady. Keep the same pace this week.")
    return tips[:3]


def top_drivers(breakdown: dict):
    metrics = {
        "Stability": breakdown.get("stability", 0),
        "Drift control": breakdown.get("acceleration", 0),
        "Cushion": breakdown.get("cushion", 0),
        "Runway": breakdown.get("runway", 0),
        "Fixed ratio": 100 - breakdown.get("affordability", 0),
        "Consistency": breakdown.get("consistency", 0),
        "Shock": breakdown.get("shock", 0),
    }
    ranked = sorted(metrics.items(), key=lambda x: x[1])
    drivers = []
    for name, score in ranked[:3]:
        if name == "Fixed ratio":
            drivers.append((name, f"{score}% of income fixed"))
        else:
            drivers.append((name, f"{score}%"))
    return drivers


def next_steps(breakdown: dict):
    steps = []
    if breakdown.get("cushion", 0) < 45:
        steps.append("Add a small buffer transfer this week.")
    if breakdown.get("acceleration", 0) < 50:
        steps.append("Set a 48‑hour soft cap to reduce drift.")
    if breakdown.get("consistency", 0) < 55:
        steps.append("Pick a single weekly pace and stick to it.")
    if breakdown.get("affordability", 0) < 45:
        steps.append("Review fixed costs for a quick trim.")
    if not steps:
        steps.append("Keep your current pace — it’s working.")
    return steps[:3]


def normalize_tone(tone: str | None):
    tone = (tone or "calm").strip().lower()
    if tone not in {"calm", "direct", "playful", "coach"}:
        tone = "calm"
    return tone


def companion_engine(tone: str, health_meta: dict):
    tips = companion_insights(health_meta)
    tone = normalize_tone(tone)
    prefix = {
        "calm": "Calm check‑in:",
        "direct": "Direct read:",
        "playful": "Quick vibe:",
        "coach": "Coach mode:",
    }[tone]
    message = f"{prefix} {tips[0]}"
    actions = ["Apply suggestion", "Create a plan", "Show risk drivers"]
    return {"message": message, "tips": tips[1:], "actions": actions}


def compute_streaks(history: list[CheckHistory]):
    stable = 0
    adjust = 0
    goal = 0
    for h in history:
        if h.status == "ok":
            stable += 1
        else:
            break
    for h in history:
        if h.status in ("ok", "caution"):
            adjust += 1
        else:
            break
    for h in history:
        if h.status == "ok":
            goal += 1
        else:
            break
    return {"stable": stable, "adjust": adjust, "goal": goal}


def compute_projection(history: list[CheckHistory]):
    if not history:
        return {"points": [62, 60, 58, 57, 59, 61], "buffer": "stable"}
    recent = history[:10]
    avg_budget = sum(float(h.daily_budget or 0) for h in recent) / max(1, len(recent))
    avg_spend = sum(float(h.today_expense or 0) for h in recent) / max(1, len(recent))
    drift = 0.0
    if avg_budget > 0:
        drift = (avg_spend - avg_budget) / avg_budget
    base = max(35, min(90, int(round(70 - drift * 30))))
    points = [max(30, min(95, base + delta)) for delta in (0, -4, -7, -3, 2, -1)]
    buffer = "stable" if drift <= 0.05 else "tight"
    return {"points": points, "buffer": buffer}


@app.on_event("startup")
def on_startup():
    init_db()


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return resp


@app.exception_handler(404)
def not_found(request: Request, exc):
    return render_template("404.html", {"request": request})


@app.exception_handler(500)
def server_error(request: Request, exc):
    return render_template("500.html", {"request": request})


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user_id = get_user_id_from_request(request)
    status = request.query_params.get("status")
    message = request.query_params.get("message")
    daily = request.query_params.get("daily")

    result = None
    if status and message and daily:
        result = {"status": status, "message": message, "daily_budget": daily}

    return render_template("index.html", {"request": request, "result": result, "user_id": user_id, "plans": PLANS})


@app.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request):
    return render_template("pricing.html", {"request": request, "user_id": get_user_id_from_request(request), "plans": PLANS})


@app.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    return render_template("privacy.html", {"request": request, "user_id": get_user_id_from_request(request)})


@app.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    return render_template("terms.html", {"request": request, "user_id": get_user_id_from_request(request)})


@app.post("/check", response_class=HTMLResponse)
def check(
    request: Request,
    csrf_token: str = Form(""),
    period: str = Form("monthly"),
    income: float = Form(...),
    fixed: float = Form(...),
    today: float = Form(...),
    days_left: int = Form(...),
):
    if not validate_csrf(request, csrf_token):
        return render_template(
            "index.html",
            {"request": request, "result": None, "user_id": get_user_id_from_request(request), "error": "Session expired. Please try again."},
        )
    if income <= 0 or fixed < 0 or today < 0 or days_left <= 0:
        return render_template(
            "index.html",
            {"request": request, "result": None, "user_id": get_user_id_from_request(request), "error": "Please check your inputs."},
        )
    if income > 1_000_000 or fixed > 1_000_000 or today > 1_000_000 or days_left > 365:
        return render_template(
            "index.html",
            {"request": request, "result": None, "user_id": get_user_id_from_request(request), "error": "Inputs look out of range."},
        )
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

            recent = session.exec(
                select(CheckHistory)
                .where(CheckHistory.user_id == user_id)
                .order_by(CheckHistory.created_at.desc())
                .limit(20)
            ).all()
            score, meta = compute_health_score(recent)
            label = health_label(score)
            reason = health_reason(recent, meta["breakdown"])
            session.add(HealthScoreHistory(
                user_id=user_id,
                score=score,
                label=label,
                reason=reason,
            ))
            session.commit()

    params = urlencode(
        {
            "daily": f"{budget_jour:.1f}",
            "status": etat,
            "message": message,
        }
    )
    return RedirectResponse(url=f"/?{params}", status_code=303)


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return render_template("register.html", {"request": request, "error": None})


@app.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    csrf_token: str = Form(""),
    email: str = Form(...),
    password: str = Form(...),
):
    if not validate_csrf(request, csrf_token):
        return render_template("register.html", {"request": request, "error": "Session expired. Please try again."})
    ip = request.client.host if request.client else "unknown"
    if is_rate_limited_key(f"register:{ip}", limit=6, window_seconds=600):
        return render_template("register.html", {"request": request, "error": "Too many attempts. Try again later."})
    email = email.strip().lower()
    if len(password) > 72 or len(password) < 8:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Password must be 8–72 characters."},
        )
    if len(email) > 120:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Email is too long."},
        )
    pw_hash = pwd_context.hash(password)

    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing:
            record_attempt(f"register:{ip}")
            return templates.TemplateResponse("register.html", {"request": request, "error": "Email already used."})

        user = User(email=email, password_hash=pw_hash)
        session.add(user)
        session.commit()
        session.refresh(user)

    resp = RedirectResponse(url="/dashboard", status_code=303)
    set_auth_cookie(resp, user.id)
    record_attempt(f"register:{ip}")
    return resp


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return render_template("login.html", {"request": request, "error": None})

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return RedirectResponse(url="/register", status_code=303)


@app.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    csrf_token: str = Form(""),
    email: str = Form(...),
    password: str = Form(...),
):
    if not validate_csrf(request, csrf_token):
        return render_template("login.html", {"request": request, "error": "Session expired. Please try again."})
    ip = request.client.host if request.client else "unknown"
    if is_rate_limited(ip):
        return render_template("login.html", {"request": request, "error": "Too many attempts. Try again later."})
    email = email.strip().lower()
    if len(password) > 72:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials."})

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user or not pwd_context.verify(password, user.password_hash):
            record_login_failure(ip)
            return render_template("login.html", {"request": request, "error": "Invalid credentials."})

    resp = RedirectResponse(url="/dashboard", status_code=303)
    set_auth_cookie(resp, user.id)
    clear_login_failures(ip)
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

    try:
        history = get_recent_history(user_id, limit=5)
        with Session(engine) as session:
            profile = session.exec(select(Profile).where(Profile.user_id == user_id)).first()
            last_score = session.exec(
                select(HealthScoreHistory)
                .where(HealthScoreHistory.user_id == user_id)
                .order_by(HealthScoreHistory.created_at.desc())
                .limit(1)
            ).first()
    except Exception:
        logging.exception("Dashboard load failed")
        history = []
        profile = None
        last_score = None

    ok_count = sum(1 for h in history if h.status == "ok")
    caution_count = sum(1 for h in history if h.status == "caution")
    danger_count = sum(1 for h in history if h.status == "danger")
    total_count = ok_count + caution_count + danger_count
    progress_value = int(round((ok_count / total_count) * 100)) if total_count else 0
    if danger_count > 0:
        pace_status = "danger"
    elif caution_count > 0:
        pace_status = "caution"
    else:
        pace_status = "ok"

    plan_state = get_plan_state_for_user(user_id)
    health_score, health_meta = compute_health_score(history)
    health_label_text = health_label(health_score)
    health_reason_text = last_score.reason if last_score else health_reason(history, health_meta["breakdown"])
    drivers = top_drivers(health_meta["breakdown"])
    steps = next_steps(health_meta["breakdown"])
    tone = normalize_tone(profile.companion_tone if profile else "calm")
    companion = companion_engine(tone, health_meta)
    health_score_display = last_score.score if last_score else health_score
    streaks = compute_streaks(history)
    projection = compute_projection(history)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "history": history,
            "stats": {"ok": ok_count, "caution": caution_count, "danger": danger_count},
            "first_name": (profile.first_name.strip() if profile and profile.first_name else "there"),
            "progress_value": progress_value,
            "pace_status": pace_status,
            "active_page": "dashboard",
            "plan_state": plan_state,
            "health_score": health_score_display,
            "health_trend": health_meta["trend"],
            "health_breakdown": health_meta["breakdown"],
            "health_risk": health_meta["risk"],
            "health_label": health_label_text,
            "health_reason": health_reason_text,
            "health_drivers": drivers,
            "health_steps": steps,
            "companion": companion,
            "companion_tone": tone,
            "streaks": streaks,
            "projection": projection,
        },
    )

@app.get("/check", response_class=HTMLResponse)
def check_page(request: Request):
    return RedirectResponse(url="/run-check", status_code=303)


@app.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request):
    return RedirectResponse(url="/account", status_code=303)


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return RedirectResponse(url="/account#preferences", status_code=303)


@app.post("/profile", response_class=HTMLResponse)
def profile_update(
    request: Request,
    csrf_token: str = Form(""),
    first_name: str = Form(""),
    last_name: str = Form(""),
    address: str = Form(""),
    city: str = Form(""),
    country: str = Form(""),
    phone: str = Form(""),
):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    if not validate_csrf(request, csrf_token):
        with Session(engine) as session:
            profile = session.exec(select(Profile).where(Profile.user_id == user_id)).first()
            if not profile:
                profile = Profile(user_id=user_id)
                session.add(profile)
                session.commit()
                session.refresh(profile)
        return render_template(
            "account.html",
            {"request": request, "profile": profile, "active_page": "account", "plan_state": get_plan_state_for_user(user_id), "error": "Session expired. Please try again."},
        )

    with Session(engine) as session:
        profile = session.exec(select(Profile).where(Profile.user_id == user_id)).first()
        if not profile:
            profile = Profile(user_id=user_id)
            session.add(profile)

        profile.first_name = first_name.strip()
        profile.last_name = last_name.strip()
        profile.address = address.strip()
        profile.city = city.strip()
        profile.country = country.strip()
        profile.phone = phone.strip()
        session.commit()

    return RedirectResponse(url="/account", status_code=303)


@app.post("/preferences", response_class=HTMLResponse)
def preferences_update(
    request: Request,
    csrf_token: str = Form(""),
    companion_tone: str = Form("calm"),
):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    if not validate_csrf(request, csrf_token):
        return RedirectResponse(url="/account#preferences", status_code=303)
    tone = normalize_tone(companion_tone)
    with Session(engine) as session:
        profile = session.exec(select(Profile).where(Profile.user_id == user_id)).first()
        if not profile:
            profile = Profile(user_id=user_id)
            session.add(profile)
        profile.companion_tone = tone
        session.commit()
    return RedirectResponse(url=f"/account#preferences", status_code=303)


@app.get("/run-check", response_class=HTMLResponse)
def run_check_page(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    gate = pro_guard(request, user_id, "run-check")
    if gate:
        return gate
    plan_state = get_plan_state_for_user(user_id)
    return templates.TemplateResponse(
        "run_check.html",
        {"request": request, "active_page": "run-check", "plan_state": plan_state},
    )


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    history = get_recent_history(user_id, limit=50)

    plan_state = get_plan_state_for_user(user_id)
    return templates.TemplateResponse(
        "history.html",
        {"request": request, "history": history, "active_page": "history", "plan_state": plan_state},
    )


@app.get("/goals", response_class=HTMLResponse)
def goals_page(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    gate = pro_guard(request, user_id, "goals")
    if gate:
        return gate
    plan_state = get_plan_state_for_user(user_id)
    return templates.TemplateResponse(
        "goals.html",
        {"request": request, "active_page": "goals", "plan_state": plan_state},
    )


@app.get("/wallet", response_class=HTMLResponse)
def wallet_page(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    gate = pro_guard(request, user_id, "wallet")
    if gate:
        return gate
    plan_state = get_plan_state_for_user(user_id)
    return templates.TemplateResponse(
        "wallet.html",
        {"request": request, "active_page": "wallet", "plan_state": plan_state},
    )


@app.get("/account", response_class=HTMLResponse)
def account_page(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    with Session(engine) as session:
        profile = session.exec(select(Profile).where(Profile.user_id == user_id)).first()
        if not profile:
            profile = Profile(user_id=user_id)
            session.add(profile)
            session.commit()
            session.refresh(profile)

    plan_state = get_plan_state_for_user(user_id)
    return render_template(
        "account.html",
        {"request": request, "profile": profile, "active_page": "account", "plan_state": plan_state},
    )


@app.get("/billing", response_class=HTMLResponse)
def billing_page(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    plan_state = get_plan_state_for_user(user_id)
    return templates.TemplateResponse(
        "billing.html",
        {"request": request, "active_page": "billing", "plan_state": plan_state},
    )


@app.get("/upgrade", response_class=HTMLResponse)
def upgrade_page(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)

    plan_state = get_plan_state_for_user(user_id)
    email = ""
    if user_id:
        with Session(engine) as session:
            user = session.exec(select(User).where(User.id == user_id)).first()
            if user:
                email = user.email

    return render_template(
        "upgrade.html",
        {
            "request": request,
            "active_page": "upgrade",
            "plan_state": plan_state,
            "email": email,
            "plans": PLANS,
        },
    )


@app.post("/checkout", response_class=HTMLResponse)
def checkout(request: Request, csrf_token: str = Form(""), plan_interval: str = Form("monthly")):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    ip = request.client.host if request.client else "unknown"
    if is_rate_limited_key(f"checkout:{ip}", limit=6, window_seconds=600):
        return render_template("upgrade.html", {"request": request, "active_page": "upgrade", "plan_state": "free", "error": "Too many attempts. Try again later."})
    if not validate_csrf(request, csrf_token):
        return render_template("upgrade.html", {"request": request, "active_page": "upgrade", "plan_state": "free", "error": "Session expired. Please try again."})
    if not stripe or not STRIPE_SECRET_KEY or not (STRIPE_PRICE_ID or STRIPE_PRICE_ID_MONTHLY or STRIPE_PRICE_ID_YEARLY):
        return render_template("upgrade.html", {"request": request, "active_page": "upgrade", "plan_state": "free", "error": "Stripe is not configured."})
    interval = plan_interval if plan_interval in ("monthly", "yearly") else "monthly"
    price_id = STRIPE_PRICE_ID
    if interval == "monthly" and STRIPE_PRICE_ID_MONTHLY:
        price_id = STRIPE_PRICE_ID_MONTHLY
    if interval == "yearly" and STRIPE_PRICE_ID_YEARLY:
        price_id = STRIPE_PRICE_ID_YEARLY
    if not price_id:
        return render_template("upgrade.html", {"request": request, "active_page": "upgrade", "plan_state": "free", "error": "Stripe price ID missing."})

    stripe.api_key = STRIPE_SECRET_KEY
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            return RedirectResponse(url="/login", status_code=303)
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(email=user.email)
            customer_id = customer["id"]
            user.stripe_customer_id = customer_id
            session.add(user)
            session.commit()

    checkout_session = stripe.checkout.Session.create(
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{APP_BASE_URL}/billing?success=1",
        cancel_url=f"{APP_BASE_URL}/upgrade?canceled=1",
    )
    logging.info("Stripe checkout session created for user %s", user_id)
    return RedirectResponse(url=checkout_session.url, status_code=303)


@app.get("/checkout", response_class=HTMLResponse)
def checkout_page(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    return render_template("checkout.html", {"request": request, "active_page": "upgrade", "plan_state": get_plan_state_for_user(user_id)})


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    if not stripe or not STRIPE_WEBHOOK_SECRET:
        return Response(status_code=400)
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception:
        return Response(status_code=400)

    data = event["data"]["object"]
    event_type = event["type"]

    if event_type in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        customer_id = data.get("customer")
        status = data.get("status")
        subscription_id = data.get("id")
        plan_state = "pro" if status in ("active", "trialing") else "free"
        with Session(engine) as session:
            user = session.exec(select(User).where(User.stripe_customer_id == customer_id)).first()
            if user:
                user.plan = plan_state
                user.stripe_subscription_id = subscription_id
                user.stripe_status = status
                session.add(user)
                session.commit()
                logging.info("Stripe subscription update user %s status %s", user.id, status)
    return Response(status_code=200)


@app.get("/billing/portal")
def billing_portal(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/login", status_code=303)
    if not stripe or not STRIPE_SECRET_KEY:
        return RedirectResponse(url="/billing", status_code=303)
    stripe.api_key = STRIPE_SECRET_KEY
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user or not user.stripe_customer_id:
            return RedirectResponse(url="/billing", status_code=303)
        portal = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=STRIPE_PORTAL_RETURN_URL,
        )
    return RedirectResponse(url=portal.url, status_code=303)
