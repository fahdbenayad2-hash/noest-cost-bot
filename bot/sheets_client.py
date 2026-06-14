from __future__ import annotations

import json
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials

SHEET_NAME = "Calculations"

HEADERS = [
    "الوقت والتاريخ",
    "معرف المستخدم",
    "اسم الخياطة",
    "اسم المنتج",
    "تفاصيل القماش",
    "تفاصيل الأحجام",
    "تكلفة القماش",
    "تكلفة الخياطة",
    "تكلفة الإكسسوارات",
    "تكلفة التوصيل",
    "تكاليف إضافية",
    "التكلفة الكلية",
    "عدد القطع",
    "تكلفة القطعة",
]


class SheetsClient:
    """Client for saving and retrieving cost calculations from Google Sheets."""

    def __init__(self, credentials_path: str, spreadsheet_id: str) -> None:
        """Initialise the client with service-account credentials.

        Args:
            credentials_path: Path to the Google service account JSON file.
            spreadsheet_id: ID of the target Google Spreadsheet.
        """
        self.spreadsheet_id = spreadsheet_id
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
        self.client = gspread.authorize(creds)

    def _ensure_sheet(self) -> gspread.Worksheet:
        """Return the 'Calculations' worksheet, creating or updating headers to Arabic."""
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
        except Exception:
            return None
        try:
            ws = spreadsheet.worksheet(SHEET_NAME)
            current_headers = ws.row_values(1)
            if current_headers != HEADERS:
                cell_range = ws.range(f"A1:{chr(64 + len(HEADERS))}1")
                for i, cell in enumerate(cell_range):
                    if i < len(HEADERS):
                        cell.value = HEADERS[i]
                ws.update_cells(cell_range)
            return ws
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=len(HEADERS))
            ws.append_row(HEADERS, value_input_option="USER_ENTERED")
            return ws

    def save_calculation(
        self, user_id: int, tailor_name: str, product_name: str, result: dict, session: dict
    ) -> bool:
        """Append a single calculation row to the 'Calculations' sheet.

        Args:
            user_id: Telegram user ID.
            tailor_name: Name of the tailor.
            product_name: Name of the product.
            result: Output of cost_calculator.calculate().
            session: The full user_data session (for fabric_batches / sizes).

        Returns:
            True on success, False on failure.
        """
        try:
            ws = self._ensure_sheet()
            if ws is None:
                return False

            fabric_batches_ar = [
                {"اللون": b["color"], "الطول": b["meters"], "السعر_للمتر": b["price_per_meter"]}
                for b in session.get("fabric_batches", [])
            ]
            sizes_ar = [
                {"الحجم": s["label"], "الكمية": s["quantity"]}
                for s in session.get("sizes", [])
            ]

            row = [
                datetime.now(timezone.utc).isoformat(),
                user_id,
                tailor_name,
                product_name,
                json.dumps(fabric_batches_ar, ensure_ascii=False),
                json.dumps(sizes_ar, ensure_ascii=False),
                result["fabric_cost"],
                result["sewing_cost"],
                result["accessories_cost"],
                result["delivery_cost"],
                result["additional_costs"],
                result["total_cost"],
                result["total_units"],
                result["unit_cost"],
            ]
            ws.append_row(row, value_input_option="USER_ENTERED")
            return True
        except Exception:
            return False

    def get_history(self, user_id: int, limit: int = 10) -> list[dict]:
        """Return the last *limit* calculations for a given user.

        Args:
            user_id: Telegram user ID to filter by.
            limit: Maximum number of rows to return.

        Returns:
            List of dicts (keys = HEADERS) or [] on failure / no data.
        """
        try:
            ws = self._ensure_sheet()
            if ws is None:
                return []
            all_rows = ws.get_all_values()
            if len(all_rows) <= 1:
                return []
            header = all_rows[0]
            matching = []
            for row in all_rows[1:]:
                if len(row) > 1 and row[1] == str(user_id):
                    matching.append(dict(zip(header, row)))
            return matching[-limit:]
        except Exception:
            return []
