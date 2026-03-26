import os
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "flights.db")
JOBS_PATH = os.path.join(os.path.dirname(__file__), "data", "jobs.json")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
