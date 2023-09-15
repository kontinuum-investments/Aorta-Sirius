from typing import Any, Dict, List

import openpyxl
from _decimal import Decimal


def get_excel_data(file_path: str, sheet_name: str) -> List[Dict[Any, Any]]:
    workbook = openpyxl.load_workbook(filename=file_path, data_only=True)
    excel_data_list: List[Dict[Any, Any]] = []
    headers: List[Any] = []

    row_number: int = 0
    for row in workbook[sheet_name]:
        if row_number == 0:
            headers = [cell.value for cell in row]

        else:
            excel_data: Dict[Any, Any] = {}
            cell_number: int = 0
            for cell in row:
                excel_data[headers[cell_number]] = Decimal(str(cell.value)) if isinstance(cell.value, (int, float)) and not isinstance(cell.value, bool) else cell.value
                cell_number = cell_number + 1

            excel_data_list.append(excel_data)

        row_number = row_number + 1

    return excel_data_list
