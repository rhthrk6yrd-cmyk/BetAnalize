# config.py
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration centrale de l'application."""

    # Clé secrète Flask (sessions, CSRF)
    SECRET_KEY = os.getenv("SECRET_KEY", "betanalyzer-secret-key-change-me")

    # API Football Data (gratuit : https://www.football-data.org/)
    FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")

    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    MINI_APP_URL = os.getenv("MINI_APP_URL", "https://your-app.onrender.com")

    # Mode démo automatique si pas de clé API
    @property
    def IS_DEMO(self):
        return not bool(self.FOOTBALL_DATA_API_KEY)

    # Fenêtre glissante (jours)
    SLIDING_WINDOW_DAYS = 3

    # Intervalle de rafraîchissement (secondes)
    REFRESH_INTERVAL = 60

    # URL API Football Data
    FOOTBALL_API_BASE = "https://api.football-data.org/v4"


config = Config()