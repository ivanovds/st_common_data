import logging
from decimal import Decimal
from typing import Union, List, Dict
import datetime
from collections import defaultdict

from st_common_data.utils import common


logger = logging.getLogger(__name__)


# --------------------- Queries to Datum API: ---------------------
def datum_api_get_request(url: str,
                          service_auth0_token: str,
                          params: dict = None,
                          body_params: dict = None):
    """
    Return:
     - json response from Datum API if success
     - raise Exception if error

    Args:
        url (str): url of Datum API
        service_auth0_token (str): auth0 token of service
        params (dict): query params
        body_params (dict): body params
    """

    return common.http_request(
        method='get',
        url=url,
        bearer=service_auth0_token,
        params=params,
        data=body_params
    )


def processing_list_of_dicts(list_of_dicts: List[Dict], key: str, keys_to_replace: dict = None) -> Dict[str, Dict]:
    """
        Convert list of dicts to dict of dicts by custom key
       Args:
           list_of_dicts (list): list of dicts
           key (str): custom(target) key
           keys_to_replace (dict)
       """
    result = {}
    for row_dict in list_of_dicts:
        ticker_name = row_dict.pop(key)
        if keys_to_replace:
            for old_key, new_key in keys_to_replace.items():
                row_dict[new_key] = row_dict.pop(old_key)

        result[ticker_name] = row_dict

    return result


def api_get_last_n_candles_by_ticker(datum_api_url: str,
                                     service_auth0_token: str,
                                     ticker: str,
                                     n_candles: int,
                                     interval: int = 5,
                                     unix_timestamp: int = None,
                                     **kwargs
                                     ) -> List[dict]:
    params = {
        'ticker': ticker,
        'interval': interval,
        'n_candles': n_candles,
        'unix_timestamp': unix_timestamp,
        **kwargs
    }

    list_of_dicts = datum_api_get_request(
        url=f'{datum_api_url}/intraday/last_n_candles',
        service_auth0_token=service_auth0_token,
        params=params
    )

    return list_of_dicts


def api_get_reports(datum_api_url: str,
                    move_date_str: str,
                    service_auth0_token: str,
                    **kwargs) -> List[str]:
    """Return list of tickers which have report event as of move_date_str"""
    list_of_dicts = datum_api_get_request(
        url=f'{datum_api_url}/reports',
        service_auth0_token=service_auth0_token,
        params={'move_date_str': move_date_str, **kwargs}
    )

    tickers_list = [row['ticker'] for row in list_of_dicts]
    return tickers_list


def api_get_splits(datum_api_url: str,
                   review_date_str: Union[datetime.date, str],
                   service_auth0_token: str,
                   **kwargs
                   ) -> dict:
    """Return dict of {str: decimal}"""
    list_of_dicts = datum_api_get_request(
        url=f'{datum_api_url}/dvd/splits',
        service_auth0_token=service_auth0_token,
        params={'date': review_date_str, **kwargs}
    )

    return {
        row['ticker']: Decimal(row['amount']) for row in list_of_dicts
    }


def api_get_dividends(datum_api_url: str,
                      review_date_str: Union[datetime.date, str],
                      service_auth0_token: str,
                      dvd_type: str = 'cash',
                      **kwargs
                      ) -> dict:
    """Return dict of {str: decimal}"""

    if dvd_type == 'cash':
        url_end = 'dvd/cash_dividends'
    elif dvd_type == 'stock':
        url_end = 'dvd/stock_dividends'
    else:
        raise Exception(f'Unknown dvd_type: {dvd_type}')

    list_of_dicts = datum_api_get_request(
        url=f'{datum_api_url}/{url_end}',
        service_auth0_token=service_auth0_token,
        params={'date': review_date_str, **kwargs}
    )

    return {
        row['ticker']: Decimal(row['amount']) for row in list_of_dicts
    }


def api_get_adv(datum_api_url: str,
                service_auth0_token: str,
                date_as_of: Union[str, datetime.date] = None) -> dict:
    """Return dict of {str: decimal}"""
    if not date_as_of:
        date_as_of = common.get_current_datetime().date()

    if not common.is_working_day(date_as_of):
        date_as_of = common.get_previous_workday(date_as_of)

    list_of_dicts = datum_api_get_request(
        url=f'{datum_api_url}/calculations/avg_daily_volume_90d',
        service_auth0_token=service_auth0_token,
        params={'date_as_of': date_as_of}
    )

    return {row['ticker']: row['value'] for row in list_of_dicts}


