from datetime import datetime

from expenses.config import Settings
from expenses.core import process_update
from expenses.external.llm import build_client
from expenses.external.sheets.client import SheetsClient
from expenses.external.sheets.writer import SheetWriter
from expenses.external.telegram import TelegramClient
from expenses.state import load_state, save_state


def main() -> None:
    config = Settings()  # ty: ignore -- reads from .env at runtime
    telegram = TelegramClient(token=config.telegram_bot_token)
    llm_client = build_client(config=config)
    sheets_client = SheetsClient(credentials_path=config.credentials_path)
    sheet = SheetWriter(
        worksheet=sheets_client.worksheet(
            spreadsheet_id=config.google_spreadsheet_id,
            sheet_name=config.google_sheet_name,
        )
    )
    state = load_state()

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
    save_state(state=state)
    print(f"Processed {len(updates)} update(s).")


if __name__ == "__main__":
    main()
