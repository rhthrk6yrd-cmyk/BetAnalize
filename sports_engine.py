# sports_engine.py
"""BetAnalyzer Pro - Moteur d'analyse complet à 16 critères (Format Compact)."""

import math, random
from datetime import datetime, timedelta

FORMATIONS = {
    "4-4-2": [{"x":50,"y":90,"role":"GK"},{"x":15,"y":70,"role":"LB"},{"x":38,"y":72,"role":"CB"},{"x":62,"y":72,"role":"CB"},{"x":85,"y":70,"role":"RB"},{"x":15,"y":45,"role":"LM"},{"x":38,"y":48,"role":"CM"},{"x":62,"y":48,"role":"CM"},{"x":85,"y":45,"role":"RM"},{"x":35,"y":18,"role":"ST"},{"x":65,"y":18,"role":"ST"}],
    "4-3-3": [{"x":50,"y":90,"role":"GK"},{"x":15,"y":70,"role":"LB"},{"x":38,"y":72,"role":"CB"},{"x":62,"y":72,"role":"CB"},{"x":85,"y":70,"role":"RB"},{"x":25,"y":50,"role":"CM"},{"x":50,"y":45,"role":"CDM"},{"x":75,"y":50,"role":"CM"},{"x":15,"y":20,"role":"LW"},{"x":50,"y":15,"role":"ST"},{"x":85,"y":20,"role":"RW"}],
    "3-5-2": [{"x":50,"y":90,"role":"GK"},{"x":25,"y":72,"role":"CB"},{"x":50,"y":75,"role":"CB"},{"x":75,"y":72,"role":"CB"},{"x":10,"y":50,"role":"LWB"},{"x":35,"y":48,"role":"CM"},{"x":50,"y":42,"role":"CAM"},{"x":65,"y":48,"role":"CM"},{"x":90,"y":50,"role":"RWB"},{"x":38,"y":18,"role":"ST"},{"x":62,"y":18,"role":"ST"}],
    "4-2-3-1": [{"x":50,"y":90,"role":"GK"},{"x":15,"y":70,"role":"LB"},{"x":38,"y":72,"role":"CB"},{"x":62,"y":72,"role":"CB"},{"x":85,"y":70,"role":"RB"},{"x":35,"y":55,"role":"CDM"},{"x":65,"y":55,"role":"CDM"},{"x":15,"y":35,"role":"LW"},{"x":50,"y":30,"role":"CAM"},{"x":85,"y":35,"role":"RW"},{"x":50,"y":12,"role":"ST"}]
}
LIVE_STATUSES = {"IN_PLAY", "LIVE", "PAUSED"}
WEIGHTS = {"form": 0.25, "ranking": 0.20, "h2h": 0.15, "stakes": 0.10, "home_away": 0.10, "goals": 0.10, "momentum": 0.10}

def calculate_form(last_5):
    if not last_5: last_5 = [random.choice(["W","D","L"]) for _ in range(5)]
    pts = sum(3 if r=="W" else (1 if r=="D" else 0) for r in last_5)
    score = round((pts / (len(last_5)*3)) * 100) if last_5 else 50
    lbl = "Excellente" if score>=75 else ("Bonne" if score>=50 else ("Moyenne" if score>=30 else "Mauvaise"))
    return {"results": last_5, "points": pts, "max_points": len(last_5)*3, "score": score, "label": lbl}

def calculate_ranking(rank, total, ppm, gd):
    r_score = round((1 - (rank - 1) / max(total - 1, 1)) * 100)
    p_score = min(100, round(ppm * 33))
    g_score = min(100, max(0, 50 + gd))
    return {"rank": rank, "total_teams": total, "points_per_match": round(ppm,2), "goal_diff": gd, "score": round(r_score*0.5 + p_score*0.3 + g_score*0.2)}

def calculate_h2h(matches):
    if not matches: matches = [{"home_win": random.choice([True,False]), "draw": False, "goals": random.randint(0,5)} for _ in range(5)]
    hw = sum(1 for m in matches if m.get("home_win"))
    dr = sum(1 for m in matches if m.get("draw"))
    aw = len(matches) - hw - dr
    avg_g = sum(m.get("goals",0) for m in matches) / max(len(matches),1)
    return {"home_wins": hw, "draws": dr, "away_wins": aw, "avg_goals": round(avg_g,2), "score": round((hw/max(len(matches),1))*100)}