def api_get_close_price(datum_api_url: str,
                        service_auth0_token: str,
                        date: Union[str, datetime.date] = None,
                        ticker: str = None,
                        **kwargs) -> dict:
    if not date:
        date = common.get_previous_workday()

    params = {'start_date': date, 'end_date': date, 'chart_type': 'ohlc', **kwargs}
    if ticker:
        params['ticker'] = ticker

    list_of_dicts = datum_api_get_request(
        url=f'{datum_api_url}/daily',
        service_auth0_token=service_auth0_token,
        params=params
    )

    if ticker:
        return {ticker: list_of_dicts[0]['c']}
    else:
        return {row['ticker']: row['c'] for row in list_of_dicts}


def api_get_tickers_sector(datum_api_url: str,
                           service_auth0_token: str,
                           tickers: List[str],
                           **kwargs) -> dict:
    list_of_dicts = datum_api_get_request(
        url=f'{datum_api_url}/bics_sectors',
        service_auth0_token=service_auth0_token,
        body_params={'tickers': tickers, **kwargs}
    )

    return {row['ticker']: row['lvl3'] for row in list_of_dicts}


def api_get_avg_pre_mh_vol(datum_api_url: str,
                           service_auth0_token: str,
                           date: datetime.date = None,
                           **kwargs) -> dict:
    if not date:
        date = common.get_current_datetime().date()

    list_of_dicts = datum_api_get_request(
        url=f'{datum_api_url}/calculations/avg_premarket_volume_90d',
        service_auth0_token=service_auth0_token,
        params={'date_as_of': date, **kwargs}
    )
    return {row['ticker']: row['value'] for row in list_of_dicts}


def api_get_pre_mh_volume(datum_api_url: str,
                          service_auth0_token: str,
                          date: datetime.date = None,
                          **kwargs) -> dict:
    if not date:
        date = common.get_previous_workday()

    list_of_dicts = datum_api_get_request(
        url=f'{datum_api_url}/daily/pre_mh_volume',
        service_auth0_token=service_auth0_token,
        params={'start_date': date, 'end_date': date, **kwargs}
    )
    return {row['t']: row['pre_v'] for row in list_of_dicts}


def api_get_tickers_general_data(datum_api_url: str,
                                 service_auth0_token: str,
                                 is_active: bool = False,
                                 is_country_hq: bool = True,
                                 is_equity_type: bool = False,
                                 is_lvl1: bool = False,
                                 is_lvl2: bool = False,
                                 is_lvl3: bool = False,
                                 is_lvl4: bool = False,
                                 is_lvl5: bool = False,
                                 is_exchange: bool = False,
                                 **kwargs) -> Dict[str, Dict]:
    """
        Return dict of tickers with their selected data
        Args:
            datum_api_url str: host name of Datum API
            service_auth0_token str: auth0 serve token
            is_active bool: is ticker activity will be in result
            is_country bool: is country of ticker will be in result
            is_equity_type bool: is equity_type of ticker will be in result
            is_lvl1 bool: is this level will be in result
            is_lvl2 bool: is this level will be in result
            is_lvl3 bool: is this level will be in result
            is_lvl4 bool: is this level will be in result
            is_lvl5 bool: is this level will be in result
            is_exchange bool: is exchange of ticker will be in result
        Returns:
            example:
                {'AAPL': {'country': 'USA', 'lvl1': 'Banking'}}
    """
    locals_variables = locals()

    keys_to_replace = {
        'country_hq': 'country'  # change "country_hq" to "country"
    }

    active_params_list = []
    for param, value in locals_variables.items():
        try:
            field = param.split('is_')[1]
            if value:
                active_params_list.append(field)
        except IndexError:
            pass

    response = datum_api_get_request(
        url=f'{datum_api_url}/tickers',
        service_auth0_token=service_auth0_token,
        params={'only_active': False, 'fields': ','.join(active_params_list), **kwargs}
    )

    return processing_list_of_dicts(response, key='ticker', keys_to_replace=keys_to_replace)


def api_get_country_list(datum_api_url: str,
                         service_auth0_token: str,
                         **kwargs) -> List[str]:
    tickers_data = datum_api_get_request(
        url=f'{datum_api_url}/tickers',
        service_auth0_token=service_auth0_token,
        params={'fields': 'country_hq', **kwargs}
    )
    unique_countries = set([row['country_hq'] for row in tickers_data])
    return list(unique_countries)


