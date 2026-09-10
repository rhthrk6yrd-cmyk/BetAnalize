# sports_engine.py
"""
Moteur d'analyse sportive complet :
- Schémas tactiques
- Alchimie des joueurs
- Analyse joueur manquant
- Filtre anti-doublon équipes en direct
- Fenêtre glissante de 3 jours
- Score d'analyse global (11 critères)
"""

import random
from datetime import datetime, timedelta
from typing import Optional


# ============================================================
# 1. SCHÉMAS TACTIQUES - Formations prédéfinies
# ============================================================

FORMATIONS = {
    "4-4-2": [
        {"x": 50, "y": 90, "role": "GK"},
        {"x": 15, "y": 70, "role": "LB"},
        {"x": 38, "y": 72, "role": "CB"},
        {"x": 62, "y": 72, "role": "CB"},
        {"x": 85, "y": 70, "role": "RB"},
        {"x": 15, "y": 45, "role": "LM"},
        {"x": 38, "y": 48, "role": "CM"},
        {"x": 62, "y": 48, "role": "CM"},
        {"x": 85, "y": 45, "role": "RM"},
        {"x": 35, "y": 18, "role": "ST"},
        {"x": 65, "y": 18, "role": "ST"},
    ],
    "4-3-3": [
        {"x": 50, "y": 90, "role": "GK"},
        {"x": 15, "y": 70, "role": "LB"},
        {"x": 38, "y": 72, "role": "CB"},
        {"x": 62, "y": 72, "role": "CB"},
        {"x": 85, "y": 70, "role": "RB"},
        {"x": 25, "y": 50, "role": "CM"},
        {"x": 50, "y": 45, "role": "CDM"},
        {"x": 75, "y": 50, "role": "CM"},
        {"x": 15, "y": 20, "role": "LW"},
        {"x": 50, "y": 15, "role": "ST"},
        {"x": 85, "y": 20, "role": "RW"},
    ],
    "3-5-2": [
        {"x": 50, "y": 90, "role": "GK"},
        {"x": 25, "y": 72, "role": "CB"},
        {"x": 50, "y": 75, "role": "CB"},
        {"x": 75, "y": 72, "role": "CB"},
        {"x": 10, "y": 50, "role": "LWB"},
        {"x": 35, "y": 48, "role": "CM"},
        {"x": 50, "y": 42, "role": "CAM"},
        {"x": 65, "y": 48, "role": "CM"},
        {"x": 90, "y": 50, "role": "RWB"},
        {"x": 38, "y": 18, "role": "ST"},
        {"x": 62, "y": 18, "role": "ST"},
    ],
    "4-2-3-1": [
        {"x": 50, "y": 90, "role": "GK"},
        {"x": 15, "y": 70, "role": "LB"},
        {"x": 38, "y": 72, "role": "CB"},
        {"x": 62, "y": 72, "role": "CB"},
        {"x": 85, "y": 70, "role": "RB"},
        {"x": 35, "y": 55, "role": "CDM"},
        {"x": 65, "y": 55, "role": "CDM"},
        {"x": 15, "y": 35, "role": "LW"},
        {"x": 50, "y": 30, "role": "CAM"},
        {"x": 85, "y": 35, "role": "RW"},
        {"x": 50, "y": 12, "role": "ST"},
    ],
}

# Positions liées (pour calculer l'alchimie)
POSITION_LINKS = {
    "GK": ["CB"],
    "CB": ["GK", "CB", "CDM", "LB", "RB"],
    "LB": ["CB", "LW", "CM"],
    "RB": ["CB", "RW", "CM"],
    "CDM": ["CB", "CM", "CAM"],
    "CM": ["CDM", "CAM", "LW", "RW", "LB", "RB"],
    "CAM": ["CM", "CDM", "ST", "LW", "RW", "CF"],
    "LW": ["LB", "CM", "CAM", "ST"],
    "RW": ["RB", "CM", "CAM", "ST"],
    "ST": ["CAM", "LW", "RW", "CF"],
    "CF": ["CAM", "ST"],
}


