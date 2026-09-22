# main.py
"""BetAnalyzer Pro - Serveur Flask principal avec sécurité anti-page vide."""

import os
from datetime import datetime, timedelta
import requests
from flask import Flask, render_template, request, jsonify
from config import config
from sports_engine import (
    get_demo_matches,
    get_demo_competitions,
    enrich_match,
    apply_rolling_window,
    filter_team_collision,
    LIVE_STATUSES,
)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


@app.route("/")
def index():
    """Page d'accueil principale."""
    status_filter = request.args.get("status", "all")
    competition_filter = request.args.get("competition", "all")
    continent_filter = request.args.get("continent", "all")
    date_filter = request.args.get("date", "all")
    search = request.args.get("q", "").strip().lower()

    data = fetch_matches()
    matches = data["matches"]
    competitions = data["competitions"]
    is_demo = data["is_demo"]

    # Application des filtres
    if status_filter == "live":
        matches = [m for m in matches if m.get("status") in LIVE_STATUSES]
    elif status_filter == "upcoming":
        matches = [m for m in matches if m.get("status") == "SCHEDULED"]
    elif status_filter == "finished":
        matches = [m for m in matches if m.get("status") == "FINISHED"]

    if competition_filter != "all":
        matches = [m for m in matches if m.get("competition", {}).get("code") == competition_filter]

    if continent_filter != "all":
        matches = [m for m in matches if m.get("competition", {}).get("continent") == continent_filter]

    if date_filter == "today":
        today = datetime.utcnow().date()
        matches = [m for m in matches if datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")).date() == today]
    elif date_filter == "tomorrow":
        tomorrow = (datetime.utcnow() + timedelta(days=1)).date()
        matches = [m for m in matches if datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")).date() == tomorrow]

    if search:
        matches = [
            m for m in matches
            if search in m.get("homeTeam", {}).get("name", "").lower()
            or search in m.get("awayTeam", {}).get("name", "").lower()
            or search in m.get("competition", {}).get("name", "").lower()
        ]

    # Compteurs
    live_count = sum(1 for m in data["matches"] if m.get("status") in LIVE_STATUSES)
    upcoming_count = sum(1 for m in data["matches"] if m.get("status") == "SCHEDULED")
    total_count = len(data["matches"])

    # Grouper les compétitions par continent
    comps_by_continent = {}
    for comp in competitions:
        cont = comp.get("continent", "Autre")
        if cont not in comps_by_continent:
            comps_by_continent[cont] = []
        comp_matches_count = sum(1 for m in data["matches"] if m.get("competition", {}).get("code") == comp["code"])
        comp["match_count"] = comp_matches_count
        comps_by_continent[cont].append(comp)

    # Grouper les matchs par date
    matches_by_date = {}
    for m in matches:
        try:
            d = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")).date()
            day_key = d.strftime("%Y-%m-%d")
            day_label = d.strftime("%A %d %B").capitalize()
        except (ValueError, KeyError):
            day_key = "unknown"
            day_label = "Aujourd'hui"

        if day_key not in matches_by_date:
            matches_by_date[day_key] = {"label": day_label, "matches": []}
        matches_by_date[day_key]["matches"].append(m)

    return render_template(
        "index.html",
        matches_by_date=matches_by_date,
        comps_by_continent=comps_by_continent,
        competitions=competitions,
        live_count=live_count,
        upcoming_count=upcoming_count,
        total_count=total_count,
        filtered_count=len(matches),
        is_demo=is_demo,
        status_filter=status_filter,
        competition_filter=competition_filter,
        continent_filter=continent_filter,
        date_filter=date_filter,
        search=search,
    )


@app.route("/match/<int:match_id>")
def match_detail(match_id):
    """Page détaillée d'un match avec les 16 critères."""
    data = fetch_matches()
    match = next((m for m in data["matches"] if m.get("id") == match_id), None)
    if not match:
        return "Match introuvable", 404
    return render_template("match_detail.html", match=match)


@app.route("/api/matches")
def api_matches():
    return jsonify(fetch_matches())


@app.route("/api/telegram/webhook", methods=["POST"])
def telegram_webhook():
    if not config.TELEGRAM_BOT_TOKEN:
        return jsonify({"ok": False, "error": "No bot token"}), 500
    body = request.get_json(silent=True) or {}
    if "message" in body:
        chat_id = body["message"]["chat"]["id"]
        text = body["message"].get("text", "")
        if text == "/start":
            send_telegram_message(chat_id, {
                "text": "⚽ *Bienvenue sur BetAnalyzer Pro !*\n\n16 critères d'analyse IA.",
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard": [
                        [{"text": "🚀 Ouvrir l'app", "web_app": {"url": config.MINI_APP_URL}}]
                    ]
                },
            })
    return jsonify({"ok": True})


def fetch_matches() -> dict:
    """Récupération sécurisée des matchs (Garantie de ne jamais avoir 0 match)."""
    api_key = config.FOOTBALL_DATA_API_KEY
    matches = []
    competitions = []
    is_demo = False

    if api_key:
        try:
            now = datetime.utcnow()
            date_from = (now - timedelta(days=2)).strftime("%Y-%m-%d")
            date_to = (now + timedelta(days=7)).strftime("%Y-%m-%d")

            resp = requests.get(
                f"{config.FOOTBALL_API_BASE}/matches",
                headers={"X-Auth-Token": api_key},
                params={"dateFrom": date_from, "dateTo": date_to},
                timeout=10,
            )
            if resp.status_code == 200:
                raw_matches = resp.json().get("matches", [])
                matches = [enrich_match(m) for m in raw_matches if m]
                
                comp_map = {}
                for m in matches:
                    c = m.get("competition", {}).get("code", "OTHER")
                    if c not in comp_map:
                        comp_map[c] = {
                            "code": c,
                            "name": m["competition"].get("name", "Ligue"),
                            "emblem": m["competition"].get("emblem", "⚽"),
                            "continent": "Europe",
                            "flag": m["competition"].get("emblem", "⚽"),
                        }
                competitions = list(comp_map.values())
        except Exception as e:
            print(f"API Error: {e}")

    # SI L'API API OFFICIELLE RENVOIE 0 MATCH -> BASCULER AUTOMATIQUEMENT SUR LE MODE DÉMO
    if not matches:
        matches = get_demo_matches()
        competitions = get_demo_competitions()
        is_demo = True

    # Filtrage et anti-collision
    window = apply_rolling_window(matches, days_past=2, days_future=7)
    active_matches = window["active_matches"] if window["active_matches"] else matches
    active_matches = filter_team_collision(active_matches)

    return {"matches": active_matches, "competitions": competitions, "is_demo": is_demo}


def send_telegram_message(chat_id: int, options: dict):
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, **options}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)