def api_get_atr(datum_api_url: str,
                service_auth0_token: str,
                date: datetime.date = None,
                **kwargs) -> Dict[str, float]:
    if not date:
        date = common.get_current_datetime().date()

    list_of_dicts = datum_api_get_request(
        url=f'{datum_api_url}/calculations/avg_true_range_14d',
        service_auth0_token=service_auth0_token,
        params={'date_as_of': date, **kwargs}
    )

    return {row['ticker_by_esignal']: row['round'] for row in list_of_dicts}


def api_get_etf_tickers(datum_api_url: str,
                        service_auth0_token: str) -> List[str]:
    """
        Return list of ETF tickers
    """

    response = datum_api_get_request(
        url=f'{datum_api_url}/tickers/etf',
        service_auth0_token=service_auth0_token
    )

    return response


def api_get_tickers_daily_data(datum_api_url: str,
                               service_auth0_token: str,
                               str_date: str,
                               is_close: bool = True,
                               is_open: bool = True,
                               is_high: bool = True,
                               is_low: bool = True,
                               is_volume: bool = True,
                               **kwargs) -> Dict[str, Dict]:
    """
        Return dict of tickers with their selected data
        Args:
            datum_api_url str: host name of Datum API
            service_auth0_token str: auth0 serve token
            str_date str: target date
            is_close bool: is ticker activity will be in result
            is_open bool: is country of ticker will be in result
            is_high bool: is equity_type of ticker will be in result
            is_low bool: is this level will be in result
            is_volume bool: is this level will be in result
        Returns:
            example:
                {'AAPL': {'c': 456.09, 'o': 342.56, 'v': 124552}}
    """
    locals_variables = locals()
    abbreviations = {
        'open': 'o',
        'close': 'c',
        'high': 'h',
        'low': 'l',
        'volume': 'v',
    }

    next_workday = common.get_next_workday(
        datetime.datetime.strptime(
            locals_variables.pop('str_date'),
            '%Y-%m-%d'
        ).date()
    )

    active_params_list = []
    for param, value in locals_variables.items():
        try:
            field = param.split('is_')[1]
            if value:
                active_params_list.append(abbreviations[field])
        except IndexError:
            pass

    response = datum_api_get_request(
        url=f'{datum_api_url}/daily/prev_date',
        service_auth0_token=service_auth0_token,
        params={'chart_type': ''.join(active_params_list), 'date': str(next_workday), **kwargs}
    )

    return processing_list_of_dicts(response, key='ticker')


def api_get_volumes(datum_api_url: str,
                    service_auth0_token: str,
                    date_from: datetime.date,
                    date_to: datetime.date,
                    ticker: str,
                    interval: int = 15,
                    **kwargs) -> Dict[str, Dict]:
    """
        Return dict of tickers with their volumes per interval
        Args:
            datum_api_url str: host name of Datum API
            service_auth0_token str: auth0 serve token
            date_from str or date: start date range
            date_to str or date: end date range
            ticker str or date: end date range
        Returns:
            example:
                {'2022-12-01 04:00:00': {'v': 456.09}}
    """
    if date_from > date_to:
        raise Exception(f'date_from should be less than date_to! (date_from={date_from}, date_to={date_to})')

    result = {}
    while date_from <= date_to:
        intermediate_date = date_from + datetime.timedelta(days=89)  # endpoint returns data only for 90 days
        if intermediate_date > date_to:
            intermediate_date = date_to

        response = datum_api_get_request(
            url=f'{datum_api_url}/intraday',
            service_auth0_token=service_auth0_token,
            params={
                'start_datetime': f'{date_from} 00:00:00',
                'end_datetime': f'{intermediate_date} 23:59:59',
                'ticker': ticker,
                'interval': interval,
                'chart_type': 'v',
                **kwargs
            }
        )

        result.update(processing_list_of_dicts(response, key='dt'))

        date_from = intermediate_date + datetime.timedelta(days=1)

    return result


