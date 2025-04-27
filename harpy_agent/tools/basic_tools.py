import datetime
import pytz
import numexpr
from decimal import InvalidOperation
from dateutil import parser
from dateutil.relativedelta import relativedelta
import concurrent.futures
import logging
from config import Config

def get_current_time(time_zone: str = Config.TIMEZONE) -> str:
    """
    Gets the current time in the specified timezone. Defaults to UTC if not provided.

    Args:
        time_zone (str, optional): The IANA timezone name (e.g., 'America/New_York', 'UTC'). Defaults to "Asia/Manila".

    Returns:
        str: A string representing the current time in the format 'YYYY-MM-DD HH:MM:SS ZZZZ±HHMM', or an error message.
    """
    try:
        tz = pytz.timezone(time_zone)
        now = datetime.datetime.now(tz)
        return f"Current time ({time_zone}): {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"
    except pytz.UnknownTimeZoneError:
        return f"Error: Unknown timezone '{time_zone}'. Use IANA timezone names (e.g., 'America/New_York', 'UTC')."
    except Exception as e:
        return f"Error getting time: {e}"

def calculate(expression: str) -> str:
    """
    Calculates the result of a single mathematical expression.

    Uses the 'numexpr' library for safe evaluation of mathematical expressions.

    Args:
        expression (str): The mathematical expression to evaluate (e.g., "2 * (3 + 5)").

    Returns:
        str: A string containing the result of the calculation, or an error message.
    """    
    try:
        result = numexpr.evaluate(expression)
        return f"Result: {result.item() if hasattr(result, 'item') else result}"
    except Exception as e:
        return f"Error calculating expression: {e}"

def calculate_date(start_date_str: str, operation: str, duration_str: str) -> str:
    """
    Calculates a future or past date based on a start date and duration.

    Args:
        start_date_str (str): The starting date in a recognizable format (e.g., "2023-10-27", "10/27/2023").
        operation (str): The operation to perform: 'add' or 'subtract'.
        duration_str (str): The duration to add or subtract. Uses units like 'days', 'weeks', 'months', 'years' (e.g., '3 weeks', '1 month 5 days', '-2 years').

    Returns:
        str: A string describing the calculated date (e.g., "2023-10-27 plus 3 weeks is 2023-11-17"), or an error message.
    """
    try:
        # Parse the start date
        start_date = parser.parse(start_date_str).date()
        
        # Parse the duration string into a relativedelta object
        # Simple parsing, assumes units like days, weeks, months, years
        delta_args = {}
        parts = duration_str.lower().split()
        value = None
        for part in parts:
            try:
                value = int(part)
            except ValueError:
                unit = part.rstrip('s') # Remove plural 's'
                if value is not None:
                    if unit in ['day', 'days']: delta_args['days'] = value
                    elif unit in ['week', 'weeks']: delta_args['weeks'] = value
                    elif unit in ['month', 'months']: delta_args['months'] = value
                    elif unit in ['year', 'years']: delta_args['years'] = value
                    else: return f"Error: Unknown duration unit '{part}'. Use days, weeks, months, years."
                    value = None # Reset value after assigning
        
        if not delta_args:
            return "Error: Could not parse duration string. Example: '3 weeks 2 days'"

        delta = relativedelta(**delta_args)

        # Perform the operation
        if operation.lower() == 'add':
            result_date = start_date + delta
            op_str = "plus"
        elif operation.lower() == 'subtract':
            result_date = start_date - delta
            op_str = "minus"
        else:
            return "Error: Invalid operation. Use 'add' or 'subtract'."

        return f"{start_date_str} {op_str} {duration_str} is {result_date.strftime('%Y-%m-%d')}"
        
    except parser.ParserError:
        return f"Error: Could not parse start date '{start_date_str}'. Use a recognizable format (e.g., YYYY-MM-DD, MM/DD/YYYY)."
    except Exception as e:
        return f"Error calculating date: {e}"

def calculate_many(expressions: list[str]) -> list[str]:
    """
    Calculates the result of multiple mathematical expressions in parallel.

    Args:
        expressions (list[str]): A list of mathematical expressions to evaluate.

    Returns:
        list[str]: A list of strings containing the results of the calculations, 
                   or error messages for individual failures.
    """
    results = [None] * len(expressions) # Preallocate list for results in original order
    expression_map = {expr: i for i, expr in enumerate(expressions)} # Map expression to original index

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_expr = {executor.submit(calculate, expr): expr for expr in expressions}
        
        for future in concurrent.futures.as_completed(future_to_expr):
            expr = future_to_expr[future]
            original_index = expression_map[expr]
            try:
                result = future.result()
                results[original_index] = result
            except Exception as exc:
                logging.error(f'Expression "{expr}" generated an exception during calculation: {exc}', exc_info=True)
                results[original_index] = f"Error calculating expression '{expr}': {exc}"

    return results