def are_positions_linked(pos1: str, pos2: str) -> bool:
    """Vérifie si deux positions sont tactiquement liées."""
    return pos2 in POSITION_LINKS.get(pos1, []) or pos1 in POSITION_LINKS.get(pos2, [])


# ============================================================
# 2. GÉNÉRATION DE JOUEURS (Démo)
# ============================================================

def generate_demo_players(side: str = "home") -> list[dict]:
    """Génère 11 joueurs fictifs avec stats réalistes."""

    if side == "home":
        names = [
            "Donnarumma", "Hakimi", "Marquinhos", "Skriniar", "N.Mendes",
            "Vitinha", "Zaïre-Emery", "Barcola", "Dembélé", "Gonçalo Ramos", "Kolo Muani",
        ]
    else:
        names = [
            "Ter Stegen", "Koundé", "Araujo", "Christensen", "Baldé",
            "Pedri", "De Jong", "Gavi", "Raphinha", "Lewandowski", "Yamal",
        ]

    positions = ["GK", "RB", "CB", "CB", "LB", "CM", "CDM", "CM", "RW", "ST", "LW"]
    numbers = [1, 2, 5, 4, 25, 17, 33, 7, 10, 9, 23]

    # Choisir aléatoirement un joueur absent
    missing_index = random.randint(0, 10) if random.random() > 0.4 else -1
    missing_reasons = ["Blessure musculaire", "Suspension", "Maladie", "Choix du coach"]

    players = []
    for i, name in enumerate(names):
        is_missing = (i == missing_index)
        players.append({
            "id": (1000 if side == "home" else 2000) + i,
            "name": name,
            "position": positions[i],
            "number": numbers[i],
            "rating": random.randint(78, 93),
            "is_captain": (i == 2),
            "is_injured": is_missing,
            "is_suspended": False,
            "is_missing": is_missing,
            "missing_reason": random.choice(missing_reasons) if is_missing else None,
            "stats": {
                "goals": random.randint(0, 15),
                "assists": random.randint(0, 12),
                "pass_accuracy": random.randint(75, 95),
                "tackles": random.randint(5, 45),
                "minutes_played": random.randint(500, 2500),
                "yellow_cards": random.randint(0, 6),
                "red_cards": random.randint(0, 1),
            },
        })

    return players


# ============================================================
# 3. ALCHIMIE DES JOUEURS (Chemistry)
# ============================================================

def calculate_chemistry(players: list[dict]) -> list[dict]:
    """Calcule les liens d'alchimie entre tous les joueurs."""
    links = []

    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            p1 = players[i]
            p2 = players[j]

            if p1["is_missing"] or p2["is_missing"]:
                continue

            score = 50  # Base
            reasons = []

            # Proximité de position
            if are_positions_linked(p1["position"], p2["position"]):
                score += 20
                reasons.append("Positions complémentaires")

            # Même niveau
            if abs(p1["rating"] - p2["rating"]) < 10:
                score += 10
                reasons.append("Niveau similaire")

            # Combo passeur-buteur
            if p1["stats"]["assists"] > 5 and p2["stats"]["goals"] > 5:
                score += 15
                reasons.append(f"{p1['name']} passeur → {p2['name']} buteur")
            if p2["stats"]["assists"] > 5 and p1["stats"]["goals"] > 5:
                score += 15
                reasons.append(f"{p2['name']} passeur → {p1['name']} buteur")

            # Précision de passe
            if p1["stats"]["pass_accuracy"] > 80 and p2["stats"]["pass_accuracy"] > 80:
                score += 10
                reasons.append("Haute précision de passes")

            score = min(100, max(0, score))

            if score >= 75:
                link_type = "strong"
            elif score >= 50:
                link_type = "medium"
            else:
                link_type = "weak"

            if score >= 40:
                links.append({
                    "player1_id": p1["id"],
                    "player2_id": p2["id"],
                    "player1_name": p1["name"],
                    "player2_name": p2["name"],
                    "player1_number": p1["number"],
                    "player2_number": p2["number"],
                    "chemistry_score": score,
                    "link_type": link_type,
                    "reason": " • ".join(reasons) if reasons else "Lien de base",
                })

    links.sort(key=lambda x: x["chemistry_score"], reverse=True)
    return links


