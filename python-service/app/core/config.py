import os
from dotenv import load_dotenv

# Load .env in local dev; in containers, env comes from compose
load_dotenv()

# LLM toggle
USE_LLM: bool = bool(os.getenv("OPENAI_API_KEY"))

# DB
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "dental_chatbot")

# Scheduler defaults
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "Dr. Bob Dentist")
DEFAULT_LOCATION = os.getenv("DEFAULT_LOCATION", "Downtown Dental Clinic")
DEFAULT_APPT_MIN = int(os.getenv("DEFAULT_APPT_MINUTES", "30"))
BUSINESS_START = os.getenv("BUSINESS_START", "09:00")  # HH:MM
BUSINESS_END = os.getenv("BUSINESS_END", "17:00")      # HH:MM
