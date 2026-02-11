from dataclasses import dataclass


@dataclass
class CompanionContext:
    name: str
    tone: str
    score: int
    risk: str
    streak_stable: int
    streak_adjust: int
    streak_goal: int
    drivers: list[tuple[str, str]]


def _tone_prefix(tone: str) -> str:
    tone = (tone or "calm").lower()
    if tone == "direct":
        return "Direct read:"
    if tone == "playful":
        return "Quick vibe:"
    if tone == "coach":
        return "Coach mode:"
    return "Calm check‑in:"


def _driver_line(ctx: CompanionContext) -> str:
    if not ctx.drivers:
        return "Your drivers look balanced right now."
    top = ctx.drivers[0]
    return f"Top driver: {top[0]} ({top[1]})."


def respond(message: str, ctx: CompanionContext) -> str:
    msg = (message or "").strip().lower()
    prefix = _tone_prefix(ctx.tone)
    name = ctx.name or "there"

    canned = [
        f"{prefix} Hey {name}, your current score is {ctx.score}. {_driver_line(ctx)}",
        f"{prefix} You're at {ctx.score}/100. Keep a steady pace for 48 hours to lift stability.",
        f"{prefix} Risk is {ctx.risk}. A small buffer transfer this week will help.",
        f"{prefix} Stable streak: {ctx.streak_stable} days. Keep it alive with one calm check today.",
        f"{prefix} Adjustments streak: {ctx.streak_adjust} days. You're responding early — keep that rhythm.",
        f"{prefix} Goal streak: {ctx.streak_goal} days. A tiny goal deposit keeps momentum positive.",
        f"{prefix} If you trim 5% on flexible spend, your drift should soften this week.",
        f"{prefix} If income rises 5%, your cushion trend improves over the next 4 weeks.",
        f"{prefix} I can show risk drivers or build a plan — your call.",
        f"{prefix} You're not behind — you're building a clearer signal.",
    ]

    if "explain" in msg or "score" in msg:
        return f"{prefix} Your score blends stability, drift, cushion, and consistency. {_driver_line(ctx)}"
    if "scenario" in msg or "what if" in msg:
        return f"{prefix} Try a 5% expense reduction scenario — it typically lifts runway by 1–2 points."
    if "risk" in msg or "driver" in msg:
        return f"{prefix} {_driver_line(ctx)} Lowering fixed ratio usually improves risk first."
    if "plan" in msg:
        return f"{prefix} Plan: set a weekly pace, cap flexible spend, and add a small buffer transfer."

    return canned[ctx.score % len(canned)]
