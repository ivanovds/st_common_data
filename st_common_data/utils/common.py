import json
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta
from typing import Union, Callable
import datetime
import pytz
import logging
import time

import requests
import psycopg2
from psycopg2 import extras

from st_common_data.info.base import make_user_agent
from st_common_data.auth import ServiceAuth0Token


logger = logging.getLogger(__name__)


try:
    from app.settings import config
    from st_common_data.auth.fastapi_auth import service_auth0_token

    DATUM_API_URL = config.datum_api_url
except ImportError:
    try:
        from django.conf import settings
        from st_common_data.auth.django_auth import service_auth0_token

        DATUM_API_URL = settings.DATUM_API_URL
    except Exception:
        DATUM_API_URL = None


HOLIDAYS_LIST_CACHE = None


def http_request(
    method: str,
    url: str,
    bearer: str | ServiceAuth0Token | None = None,
    data: dict | None = None,
    params: dict | None = None,
    timeout: int = 30,
    retry: int = 0,
    retry_time: int = 10,
    error_msg_prefix: str | None = None,
    raw_data: bool = False,
    headers: dict | None = None,
    verify_sert: bool = True,
    proxies: dict | None = None,
    multipart_form_data: bool = False,
    msk_callback: Callable | None = None,
    log_errors: bool = True,
):
    variables = locals()

    if headers is None:
        headers = {'Authorization': f'Bearer {bearer}'}

    headers['User-Agent'] = make_user_agent()

    response = requests.request(
        method=method,
        url=url,
        json=data if not multipart_form_data else None,
        data=data if multipart_form_data else None,
        params=params,
        headers=headers,
        timeout=timeout,
        verify=verify_sert,
        proxies=proxies
    )

    if not response.ok:
        if retry:
            time.sleep(retry_time)
            variables['retry'] -= 1
            result = http_request(**variables)
        else:
            error_message = f'{url} returned with {response.status_code} status code, details:  {response.text}'
            # update message
            if error_msg_prefix:
                error_message = error_message + error_message

            if msk_callback:
                msk_callback(text=error_message)
            if log_errors:
                logger.error(error_message)
            response.raise_for_status()
    else:
        if raw_data:
            result = response.content
        else:
            try:
                result = response.json()
            except:
                result = None

    return result


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


def touch_db_with_connection(connection, query, params=None, save=False, returning=False,
                             transaction=False, dict_response: bool = True):
    try:
        with connection.cursor() as cursor:
            extras.register_default_jsonb(cursor.cursor, loads=json.loads)
            if not transaction:
                cursor.execute(query, params)
            else:
                for part in query:
                    cursor.execute(part)
            if save:
                connection.commit()
                if returning:
                    if dict_response:
                        columns = [col[0] for col in cursor.description]
                        return [dict(zip(columns, row)) for row in cursor.fetchall()]
                    else:
                        return cursor.fetchall()
                else:
                    return True
            else:
                if dict_response:
                    columns = [col[0] for col in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
                else:
                    return cursor.fetchall()
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
