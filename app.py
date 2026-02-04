from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


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


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None})


@app.post("/check", response_class=HTMLResponse)
def check(
    request: Request,
    income: float = Form(...),
    fixed: float = Form(...),
    today: float = Form(...),
    days_left: int = Form(...),
):
    budget_jour, etat, message = analyser_depense(income, fixed, today, days_left)
    result = {
        "daily_budget": round(budget_jour, 2),
        "status": etat,
        "message": message,
    }
    return templates.TemplateResponse("index.html", {"request": request, "result": result})
