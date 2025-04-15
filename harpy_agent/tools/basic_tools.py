import datetime
import pytz
import numexpr
from forex_python.converter import CurrencyRates, RatesNotAvailableError
from decimal import Decimal, InvalidOperation
from dateutil import parser
from dateutil.relativedelta import relativedelta

def get_current_time(time_zone: str = 'UTC') -> str:
    """Gets the current time in the specified timezone (default UTC). Uses IANA timezone names (e.g., 'America/New_York')."""
    try:
        tz = pytz.timezone(time_zone)
        now = datetime.datetime.now(tz)
        return f"Current time ({time_zone}): {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"
    except pytz.UnknownTimeZoneError:
        return f"Error: Unknown timezone '{time_zone}'. Use IANA timezone names (e.g., 'America/New_York', 'UTC')."
    except Exception as e:
        return f"Error getting time: {e}"

def calculate(expression: str) -> str:
    """Calculates the result of a mathematical expression using numexpr for safety."""    
    try:
        result = numexpr.evaluate(expression)
        return f"Result: {result.item() if hasattr(result, 'item') else result}"
    except Exception as e:
        return f"Error calculating expression: {e}"

def convert_currency(amount_str: str, from_currency: str, to_currency: str) -> str:
    """Converts an amount from one currency to another using current exchange rates."""
    try:
        # Instantiate CurrencyRates within the function for modularity
        c = CurrencyRates()
        amount = Decimal(amount_str)
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        converted_amount = c.convert(from_currency, to_currency, amount)
        # Format to 2 decimal places, common for currency
        formatted_amount = f"{converted_amount:.2f}"
        return f"{amount_str} {from_currency} is approximately {formatted_amount} {to_currency}"
    except InvalidOperation:
         return f"Error: Invalid amount '{amount_str}'. Please provide a valid number."
    except RatesNotAvailableError:
        return f"Error: Currency rates not available for {from_currency} or {to_currency}. Check currency codes."
    except Exception as e:
        return f"Error converting currency: {e}"

def calculate_date(start_date_str: str, operation: str, duration_str: str) -> str:
    """Calculates a future or past date based on a start date and duration.
       Duration examples: '3 days', '2 weeks', '1 month 5 days', '-1 year'
       Operation: 'add' or 'subtract'.
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