def calculate_stakes(situation):
    bonuses = {"title_race": 20, "relegation": 25, "european_qualification": 15, "african_qualification": 15, "mid_table": 0}
    labels = {"title_race": "🏆 Titre", "relegation": "Maintien", "european_qualification": "Europe", "african_qualification": "Afrique", "mid_table": "Milieu"}
    b = bonuses.get(situation, 0)
    return {"situation": situation, "label": labels.get(situation, "Autre"), "bonus": b, "score": 50 + b}

def calculate_home_away(is_home, h_form, a_form):
    base = h_form*100 if is_home else a_form*100
    b = 12 if is_home else -5
    return {"location": "Dom" if is_home else "Ext", "bonus": b, "score": min(100, max(0, round(base + b)))}

def calculate_goals(g_scored, g_conceded):
    att = min(100, round(g_scored * 30))
    def_s = max(0, min(100, round((3 - g_conceded) * 33)))
    return {"goals_scored_avg": round(g_scored,2), "goals_conceded_avg": round(g_conceded,2), "attack_score": att, "defense_score": def_s, "score": round((att+def_s)/2)}

def calculate_momentum(streak):
    st, count = streak.get("type","none"), streak.get("count",0)
    b = 22 if st=="W" and count>=3 else (-18 if st=="L" and count>=3 else (count*5 if st=="W" else (-count*4 if st=="L" else 0)))
    lbl = f"{count} V conséc." if st=="W" else (f"{count} D conséc." if st=="L" else "Neutre")
    return {"type": st, "count": count, "bonus": b, "label": lbl, "score": max(0, min(100, 50+b))}

def calculate_over_under_btts(g_a, g_b, h2h_g):
    exp = (g_a + g_b + h2h_g) / 3
    o25 = min(95, max(5, round(exp * 30)))
    btts = min(95, max(5, round((g_a * g_b)*40 + 20)))
    return {"expected_goals": round(exp,2), "over_25": o25, "under_25": 100-o25, "over_35": max(5, o25-25), "btts_yes": btts, "btts_no": 100-btts}

def poisson_probability(k, lam):
    return ((math.pow(lam, k) * math.exp(-lam)) / math.factorial(k)) if lam > 0 else 0.0

def calculate_poisson_distribution(lam_h, lam_a):
    hw, dr, aw = 0.0, 0.0, 0.0
    for i in range(7):
        for j in range(7):
            p = poisson_probability(i, lam_h) * poisson_probability(j, lam_a)
            if i > j: hw += p
            elif i == j: dr += p
            else: aw += p
    tot = hw + dr + aw
    if tot > 0: hw, dr, aw = hw/tot, dr/tot, aw/tot
    return {"lambda_home": round(lam_h,2), "lambda_away": round(lam_a,2), "prob_1": round(hw*100), "prob_N": round(dr*100), "prob_2": round(aw*100)}

def calculate_chemistry(stability=None, xi_reg=None):
    s = stability if stability is not None else random.uniform(0.5,1.0)
    x = xi_reg if xi_reg is not None else random.uniform(0.5,1.0)
    score = round((s*0.6 + x*0.4)*100)
    return {"squad_stability": round(s*100), "xi_regularity": round(x*100), "score": score, "label": "Excellente" if score>=75 else ("Bonne" if score>=50 else "Faible")}

def calculate_missing_impact(missing=None):
    if not missing:
        missing = []
        if random.random() > 0.5:
            missing = [{"name": random.choice(["Mbappé","Haaland","Salah","Vinicius"]), "position": "ST", "importance": random.randint(70,95), "reason": "Blessure"}]
    malus = sum(8 if p.get("importance",50)>=85 else (5 if p.get("importance",50)>=70 else 3) for p in missing)
    malus = min(30, malus)
    return {"missing_count": len(missing), "missing_players": missing, "malus_percent": malus, "score": max(0, 100 - malus*2)}

def calculate_fatigue(days_rest):
    malus = 8 if days_rest < 4 else (4 if days_rest == 4 else 0)
    score = 60 if days_rest < 4 else (80 if days_rest == 4 else 100)
    lbl = "Fatigue élevée" if days_rest < 4 else ("Repos correct" if days_rest == 4 else "Fraîcheur optimale")
    return {"days_rest": days_rest, "malus_percent": malus, "score": score, "label": lbl}

def calculate_clean_sheet(cs, total):
    tot = max(1, total)
    ratio = (cs / tot) * 100
    return {"clean_sheets": cs, "total_matches": tot, "ratio": round(ratio), "score": round(ratio), "label": "🧱 Solide" if ratio>=40 else "⚠️ Fragile"}

