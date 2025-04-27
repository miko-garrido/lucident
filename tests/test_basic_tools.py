import pytest
import pytz
from harpy_agent.tools import basic_tools
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from unittest.mock import patch, MagicMock
from config import Config

# --- Test get_current_time ---

def test_get_current_time_asia_manila():
    result = basic_tools.get_current_time()
    assert "Asia/Manila" in result
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

def test_calculate_one_simple_addition():
    assert basic_tools.calculate_one("2 + 2") == "Result: 4"

def test_calculate_one_complex_expression():
    assert basic_tools.calculate_one("(5 * 3) / (2 + 1)") == "Result: 5.0"

def test_calculate_one_invalid_expression():
    result = basic_tools.calculate_one("2 +")
    assert "Error calculating expression:" in result

def test_calculate_one_division_by_zero():
    # numexpr handles division by zero, often resulting in inf
    result = basic_tools.calculate_one("1 / 0")
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

# --- Test calculate_many ---

def test_calculate_success():
    expressions = ["1 + 1", "10 / 2", "(2+3)*4"]
    expected = ["Result: 2", "Result: 5.0", "Result: 20"]
    assert basic_tools.calculate(expressions) == expected

def test_calculate_with_errors():
    expressions = ["2 * 5", "1 / 0", "3 + "]
    results = basic_tools.calculate(expressions)
    assert results[0] == "Result: 10"
    assert "Error calculating expression: division by zero" in results[1]
    assert "Error calculating expression: invalid syntax" in results[2]

def test_calculate_empty_list():
    expressions = []
    expected = []
    assert basic_tools.calculate(expressions) == expected

def test_calculate_mixed():
    expressions = ["sqrt(16)", "5 - ", "2**3"]
    results = basic_tools.calculate(expressions)
    assert results[0] == "Result: 4.0"
    assert "Error calculating expression: invalid syntax" in results[1]
    assert results[2] == "Result: 8" 

# --- Test calculate_unix_ms_timestamp ---

def test_calculate_unix_ms_timestamp_valid_ny():
    date_str = "2023-10-27 10:00:00"
    tz_str = "America/New_York"
    # Expected timestamp for 2023-10-27 10:00:00 EDT (UTC-4)
    expected_ts = 1698415200000
    result = basic_tools.calculate_unix_ms_timestamp(date_str, tz_str)
    assert f"Unix timestamp in milliseconds for {date_str} ({tz_str}): {expected_ts}" == result

def test_calculate_unix_ms_timestamp_valid_utc():
    date_str = "2023-10-27 14:00:00"
    tz_str = "UTC"
    # Expected timestamp for 2023-10-27 14:00:00 UTC
    expected_ts = 1698415200000
    result = basic_tools.calculate_unix_ms_timestamp(date_str, tz_str)
    assert f"Unix timestamp in milliseconds for {date_str} ({tz_str}): {expected_ts}" == result

def test_calculate_unix_ms_timestamp_just_date():
    # Assumes midnight if time is not provided
    date_str = "2024-01-15"
    tz_str = "Asia/Manila" # UTC+8
    # Expected timestamp for 2024-01-15 00:00:00 PHT (UTC+8)
    expected_ts = 1705248000000
    result = basic_tools.calculate_unix_ms_timestamp(date_str, tz_str)
    assert f"Unix timestamp in milliseconds for {date_str} ({tz_str}): {expected_ts}" == result

def test_calculate_unix_ms_timestamp_invalid_date():
    date_str = "Invalid Date String"
    tz_str = "UTC"
    result = basic_tools.calculate_unix_ms_timestamp(date_str, tz_str)
    assert f"Error: Could not parse date string '{date_str}'." in result

def test_calculate_unix_ms_timestamp_invalid_timezone():
    date_str = "2023-10-27 10:00:00"
    tz_str = "Invalid/Timezone"
    result = basic_tools.calculate_unix_ms_timestamp(date_str, tz_str)
    assert f"Error: Unknown timezone '{tz_str}'." in result

# --- Test convert_ms_to_hhmmss ---

def test_convert_ms_to_hhmmss_zero():
    assert basic_tools.convert_ms_to_hhmmss(0) == "0:00:00"

def test_convert_ms_to_hhmmss_less_than_second():
    assert basic_tools.convert_ms_to_hhmmss(500) == "0:00:00"

def test_convert_ms_to_hhmmss_seconds():
    assert basic_tools.convert_ms_to_hhmmss(5000) == "0:00:05"
    assert basic_tools.convert_ms_to_hhmmss(59999) == "0:00:59"

def test_convert_ms_to_hhmmss_minutes_seconds():
    assert basic_tools.convert_ms_to_hhmmss(65000) == "0:01:05" # 1 min 5 sec
    assert basic_tools.convert_ms_to_hhmmss(3599000) == "0:59:59" # 59 min 59 sec

def test_convert_ms_to_hhmmss_hours_minutes_seconds():
    assert basic_tools.convert_ms_to_hhmmss(3600000) == "1:00:00" # 1 hour
    assert basic_tools.convert_ms_to_hhmmss(3661000) == "1:01:01" # 1 hour 1 min 1 sec
    assert basic_tools.convert_ms_to_hhmmss(86399000) == "23:59:59" # 23 hours 59 min 59 sec

def test_convert_ms_to_hhmmss_multiple_hours():
    assert basic_tools.convert_ms_to_hhmmss(90000000) == "25:00:00" # 25 hours