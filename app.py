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
        return budget_jour, "alerte", "Ton budget disponible est trop bas ou les jours restants sont invalides."

    if depense <= budget_jour:
        return budget_jour, "ok", "Cette dépense est dans ta norme habituelle."
    elif depense <= budget_jour * 1.3:
        return budget_jour, "attention", "Cette dépense réduit ton confort en fin de mois."
    else:
        return budget_jour, "depassement", "À ce rythme, ton équilibre mensuel est fragilisé."


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None})


@app.post("/check", response_class=HTMLResponse)
def check(
    request: Request,
    revenu: float = Form(...),
    fixes: float = Form(...),
    depense: float = Form(...),
    jours: int = Form(...),
):
    budget_jour, etat, message = analyser_depense(revenu, fixes, depense, jours)
    result = {
        "budget_jour": round(budget_jour, 2),
        "etat": etat,
        "message": message,
    }
    return templates.TemplateResponse("index.html", {"request": request, "result": result})
