import psycopg2
from psycopg2 import extras
import datetime
import pytz
from decimal import Decimal, ROUND_HALF_UP

from st_common_data.nyse_holidays import NYSE_HOLIDAYS


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
    for holiday in NYSE_HOLIDAYS:
        if current_datetime.strftime("%d.%m.%Y") == holiday['date'] and (holiday['status'] == 'Closed'):
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


