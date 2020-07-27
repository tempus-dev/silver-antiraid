import os

from dotenv import load_dotenv

# Load env from .env if possible.
if os.environ.get("MODE") != "production":
    load_dotenv(verbose=True)

TOKEN = os.environ.get("TOKEN")
DATABASE_URI = os.environ.get("DATABASE_URI")
LOG_LEVEL = os.environ.get("LOG_LEVEL")
MAINTAINERS = os.environ.get("MAINTAINERS").split(",")
