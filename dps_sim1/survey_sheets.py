# dps_sim1/survey_sheets.py
import os
from functools import lru_cache
from typing import List, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

@lru_cache(maxsize=1)
def get_sheets_service():
    creds_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)

def append_row(spreadsheet_id: str, range_a1: str, row: List[Any]) -> None:
    svc = get_sheets_service()
    body = {"values": [row]}
    svc.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_a1,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()