def calculate_discipline(y_avg, r_avg, f_avg):
    pen = y_avg*5 + r_avg*25 + f_avg*2
    score = max(0, min(100, round(100 - pen)))
    return {"yellow_avg": round(y_avg,2), "red_avg": round(r_avg,3), "fouls_avg": round(f_avg,1), "risk_score": score, "risk_label": "Faible" if score>=70 else "Élevé", "score": score}

def apply_live_correction(pre_score, live_data):
    if not live_data or not live_data.get("is_live"): return pre_score
    m, sh, sa = live_data.get("minute",0), live_data.get("score_home",0), live_data.get("score_away",0)
    rh, ra = live_data.get("red_cards_home",0), live_data.get("red_cards_away",0)
    w_live = min(0.9, m / 90)
    bias = 50 + (sh - sa)*10 if sh != sa else 50
    bias = max(5, min(95, bias - rh*15 + ra*15))
    adj = round(pre_score["confidence"] * (1 - w_live) + bias * w_live)
    return {**pre_score, "confidence": adj, "live_bias": bias, "minute": m, "corrected": True}

def calculate_global_confidence(scores):
    w_sum = sum(scores.get(k,50) * w for k,w in WEIGHTS.items())
    w_sum += (scores.get("chemistry",50) - 50)*0.05 - (100 - scores.get("missing",100))*0.10 - (100 - scores.get("fatigue",100))*0.05
    conf = max(0, min(96, round(w_sum)))
    lbl = "🟢 Confiance élevée" if conf>=75 else ("🟡 Confiance modérée" if conf>=55 else "🔴 Confiance faible")
    return {"confidence": conf, "label": lbl, "prediction": "Pari sûr" if conf>=75 else "Équilibré"}

def simulate_match(match):
    h_form, a_form = calculate_form([]), calculate_form([])
    h_rank = calculate_ranking(random.randint(1,20), 20, random.uniform(1.0,2.5), random.randint(-15,25))
    a_rank = calculate_ranking(random.randint(1,20), 20, random.uniform(1.0,2.5), random.randint(-15,25))
    h2h = calculate_h2h([])
    s_h, s_a = calculate_stakes(random.choice(["title_race","mid_table","european_qualification","relegation"])), calculate_stakes(random.choice(["title_race","mid_table","european_qualification","relegation"]))
    h_ha, a_ha = calculate_home_away(True, h_form["score"]/100, a_form["score"]/100), calculate_home_away(False, h_form["score"]/100, a_form["score"]/100)
    h_g, a_g = calculate_goals(random.uniform(1.0,2.5), random.uniform(0.5,2.0)), calculate_goals(random.uniform(0.8,2.2), random.uniform(0.8,2.0))
    h_m = calculate_momentum({"type": random.choice(["W","L","D"]), "count": random.randint(1,5)})
    a_m = calculate_momentum({"type": random.choice(["W","L","D"]), "count": random.randint(1,5)})
    ou = calculate_over_under_btts(h_g["goals_scored_avg"], a_g["goals_scored_avg"], h2h["avg_goals"])
    poi = calculate_poisson_distribution(h_g["goals_scored_avg"]*1.15, a_g["goals_scored_avg"]*0.90)
    h_chem, a_chem = calculate_chemistry(), calculate_chemistry()
    h_miss, a_miss = calculate_missing_impact([]), calculate_missing_impact([])
    h_fat, a_fat = calculate_fatigue(random.randint(2,8)), calculate_fatigue(random.randint(2,8))
    h_cs, a_cs = calculate_clean_sheet(random.randint(1,7), 10), calculate_clean_sheet(random.randint(1,7), 10)
    h_disc, a_disc = calculate_discipline(random.uniform(1.5,3.5), random.uniform(0.05,0.2), random.uniform(8,15)), calculate_discipline(random.uniform(1.5,3.5), random.uniform(0.05,0.2), random.uniform(8,15))

    h_scores = {"form": h_form["score"], "ranking": h_rank["score"], "h2h": h2h["score"], "stakes": s_h["score"], "home_away": h_ha["score"], "goals": h_g["score"], "momentum": h_m["score"], "chemistry": h_chem["score"], "missing": h_miss["score"], "fatigue": h_fat["score"]}
    a_scores = {"form": a_form["score"], "ranking": a_rank["score"], "h2h": 100 - h2h["score"], "stakes": s_a["score"], "home_away": a_ha["score"], "goals": a_g["score"], "momentum": a_m["score"], "chemistry": a_chem["score"], "missing": a_miss["score"], "fatigue": a_fat["score"]}

    h_glob, a_glob = calculate_global_confidence(h_scores), calculate_global_confidence(a_scores)
    diff = h_glob["confidence"] - a_glob["confidence"]

    if diff > 15: pred, pred_lbl, conf = "1", "Victoire Domicile", h_glob["confidence"]
    elif diff < -15: pred, pred_lbl, conf = "2", "Victoire Extérieur", a_glob["confidence"]
    else: pred, pred_lbl, conf = "N", "Match Nul probable", round((h_glob["confidence"]+a_glob["confidence"])/2)

    safety = "+2.5 Buts" if ou["over_25"]>65 else ("BTTS OUI" if ou["btts_yes"]>65 else ("1N (Double chance)" if poi["prob_1"]+poi["prob_N"]>75 else "-3.5 Buts"))

    if match.get("live_data") and match["live_data"].get("is_live"):
        h_glob = apply_live_correction(h_glob, match["live_data"])
        conf = h_glob["confidence"]

    return {
        "criteria": {
            "form": {"home": h_form, "away": a_form}, "ranking": {"home": h_rank, "away": a_rank}, "h2h": h2h,
            "stakes": {"home": s_h, "away": s_a}, "home_away": {"home": h_ha, "away": a_ha}, "goals": {"home": h_g, "away": a_g},
            "momentum": {"home": h_m, "away": a_m}, "over_under_btts": ou, "poisson": poi,
            "chemistry": {"home": h_chem, "away": a_chem}, "missing": {"home": h_miss, "away": a_miss},
            "fatigue": {"home": h_fat, "away": a_fat}, "clean_sheet": {"home": h_cs, "away": a_cs}, "discipline": {"home": h_disc, "away": a_disc}
        },
        "formations": {"home": random.choice(list(FORMATIONS.keys())), "away": random.choice(list(FORMATIONS.keys()))},
        "prediction": pred, "prediction_label": pred_lbl, "confidence": conf, "safety_bet": safety,
        "home_global_score": h_glob["confidence"], "away_global_score": a_glob["confidence"]
    }