def get_overall_chemistry(links: list[dict]) -> int:
    """Score d'alchimie global de l'équipe."""
    if not links:
        return 50
    return round(sum(l["chemistry_score"] for l in links) / len(links))


# ============================================================
# 4. ANALYSE JOUEUR MANQUANT
# ============================================================

def calculate_player_impact(player: dict) -> int:
    """Calcule le score d'impact d'un joueur (0-100)."""
    impact = player["rating"]

    position_weights = {
        "GK": 15, "CB": 10, "ST": 15, "CAM": 12,
        "CM": 10, "CDM": 10, "LW": 8, "RW": 8,
        "LB": 6, "RB": 6, "CF": 12,
    }
    impact += position_weights.get(player["position"], 5)

    if player["stats"]["goals"] > 10:
        impact += 10
    if player["stats"]["assists"] > 8:
        impact += 8
    if player["is_captain"]:
        impact += 10

    return min(100, impact)


def get_impact_areas(player: dict) -> list[str]:
    """Retourne les zones de jeu affectées par l'absence."""
    areas_map = {
        "GK": ["Défense", "Sorties aériennes", "Relance"],
        "CB": ["Solidité défensive", "Couverture"],
        "LB": ["Flanc gauche", "Couverture défensive"],
        "RB": ["Flanc droit", "Couverture défensive"],
        "CDM": ["Milieu défensif", "Transition", "Pressing"],
        "CM": ["Milieu de terrain", "Distribution", "Contrôle"],
        "CAM": ["Création", "Passes décisives", "Dernier tiers"],
        "LW": ["Attaque gauche", "Centres", "Dribbles"],
        "RW": ["Attaque droite", "Centres", "Dribbles"],
        "ST": ["Finition", "Poids en attaque", "Occupation défenseurs"],
        "CF": ["Jeu en pointe", "Déviation", "Finition"],
    }
    areas = areas_map.get(player["position"], ["Jeu général"])
    if player["is_captain"]:
        areas.append("Leadership")
    return areas


def find_best_replacement(missing_player: dict, available_players: list[dict]) -> Optional[dict]:
    """Trouve le meilleur remplaçant pour un joueur absent."""
    # Même poste
    same_pos = [p for p in available_players if p["position"] == missing_player["position"]]
    if same_pos:
        return max(same_pos, key=lambda p: p["rating"])

    # Poste compatible
    compatible = [
        p for p in available_players
        if are_positions_linked(p["position"], missing_player["position"])
    ]
    if compatible:
        return max(compatible, key=lambda p: p["rating"])

    return None


def analyze_missing_player(players: list[dict], team_name: str) -> Optional[dict]:
    """Analyse l'impact du joueur manquant le plus important."""
    missing = [p for p in players if p["is_missing"]]
    if not missing:
        return None

    # Le plus impactant
    most_impactful = max(missing, key=calculate_player_impact)
    impact_score = calculate_player_impact(most_impactful)
    impact_areas = get_impact_areas(most_impactful)

    available = [p for p in players if not p["is_missing"]]
    replacement = find_best_replacement(most_impactful, available)

    return {
        "player": most_impactful,
        "team": team_name,
        "impact_score": impact_score,
        "impact_areas": impact_areas,
        "replacement": replacement,
        "analysis_text": (
            f"🔴 Absent: {most_impactful['name']} ({most_impactful['position']})\n"
            f"📊 Impact: {impact_score}/100\n"
            f"❓ Raison: {most_impactful.get('missing_reason', 'Non précisée')}\n"
            f"⚡ Zones: {', '.join(impact_areas)}"
        ),
    }


