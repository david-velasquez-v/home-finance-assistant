from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


class SheetsClient:
    def __init__(self, credentials_path: Path) -> None:
        creds = Credentials.from_service_account_file(str(credentials_path), scopes=_SCOPES)
        self._client = gspread.authorize(creds)

    def worksheet(self, spreadsheet_id: str, sheet_name: str) -> gspread.Worksheet:
        return self._client.open_by_key(spreadsheet_id).worksheet(sheet_name)