def apply_rolling_window(matches, days_past=0, days_future=7):
    now = datetime.utcnow()
    cutoff_p, cutoff_f = now - timedelta(hours=2), now + timedelta(days=days_future)
    act, exp = [], []
    for m in matches:
        try: m_date = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")).replace(tzinfo=None)
        except: m_date = now
        st = m.get("status", "SCHEDULED")
        if (st == "FINISHED" and m_date < cutoff_p) or (m_date < now - timedelta(days=days_past) and st not in LIVE_STATUSES) or (m_date > cutoff_f):
            exp.append(m)
        else: act.append(m)
    act.sort(key=lambda x: x.get("utcDate", ""))
    return {"active_matches": act, "expired_matches": exp, "active_count": len(act), "expired_count": len(exp)}

def filter_team_collision(matches):
    busy_days = {}
    filtered = []
    for m in matches:
        try: d_key = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except: filtered.append(m); continue
        hid, aid = m.get("homeTeam",{}).get("id"), m.get("awayTeam",{}).get("id")
        if d_key not in busy_days: busy_days[d_key] = set()
        if hid in busy_days[d_key] or aid in busy_days[d_key]: continue
        busy_days[d_key].add(hid); busy_days[d_key].add(aid)
        filtered.append(m)
    return filtered

def enrich_match(match):
    if match.get("status") in LIVE_STATUSES:
        match["live_data"] = {"is_live": True, "minute": match.get("minute", random.randint(1,90)), "score_home": match.get("score",{}).get("fullTime",{}).get("home") or 0, "score_away": match.get("score",{}).get("fullTime",{}).get("away") or 0, "red_cards_home": random.randint(0,1), "red_cards_away": random.randint(0,1)}
    match["analysis"] = simulate_match(match)
    return match