# ============================================================
# 5. FILTRE ANTI-DOUBLON (Équipes en direct)
# ============================================================

LIVE_STATUSES = {"IN_PLAY", "LIVE", "PAUSED"}


def filter_duplicate_live_teams(matches: list[dict]) -> list[dict]:
    """Empêche qu'une équipe apparaisse dans 2 matchs en direct."""
    live_matches = [m for m in matches if m["status"] in LIVE_STATUSES]
    other_matches = [m for m in matches if m["status"] not in LIVE_STATUSES]

    seen_team_ids = set()
    filtered_live = []

    # Trier par date (plus récent = priorité)
    live_matches.sort(key=lambda m: m["utcDate"], reverse=True)

    for match in live_matches:
        home_id = match["homeTeam"]["id"]
        away_id = match["awayTeam"]["id"]

        if home_id in seen_team_ids or away_id in seen_team_ids:
            continue  # Doublon ignoré

        seen_team_ids.add(home_id)
        seen_team_ids.add(away_id)
        filtered_live.append(match)

    return filtered_live + other_matches


def detect_duplicate_teams(matches: list[dict]) -> dict:
    """Détecte les équipes en double dans les matchs en direct."""
    live_matches = [m for m in matches if m["status"] in LIVE_STATUSES]
    team_count = {}

    for match in live_matches:
        for team_key in ["homeTeam", "awayTeam"]:
            team = match[team_key]
            tid = team["id"]
            if tid not in team_count:
                team_count[tid] = {"name": team.get("shortName", team["name"]), "count": 0}
            team_count[tid]["count"] += 1

    duplicates = [v["name"] for v in team_count.values() if v["count"] > 1]
    return {"has_duplicates": len(duplicates) > 0, "duplicate_teams": duplicates}


# ============================================================
# 6. FENÊTRE GLISSANTE DE 3 JOURS
# ============================================================

def apply_sliding_window(current_matches: list[dict], new_matches: list[dict] = None) -> dict:
    """
    Fenêtre glissante de 3 jours centrée sur aujourd'hui.
    Supprime les matchs expirés, ajoute les nouveaux.
    """
    if new_matches is None:
        new_matches = []

    now = datetime.utcnow()

    # Fenêtre : hier 00h00 → après-demain 23h59
    window_start = now - timedelta(days=1)
    window_start = window_start.replace(hour=0, minute=0, second=0, microsecond=0)

    window_end = now + timedelta(days=2)
    window_end = window_end.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Fusionner (les nouveaux écrasent les anciens)
    all_matches = {m["id"]: m for m in current_matches}
    added_new = []

    for m in new_matches:
        if m["id"] not in all_matches:
            added_new.append(m)
        all_matches[m["id"]] = m

    # Séparer actifs et expirés
    active = []
    expired = []

    for match in all_matches.values():
        try:
            match_date = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00"))
            match_date = match_date.replace(tzinfo=None)
        except (ValueError, AttributeError):
            match_date = now

        if window_start <= match_date <= window_end:
            active.append(match)
        else:
            expired.append(match)

    active.sort(key=lambda m: m["utcDate"])

    return {
        "active_matches": active,
        "expired_matches": expired,
        "new_matches": added_new,
        "window_start": window_start.strftime("%d/%m/%Y"),
        "window_end": window_end.strftime("%d/%m/%Y"),
        "active_count": len(active),
        "expired_count": len(expired),
        "new_count": len(added_new),
    }


# ============================================================
# 7. SCORE D'ANALYSE GLOBAL (11 critères)
# ============================================================

