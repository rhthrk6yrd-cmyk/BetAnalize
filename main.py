# main.py
"""
BetAnalyzer Pro - Telegram Mini App
Serveur Flask principal avec API + rendu HTML
"""

import os
from datetime import datetime, timedelta
import requests
from flask import Flask, render_template, request, jsonify
from config import config
from sports_engine import (
    get_demo_matches,
    get_demo_competitions,
    enrich_match,
    filter_duplicate_live_teams,
    detect_duplicate_teams,
    apply_sliding_window,
    LIVE_STATUSES,
)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


# ============================================================
# ROUTE PRINCIPALE - Page d'accueil
# ============================================================

@app.route("/")
def index():
    """Page principale de la Mini App."""
    status_filter = request.args.get("status", "all")
    competition_filter = request.args.get("competition", "all")

    # Récupérer les données
    data = fetch_matches(status_filter, competition_filter)
    matches = data["matches"]
    competitions = data["competitions"]
    is_demo = data["is_demo"]

    # Compteur live
    live_count = sum(1 for m in matches if m.get("status") in LIVE_STATUSES)

    # Grouper par compétition
    grouped = {}
    for match in matches:
        code = match.get("competition", {}).get("code", "OTHER")
        if code not in grouped:
            grouped[code] = {
                "name": match.get("competition", {}).get("name", "Autre"),
                "emblem": match.get("competition", {}).get("emblem", "⚽"),
                "matches": [],
            }
        grouped[code]["matches"].append(match)

    # Fenêtre glissante info
    window = apply_sliding_window(matches)
    window_info = (
        f"📅 Fenêtre: {window['window_start']} → {window['window_end']} | "
        f"✅ {window['active_count']} actifs | "
        f"🗑️ {window['expired_count']} expirés"
    )

    # Détection doublons
    duplicates = detect_duplicate_teams(matches)

    return render_template(
        "index.html",
        grouped=grouped,
        competitions=competitions,
        live_count=live_count,
        total_matches=len(matches),
        is_demo=is_demo,
        status_filter=status_filter,
        competition_filter=competition_filter,
        window_info=window_info,
        duplicates=duplicates,
    )


# ============================================================
# API - Données JSON (pour Telegram / AJAX)
# ============================================================

@app.route("/api/matches")
def api_matches():
    """API JSON pour les matchs."""
    status = request.args.get("status", "all")
    competition = request.args.get("competition", "all")
    data = fetch_matches(status, competition)
    return jsonify(data)


@app.route("/api/telegram/webhook", methods=["POST"])
def telegram_webhook():
    """Webhook Telegram Bot."""
    if not config.TELEGRAM_BOT_TOKEN:
        return jsonify({"ok": False, "error": "No bot token"}), 500

    body = request.get_json(silent=True) or {}

    if "message" in body:
        chat_id = body["message"]["chat"]["id"]
        text = body["message"].get("text", "")

        if text == "/start":
            send_telegram_message(chat_id, {
                "text": (
                    "⚽ *Bienvenue sur BetAnalyzer Pro !*\n\n"
                    "📊 11 critères d'analyse\n"
                    "🎯 Schéma tactique\n"
                    "🔗 Alchimie des joueurs\n"
                    "🚑 Impact des absences\n\n"
                    "👇 Ouvre l'application ci-dessous !"
                ),
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard": [
                        [{"text": "🚀 Ouvrir BetAnalyzer Pro", "web_app": {"url": config.MINI_APP_URL}}],
                        [{"text": "📊 Matchs en direct", "callback_data": "live_matches"}],
                    ]
                },
            })

        elif text == "/live":
            data = fetch_matches("IN_PLAY", "all")
            live = data["matches"]
            if not live:
                send_telegram_message(chat_id, {"text": "😴 Aucun match en direct pour le moment."})
            else:
                msg = "🔴 *Matchs en direct :*\n\n"
                for m in live[:10]:
                    h = m["homeTeam"].get("shortName", "Home")
                    a = m["awayTeam"].get("shortName", "Away")
                    sh = m["score"]["fullTime"]["home"]
                    sa = m["score"]["fullTime"]["away"]
                    sh = sh if sh is not None else "-"
                    sa = sa if sa is not None else "-"
                    minute = m.get("minute", "?")
                    comp = m["competition"]["name"]
                    msg += f"⚽ {h} {sh} - {sa} {a}\n   🏆 {comp} • ⏱ {minute}'\n\n"
                send_telegram_message(chat_id, {
                    "text": msg,
                    "parse_mode": "Markdown",
                    "reply_markup": {
                        "inline_keyboard": [
                            [{"text": "📱 Détails", "web_app": {"url": config.MINI_APP_URL}}]
                        ]
                    },
                })

        elif text == "/help":
            send_telegram_message(chat_id, {
                "text": (
                    "📖 *Commandes :*\n\n"
                    "/start - Démarrer\n"
                    "/live - Matchs en direct\n"
                    "/help - Aide"
                ),
                "parse_mode": "Markdown",
            })

    return jsonify({"ok": True})


# ============================================================
# FONCTIONS UTILITAIRES (CORRECTION DU FORMAT DE DATE)
# ============================================================

def fetch_matches(status_filter: str = "all", competition_filter: str = "all") -> dict:
    """Récupère les matchs depuis l'API Football Data ou le mode démo."""
    api_key = config.FOOTBALL_DATA_API_KEY

    if not api_key:
        return {
            "matches": get_demo_matches(),
            "competitions": get_demo_competitions(),
            "is_demo": True,
        }

    try:
        now = datetime.utcnow()
        # Format obligatoire YYYY-MM-DD pour Football Data API
        date_from = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        date_to = (now + timedelta(days=2)).strftime("%Y-%m-%d")

        params = {
            "dateFrom": date_from,
            "dateTo": date_to,
        }

        if status_filter != "all":
            params["status"] = status_filter
        if competition_filter != "all":
            params["competitions"] = competition_filter

        resp = requests.get(
            f"{config.FOOTBALL_API_BASE}/matches",
            headers={"X-Auth-Token": api_key},
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        raw_matches = data.get("matches", [])
        matches = [enrich_match(m) for m in raw_matches]

        # Extraire les compétitions
        comp_map = {}
        for m in matches:
            c = m["competition"]["code"]
            if c not in comp_map:
                comp_map[c] = {
                    "code": c,
                    "name": m["competition"]["name"],
                    "emblem": m["competition"].get("emblem", "⚽"),
                }
        competitions = list(comp_map.values())
        is_demo = False

    except Exception as e:
        print(f"API Error: {e}")
        matches = get_demo_matches()
        competitions = get_demo_competitions()
        is_demo = True

    # Filtrer par statut / compétition
    if status_filter != "all":
        matches = [m for m in matches if m.get("status") == status_filter]
    if competition_filter != "all":
        matches = [m for m in matches if m.get("competition", {}).get("code") == competition_filter]

    # Anti-doublon
    matches = filter_duplicate_live_teams(matches)

    return {
        "matches": matches,
        "competitions": competitions,
        "is_demo": is_demo,
    }


def send_telegram_message(chat_id: int, options: dict):
    """Envoie un message via l'API Telegram."""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, **options}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram send error: {e}")


# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)