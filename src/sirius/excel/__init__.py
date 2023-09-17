from typing import Any, Dict, List

import openpyxl
from _decimal import Decimal

from sirius.exceptions import SDKClientException


class NotAKeyValuePairException(SDKClientException):
    pass


def _get_cell_value_from_cell(cell_value: Any) -> Any:
    return Decimal(str(cell_value)) if isinstance(cell_value, (int, float)) and not isinstance(cell_value, bool) else cell_value


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
                excel_data[headers[cell_number]] = _get_cell_value_from_cell(cell.value)
                cell_number = cell_number + 1

            excel_data_list.append(excel_data)

        row_number = row_number + 1

    return excel_data_list


def get_key_value_pair(file_path: str, sheet_name: str) -> Dict[Any, Any]:
    workbook = openpyxl.load_workbook(filename=file_path, data_only=True)
    key_value_pair: Dict[Any, Any] = {}

    for row in workbook[sheet_name]:
        if len(row) != 2:
            raise NotAKeyValuePairException()

        key_value_pair[str(row[0].value)] = _get_cell_value_from_cell(row[1].value)

    return key_value_pair
