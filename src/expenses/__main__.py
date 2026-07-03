from datetime import datetime

from expenses.config import Settings
from expenses.core import process_update
from expenses.external.llm import build_client
from expenses.external.sheets.adapter import SheetAdapter
from expenses.external.sheets.client import SheetsClient
from expenses.external.telegram import TelegramClient


def main() -> None:
    config = Settings()  # ty: ignore -- reads from .env at runtime
    telegram = TelegramClient(token=config.telegram_bot_token)
    llm_client = build_client(config=config)

    sheets_client = SheetsClient(
        credentials_json=config.google_credentials_json,
        spreadsheet_id=config.google_spreadsheet_id,
    )
    sheet = SheetAdapter.open(
        client=sheets_client,
        expenses_sheet_name=config.google_sheet_name,
        state_sheet_name=config.state_sheet_name,
    )

    state = sheet.load_state()
    offset = state.last_update_id + 1 if state.last_update_id > 0 else None
    updates = telegram.get_updates(offset=offset)

    if not updates:
        print("No new messages.")
        return

    for update in updates:
        process_update(
            update,
            telegram=telegram,
            client=llm_client,
            sheet=sheet,
            config=config,
        )
        state.last_update_id = update["update_id"]

    state.last_run = datetime.now()
    sheet.save_state(state=state)
    print(f"Processed {len(updates)} update(s).")


if __name__ == "__main__":
    main()