def calculate_full_analysis(match: dict) -> dict:
    """Calcule les 11 critères d'analyse pour un match."""
    tactical_score = 60
    if match.get("homeTeam", {}).get("formation"):
        tactical_score += 10
    if match.get("awayTeam", {}).get("formation"):
        tactical_score += 10
    tactical_score += random.randint(0, 20)

    home_links = match.get("homeTeam", {}).get("chemistryLinks", [])
    away_links = match.get("awayTeam", {}).get("chemistryLinks", [])
    avg_home = sum(l["chemistry_score"] for l in home_links) / len(home_links) if home_links else 50
    avg_away = sum(l["chemistry_score"] for l in away_links) / len(away_links) if away_links else 50
    chemistry_score = round((avg_home + avg_away) / 2)

    missing_score = 80
    mpa = match.get("missingPlayerAnalysis", {})
    if mpa.get("home"):
        missing_score -= mpa["home"]["impact_score"] * 0.3
    if mpa.get("away"):
        missing_score -= mpa["away"]["impact_score"] * 0.3

    return {
        "form": random.randint(60, 100),
        "head_to_head": random.randint(50, 90),
        "ranking": random.randint(50, 90),
        "stakes": random.randint(50, 90),
        "home_away": random.randint(55, 85),
        "goals": random.randint(50, 90),
        "momentum": random.randint(50, 90),
        "over_under": random.randint(50, 90),
        "tactical": min(100, tactical_score),
        "chemistry": min(100, max(0, chemistry_score)),
        "missing_player": min(100, max(0, round(missing_score))),
    }


# ============================================================
# 8. ENRICHISSEMENT COMPLET D'UN MATCH
# ============================================================

def enrich_match(match: dict) -> dict:
    """Ajoute tactique, chimie, absences et analyse à un match."""
    home_players = generate_demo_players("home")
    away_players = generate_demo_players("away")

    home_formation_name = random.choice(list(FORMATIONS.keys()))
    away_formation_name = random.choice(list(FORMATIONS.keys()))

    home_formation = {
        "name": home_formation_name,
        "positions": [
            {**pos, "player": home_players[i]}
            for i, pos in enumerate(FORMATIONS[home_formation_name])
        ],
    }
    away_formation = {
        "name": away_formation_name,
        "positions": [
            {**pos, "player": away_players[i]}
            for i, pos in enumerate(FORMATIONS[away_formation_name])
        ],
    }

    home_chemistry = calculate_chemistry(home_players)
    away_chemistry = calculate_chemistry(away_players)

    home_missing = analyze_missing_player(
        home_players,
        match.get("homeTeam", {}).get("shortName", "Domicile"),
    )
    away_missing = analyze_missing_player(
        away_players,
        match.get("awayTeam", {}).get("shortName", "Extérieur"),
    )

    match["homeTeam"]["formation"] = home_formation
    match["homeTeam"]["players"] = home_players
    match["homeTeam"]["chemistryLinks"] = home_chemistry
    match["homeTeam"]["missingPlayers"] = [p for p in home_players if p["is_missing"]]

    match["awayTeam"]["formation"] = away_formation
    match["awayTeam"]["players"] = away_players
    match["awayTeam"]["chemistryLinks"] = away_chemistry
    match["awayTeam"]["missingPlayers"] = [p for p in away_players if p["is_missing"]]

    match["missingPlayerAnalysis"] = {
        "home": home_missing,
        "away": away_missing,
    }

    match["analysis"] = calculate_full_analysis(match)

    return match


# ============================================================
# 9. DONNÉES DE DÉMO
# ============================================================