def api_get_closes_opens(datum_api_url: str,
                         service_auth0_token: str,
                         date_from: datetime.date,
                         date_to: datetime.date,
                         **kwargs) -> List[Dict]:
    """
        Return dict of tickers with their closes and opens
        Args:
            datum_api_url str: host name of Datum API
            service_auth0_token str: auth0 serve token
            date_from str or date: start date range
            date_to str or date: end date range
        Returns:
            example:
                {'2022-12-01 04:00:00': {'v': 456.09}}
    """
    if date_from > date_to:
        raise Exception(f'date_from should be less than date_to! (date_from={date_from}, date_to={date_to})')

    result = []
    while date_from <= date_to:
        intermediate_date = date_from + datetime.timedelta(days=29)  # endpoint returns data only for 30 days
        if intermediate_date > date_to:
            intermediate_date = date_to

        result.extend(
            datum_api_get_request(
                url=f'{datum_api_url}/opg_and_clo',
                service_auth0_token=service_auth0_token,
                params={
                    'start_date': f'{date_from}',
                    'end_date': f'{intermediate_date}',
                    **kwargs
                }
            )
        )

        date_from = intermediate_date + datetime.timedelta(days=1)

    return result


def api_get_ptp_tickers(datum_api_url: str, service_auth0_token: str) -> Dict[str, list]:
    datum_response = datum_api_get_request(
        url=f'{datum_api_url}/tickers/all_ptps',
        service_auth0_token=service_auth0_token
    )
    tickers_by_sorter = defaultdict(list)
    for row in datum_response:
        tickers_by_sorter[row['sorter']].append(row['ticker'])
    return tickers_by_sorter


def api_get_tickers_changes(datum_api_url: str,
                            service_auth0_token: str,
                            start_eff_date: str,
                            end_eff_date: str,
                            **kwargs):
    return datum_api_get_request(
        url=f'{datum_api_url}/corporate_actions/ticker_changes',
        service_auth0_token=service_auth0_token,
        params={
            'start_eff_date': start_eff_date,
            'end_eff_date': end_eff_date,
            **kwargs
        }
    )


def api_get_changed_tickers_per_date(datum_api_url: str,
                                     service_auth0_token: str,
                                     start_eff_date: str,
                                     end_eff_date: str,
                                     ):
    ticker_changes = api_get_tickers_changes(datum_api_url=datum_api_url,
                                             service_auth0_token=service_auth0_token,
                                             start_eff_date=start_eff_date,
                                             end_eff_date=end_eff_date)
    response = defaultdict(list)
    for row in ticker_changes:
        response[row['eff_date']].append(row['old_ticker'])
        response[row['eff_date']].append(row['new_ticker'])

    return response


def api_get_auctions(datum_api_url: str,
                     service_auth0_token: str,
                     start_date: str,
                     end_date: str,
                     ticker: str = None,
                     auction: str = None,
                     **kwargs):
    """
        ticker: optional, in query params, if it is null, endpoint returns auctions of active US stocks,
                but in this case max date range of auction data is 5 days
        auction: optional, in query params, can be: open/close/reopen
                 if empty, endpoint returns all of the above auction types
    """

    params = {
        'start_date': start_date,
        'end_date': end_date,
        **kwargs
    }
    if ticker is not None:
        params.update({'ticker': ticker})
    if auction is not None:
        params.update({'auction_type': auction})

    return datum_api_get_request(
        url=f'{datum_api_url}/auctions',
        service_auth0_token=service_auth0_token,
        params=params
    )


def api_get_holidays(datum_api_url: str,
                     service_auth0_token: str,
                     gte_date: str,
                     lte_date: str,
                     **kwargs):
    params = {
        "gte_date": gte_date,
        "lte_date": lte_date,
        "holiday_name": True,
        **kwargs
    }

    return datum_api_get_request(
        url=f'{datum_api_url}/holidays',
        service_auth0_token=service_auth0_token,
        params=params
    )


def api_get_short_days(datum_api_url: str,
                       service_auth0_token: str,
                       gte_date: str,
                       lte_date: str,
                       **kwargs):
    params = {
        "gte_date": gte_date,
        "lte_date": lte_date,
        "short_day_name": True,
        **kwargs
    }

    return datum_api_get_request(
        url=f'{datum_api_url}/short_days',
        service_auth0_token=service_auth0_token,
        params=params
    )


def api_get_median_opg_volume(datum_api_url: str,
                              service_auth0_token: str,
                              date: datetime.date = None,
                              **kwargs) -> dict:
    if not date:
        date = common.get_current_datetime().date()

    list_of_dicts = datum_api_get_request(
        url=f'{datum_api_url}/calculations/median_opg_volume_20d',
        service_auth0_token=service_auth0_token,
        params={'date_as_of': date, **kwargs}
    )
    return {row['ticker']: row['value'] for row in list_of_dicts}

# --------------------- End of Queries to Datum API ---------------------
