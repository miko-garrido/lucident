import pytest
from harpy_agent.tools import basic_tools
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from unittest.mock import patch, MagicMock

# --- Test get_current_time ---

def test_get_current_time_utc():
    result = basic_tools.get_current_time()
    assert "UTC" in result
    # Basic check for format, actual time will vary
    assert ":" in result 
    assert "-" in result

def test_get_current_time_specific_tz():
    result = basic_tools.get_current_time('America/New_York')
    assert "America/New_York" in result or "EDT" in result or "EST" in result # Account for DST
    assert ":" in result
    assert "-" in result

def test_get_current_time_invalid_tz():
    result = basic_tools.get_current_time('Invalid/Timezone')
    assert "Error: Unknown timezone 'Invalid/Timezone'" in result

# --- Test calculate ---

def test_calculate_simple_addition():
    assert basic_tools.calculate("2 + 2") == "Result: 4"

def test_calculate_complex_expression():
    assert basic_tools.calculate("(5 * 3) / (2 + 1)") == "Result: 5.0"

def test_calculate_invalid_expression():
    result = basic_tools.calculate("2 +")
    assert "Error calculating expression:" in result

def test_calculate_division_by_zero():
    # numexpr handles division by zero, often resulting in inf
    result = basic_tools.calculate("1 / 0")
    # Update assertion to check for the actual error message
    assert "Error calculating expression: division by zero" in result

# --- Test calculate_date ---

def test_calculate_date_add_days():
    start = "2024-01-10"
    duration = "5 days"
    expected_date = "2024-01-15"
    result = basic_tools.calculate_date(start, "add", duration)
    assert f"{start} plus {duration} is {expected_date}" == result

def test_calculate_date_subtract_weeks():
    start = "2024-03-01"
    duration = "2 weeks"
    expected_date = "2024-02-16"
    result = basic_tools.calculate_date(start, "subtract", duration)
    assert f"{start} minus {duration} is {expected_date}" == result

def test_calculate_date_add_months_and_days():
    start = "2024-05-20"
    duration = "1 month 3 days"
    expected_date = "2024-06-23"
    result = basic_tools.calculate_date(start, "add", duration)
    assert f"{start} plus {duration} is {expected_date}" == result
    
def test_calculate_date_subtract_years():
    start = "2025-07-15"
    duration = "1 year"
    expected_date = "2024-07-15"
    result = basic_tools.calculate_date(start, "subtract", duration)
    assert f"{start} minus {duration} is {expected_date}" == result

def test_calculate_date_invalid_start_date():
    result = basic_tools.calculate_date("Invalid Date", "add", "1 day")
    assert "Error: Could not parse start date 'Invalid Date'" in result

def test_calculate_date_invalid_operation():
    result = basic_tools.calculate_date("2024-01-01", "multiply", "1 day")
    assert "Error: Invalid operation. Use 'add' or 'subtract'." in result

def test_calculate_date_invalid_duration_unit():
    result = basic_tools.calculate_date("2024-01-01", "add", "3 fortnights")
    assert "Error: Unknown duration unit 'fortnights'" in result
    
def test_calculate_date_unparsable_duration():
    result = basic_tools.calculate_date("2024-01-01", "add", "three days")
    assert "Error: Could not parse duration string." in result # Because 'three' is not int 