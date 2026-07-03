import json
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


class SheetsClient:
    def __init__(self, credentials_json: str, spreadsheet_id: str) -> None:
        info: dict[str, Any] = json.loads(credentials_json)
        creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
        client = gspread.authorize(creds)
        self._spreadsheet = client.open_by_key(spreadsheet_id)

    def get_or_create_worksheet(
        self,
        title: str,
        rows: int = 100,
        cols: int = 10,
    ) -> gspread.Worksheet:
        try:
            return self._spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            return self._spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)
