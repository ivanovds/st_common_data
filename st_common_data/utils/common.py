import psycopg2
from psycopg2 import extras
import datetime
import pytz
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta
from typing import Union


try:
    from app.settings import config
    from st_common_data.auth.fastapi_auth import service_auth0_token
    DATUM_API_URL = config.datum_api_url
except Exception as e:
    try:
        from django.conf import settings
        from st_common_data.auth.django_auth import service_auth0_token
        DATUM_API_URL = settings.DATUM_API_URL
    except Exception:
        pass


HOLIDAYS_LIST_CACHE = None


def touch_db(query, dbp, params=None, save=False, returning=False, transaction=False):
    try:
        with psycopg2.connect(dbp) as conn:
            with conn.cursor() as cur:
                if not transaction:
                    cur.execute(query, params)
                else:
                    for part in query:
                        cur.execute(part)
                if save:
                    conn.commit()
                    if returning:
                        return cur.fetchall()
                    else:
                        return True
                else:
                    return cur.fetchall()
    except psycopg2.Error as err:
        raise Exception(f'ERR touch_db: {str(err)}')


def touch_db_with_dict_response(query, dbp, params=None, save=False, returning=False,
                                transaction=False):
    try:
        with psycopg2.connect(dbp) as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                if not transaction:
                    cur.execute(query, params)
                else:
                    for part in query:
                        cur.execute(part)
                if save:
                    conn.commit()
                    if returning:
                        return cur.fetchall()
                    else:
                        return True
                else:
                    return cur.fetchall()
    except psycopg2.Error as err:
        raise Exception(f'ERR touch_db_with_dict_response: {str(err)}')


def get_current_datetime():
    return datetime.datetime.now(pytz.timezone('UTC')).replace(microsecond=0, tzinfo=None)


def get_current_datetime_with_tz():
    return datetime.datetime.now(pytz.timezone('UTC'))


def get_current_eastern_datetime():
    return datetime.datetime.now(pytz.timezone('US/Eastern'))


def get_current_kyiv_datetime():
    return datetime.datetime.now(pytz.timezone('Europe/Kiev'))


def is_holiday(current_datetime):
    global HOLIDAYS_LIST_CACHE
    date_str = str(current_datetime.date())
    if not HOLIDAYS_LIST_CACHE:
        from st_common_data.datum import api_get_holidays
        HOLIDAYS_LIST_CACHE = api_get_holidays(
                datum_api_url=DATUM_API_URL,
                service_auth0_token=service_auth0_token,
                gte_date='2018-01-01',
                lte_date=str((datetime.datetime.now() + relativedelta(years=2)).date())
        )
    for row in HOLIDAYS_LIST_CACHE:
        if date_str == row['holiday_date']:
            return True
    return False


def is_working_day(current_date=None):
    if current_date is None:
        current_date = get_current_datetime().date()
    current_datetime = datetime.datetime.combine(current_date, datetime.time.min)

    if is_holiday(current_datetime) or (current_datetime.weekday() in [5, 6]):
        return False
    else:
        return True


def get_previous_workday(current_date=None):
    if current_date is None:
        current_date = get_current_datetime().date()
    current_datetime = datetime.datetime.combine(current_date, datetime.time.min)
    # We are expecting a not more than 20 holidays (to prevent infinite loop)
    for i in range(0, 20):
        current_datetime = current_datetime - datetime.timedelta(days=1)
        if is_holiday(current_datetime) or (current_datetime.weekday() in [5, 6]):
            continue
        else:
            return current_datetime.date()
    return False


def get_next_workday(current_date=None):
    if current_date is None:
        current_date = get_current_datetime().date()
    current_datetime = datetime.datetime.combine(current_date, datetime.time.min)
    # We are expecting a not more than 20 holidays (to prevent infinite loop)
    for i in range(0, 20):
        current_datetime = current_datetime + datetime.timedelta(days=1)
        if is_holiday(current_datetime) or (current_datetime.weekday() in [5, 6]):
            continue
        else:
            return current_datetime.date()

    return False


def round_half_up(n):
    return int(Decimal(n).quantize(0, rounding=ROUND_HALF_UP))


def round_half_up_decimal(num, decimal_places=4):
    r_number = '1.'
    for i in range(decimal_places):
        r_number += '0'

    return Decimal(num).quantize(Decimal(r_number), rounding=ROUND_HALF_UP)


def round_or_zero(num):
    if num:
        return round_half_up(num)
    else:
        return 0


def convert_dict_keys_to_str(param_dict):
    return {str(k): v for k, v in param_dict.items()}


def safe_divide(
        a: Union[None, int, float, Decimal],
        b: Union[None, int, float, Decimal]
) -> Union[int, float, Decimal]:
    """
    Safe division of two numbers for preventing ZeroDivisionError and NoneType values

    :param a: dividend
    :param b: divisor
    :return:
    """
    if any([a is None, b is None, b == 0]):
        return 0
    else:
        return a / b


def safe_add(*args):
    all_none = True
    result = 0
    for arg in args:
        if arg is not None:
            all_none = False
            result += arg
    if all_none:
        return None
    else:
        return result


def safe_subtract(*args):
    all_none = True
    result = 0
    for arg in args:
        if arg is not None:
            all_none = False
            result -= arg
    if all_none:
        return None
    else:
        return result


def get_last_thanksgiving_day():
    """Fourth Thursday of November"""
    month = 11
    now = get_current_datetime()

    # check current year:
    cur_year = now.year
    cur_year_thanksgiving_day = get_fourth_thursday(cur_year, month)

    if cur_year_thanksgiving_day <= now.date():
        return cur_year_thanksgiving_day
    else:
        return get_fourth_thursday(cur_year - 1, month)


def get_previous_thanksgiving_day(rating_year=None):
    """Fourth Thursday of November (year before rating_year)"""
    if not rating_year:
        rating_year = get_current_datetime().year

    return get_fourth_thursday(rating_year - 1, 11)


def get_fourth_thursday(year, month):
    first_day = datetime.date(year, month, 1)

    # go forward to the first Thursday
    offset = 4 - first_day.isoweekday()
    if offset < 0:
        offset += 7  # go forward one week if necessary

    return first_day + datetime.timedelta(days=offset) + datetime.timedelta(days=21)
