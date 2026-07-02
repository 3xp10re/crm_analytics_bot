import csv
from pathlib import Path

from database import get_connection, init_db

ALLOWED_STATUSES = {
    "new",
    "in_progress",
    "complete",
    "cancel",
}

def import_csv(file_path: str):
    pass