def get_demo_competitions():
    return [
        {"code": "CL", "name": "UEFA Champions League", "emblem": "🏆", "continent": "Europe", "flag": "🇪🇺"},
        {"code": "PL", "name": "Premier League", "emblem": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "continent": "Europe", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
        {"code": "PD", "name": "LaLiga", "emblem": "🇪🇸", "continent": "Europe", "flag": "🇪🇸"},
        {"code": "FL1", "name": "Ligue 1", "emblem": "🇫🇷", "continent": "Europe", "flag": "🇫🇷"},
        {"code": "BL1", "name": "Bundesliga", "emblem": "🇩🇪", "continent": "Europe", "flag": "🇩🇪"},
        {"code": "SA", "name": "Serie A", "emblem": "🇮🇹", "continent": "Europe", "flag": "🇮🇹"},
        {"code": "CAN", "name": "Qualifications CAN", "emblem": "🌍", "continent": "Afrique", "flag": "🌍"},
        {"code": "CAF", "name": "CAF Champions League", "emblem": "🏆", "continent": "Afrique", "flag": "🌍"},
        {"code": "BOT", "name": "Botola Pro Maroc", "emblem": "🇲🇦", "continent": "Afrique", "flag": "🇲🇦"},
        {"code": "L1A", "name": "Ligue 1 Algérie", "emblem": "🇩🇿", "continent": "Afrique", "flag": "🇩🇿"},
        {"code": "COP", "name": "Copa Libertadores", "emblem": "🏆", "continent": "Amériques", "flag": "🌎"},
        {"code": "MLS", "name": "MLS USA", "emblem": "🇺🇸", "continent": "Amériques", "flag": "🇺🇸"},
        {"code": "SPL", "name": "Saudi Pro League", "emblem": "🇸🇦", "continent": "Asie", "flag": "🇸🇦"}
    ]

def get_demo_matches():
    now = datetime.utcnow()
    comps = get_demo_competitions()
    teams_map = {
        "PL": [("Arsenal","ARS"),("Liverpool","LIV"),("Man City","MCI"),("Chelsea","CHE")],
        "PD": [("Real Madrid","RMA"),("Barcelona","BAR"),("Atlético","ATM"),("Sevilla","SEV")],
        "FL1": [("PSG","PSG"),("Marseille","OM"),("Lyon","OL"),("Monaco","ASM")],
        "BL1": [("Bayern","BAY"),("Dortmund","BVB"),("Leipzig","RBL"),("Leverkusen","B04")],
        "SA": [("Juventus","JUV"),("Inter","INT"),("AC Milan","MIL"),("Napoli","NAP")],
        "CL": [("Real Madrid","RMA"),("Bayern","BAY"),("Man City","MCI"),("PSG","PSG")],
        "CAN": [("Sénégal","SEN"),("Maroc","MAR"),("Algérie","ALG"),("Côte d'Ivoire","CIV")],
        "BOT": [("Raja Casa","RAJ"),("Wydad","WAC"),("FAR","FAR"),("RSB","RSB")],
        "L1A": [("USM Alger","USMA"),("MC Alger","MCA"),("CR Belouizdad","CRB"),("JS Kabylie","JSK")],
        "COP": [("Flamengo","FLA"),("Palmeiras","PAL"),("Boca Juniors","BOC"),("River Plate","CARP")],
        "MLS": [("Inter Miami","MIA"),("LA Galaxy","LAG"),("Atlanta","ATL")],
        "SPL": [("Al Nassr","NAS"),("Al Hilal","HIL"),("Al Ittihad","ITT")]
    }
    matches = []
    m_id = 10000
    for c in comps:
        t_list = teams_map.get(c["code"], [("Équipe A","TA"), ("Équipe B","TB")])
        for i in range(min(2, len(t_list)//2)):
            t1, t2 = t_list[i*2], t_list[i*2+1]
            d_off, h_off = random.randint(0, 5), random.randint(-2, 20)
            m_date = now + timedelta(days=d_off, hours=h_off)
            st = "IN_PLAY" if h_off < 0 else ("SCHEDULED" if h_off > 2 else random.choice(["IN_PLAY","SCHEDULED"]))
            sh = random.randint(0,3) if st in LIVE_STATUSES else None
            sa = random.randint(0,3) if st in LIVE_STATUSES else None
            m = {
                "id": m_id, "competition": {"code": c["code"], "name": c["name"], "emblem": c["emblem"], "flag": c["flag"], "continent": c["continent"]},
                "homeTeam": {"id": m_id*2, "name": t1[0], "shortName": t1[1]}, "awayTeam": {"id": m_id*2+1, "name": t2[0], "shortName": t2[1]},
                "utcDate": m_date.isoformat()+"Z", "status": st, "matchday": random.randint(1,38),
                "score": {"fullTime": {"home": sh, "away": sa}}, "minute": random.randint(1,90) if st=="IN_PLAY" else None, "category": "Masculin"
            }
            matches.append(enrich_match(m))
            m_id += 1
    return matches