import datetime
from typing import List, Dict, Any

from _decimal import Decimal

from sirius import excel


def test_excel_read() -> None:
    excel_data_list: List[Dict[Any, Any]] = excel.get_excel_data("test_excel.xlsx", "Sheet1")

    assert len(excel_data_list) == 2
    assert excel_data_list[0]["Text"] == "ABCD"
    assert excel_data_list[0]["Date"].date() == datetime.datetime.today().date()
    assert isinstance(excel_data_list[0]["Date time"], datetime.datetime)
    assert isinstance(excel_data_list[0]["Time"], datetime.time)
    assert excel_data_list[0]["Number"] == Decimal("3")
    assert excel_data_list[0]["Decimal"] == Decimal("3.1")
    assert isinstance(excel_data_list[0]["Boolean"], bool)
    assert excel_data_list[0]["Percentage"] == Decimal("0.2")