def get_demo_matches() -> list[dict]:
    """Génère des matchs fictifs réalistes."""
    now = datetime.utcnow()

    raw_matches = [
        {
            "id": 1001,
            "competition": {"name": "Ligue 1", "code": "FL1", "emblem": "🇫🇷", "country": "France"},
            "homeTeam": {"id": 524, "name": "Paris Saint-Germain", "shortName": "PSG", "crest": ""},
            "awayTeam": {"id": 516, "name": "Olympique de Marseille", "shortName": "OM", "crest": ""},
            "utcDate": (now + timedelta(hours=2)).isoformat() + "Z",
            "status": "SCHEDULED",
            "matchday": 28,
            "score": {"fullTime": {"home": None, "away": None}, "halfTime": {"home": None, "away": None}},
        },
        {
            "id": 1002,
            "competition": {"name": "Ligue 1", "code": "FL1", "emblem": "🇫🇷", "country": "France"},
            "homeTeam": {"id": 521, "name": "Olympique Lyonnais", "shortName": "OL", "crest": ""},
            "awayTeam": {"id": 522, "name": "AS Monaco", "shortName": "ASM", "crest": ""},
            "utcDate": (now - timedelta(minutes=30)).isoformat() + "Z",
            "status": "IN_PLAY",
            "matchday": 28,
            "score": {"fullTime": {"home": 1, "away": 2}, "halfTime": {"home": 0, "away": 1}},
            "minute": 67,
        },
        {
            "id": 1003,
            "competition": {"name": "Premier League", "code": "PL", "emblem": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "country": "England"},
            "homeTeam": {"id": 64, "name": "Liverpool FC", "shortName": "LIV", "crest": ""},
            "awayTeam": {"id": 65, "name": "Manchester City", "shortName": "MCI", "crest": ""},
            "utcDate": (now + timedelta(hours=5)).isoformat() + "Z",
            "status": "SCHEDULED",
            "matchday": 30,
            "score": {"fullTime": {"home": None, "away": None}, "halfTime": {"home": None, "away": None}},
        },
        {
            "id": 1004,
            "competition": {"name": "Premier League", "code": "PL", "emblem": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "country": "England"},
            "homeTeam": {"id": 66, "name": "Arsenal FC", "shortName": "ARS", "crest": ""},
            "awayTeam": {"id": 61, "name": "Chelsea FC", "shortName": "CHE", "crest": ""},
            "utcDate": (now - timedelta(hours=3)).isoformat() + "Z",
            "status": "FINISHED",
            "matchday": 30,
            "score": {"fullTime": {"home": 3, "away": 1}, "halfTime": {"home": 2, "away": 0}},
        },
        {
            "id": 1005,
            "competition": {"name": "La Liga", "code": "PD", "emblem": "🇪🇸", "country": "Spain"},
            "homeTeam": {"id": 81, "name": "FC Barcelona", "shortName": "BAR", "crest": ""},
            "awayTeam": {"id": 86, "name": "Real Madrid CF", "shortName": "RMA", "crest": ""},
            "utcDate": (now + timedelta(hours=8)).isoformat() + "Z",
            "status": "SCHEDULED",
            "matchday": 32,
            "score": {"fullTime": {"home": None, "away": None}, "halfTime": {"home": None, "away": None}},
        },
        {
            "id": 1006,
            "competition": {"name": "Champions League", "code": "CL", "emblem": "🏆", "country": "Europe"},
            "homeTeam": {"id": 505, "name": "Bayern Munich", "shortName": "BAY", "crest": ""},
            "awayTeam": {"id": 503, "name": "Inter Milan", "shortName": "INT", "crest": ""},
            "utcDate": (now - timedelta(minutes=10)).isoformat() + "Z",
            "status": "IN_PLAY",
            "matchday": 4,
            "score": {"fullTime": {"home": 2, "away": 2}, "halfTime": {"home": 1, "away": 1}},
            "minute": 82,
        },
    ]

    return [enrich_match(m) for m in raw_matches]


def get_demo_competitions() -> list[dict]:
    """Liste des compétitions de démo."""
    return [
        {"code": "PL", "name": "Premier League", "emblem": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
        {"code": "PD", "name": "La Liga", "emblem": "🇪🇸"},
        {"code": "FL1", "name": "Ligue 1", "emblem": "🇫🇷"},
        {"code": "BL1", "name": "Bundesliga", "emblem": "🇩🇪"},
        {"code": "SA", "name": "Serie A", "emblem": "🇮🇹"},
        {"code": "CL", "name": "Champions League", "emblem": "🏆"},
    ]