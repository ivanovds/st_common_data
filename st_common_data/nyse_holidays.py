NYSE_HOLIDAYS = [
    {
        'date': '07.09.2020',
        'name': 'Labor Day',
        'status': 'Closed',
    },
    {
        'date': '26.11.2020',
        'name': 'Thanksgiving Day',
        'status': 'Closed',
    },
    {
        'date': '27.11.2020',
        'name': 'Thanksgiving Day',
        'status': '9:30 AM - 1:00 PM',
    },
    {
        'date': '24.12.2020',
        'name': 'Christmas',
        'status': '9:30 AM - 1:00 PM',
    },
    {
        'date': '25.12.2020',
        'name': 'Christmas',
        'status': 'Closed',
    },
    # ---------- 2021 --------------------
    {
        'date': '01.01.2021',
        'name': 'New Year\'s Day',
        'status': 'Closed',
    },
    {
        'date': '18.01.2021',
        'name': 'Martin Luther King Jr. Day',
        'status': 'Closed',
    },
    {
        'date': '15.02.2021',
        'name': 'Washington\'s Birthday',
        'status': 'Closed',
    },
    {
        'date': '02.04.2021',
        'name': 'Good Friday',
        'status': 'Closed',
    },
    {
        'date': '31.05.2021',
        'name': 'Memorial Day',
        'status': 'Closed',
    },
    {
        'date': '05.07.2021',
        'name': 'Independence Day',
        'status': 'Closed',
    },
    {
        'date': '06.09.2021',
        'name': 'Labor Day',
        'status': 'Closed',
    },
    {
        'date': '25.11.2021',
        'name': 'Thanksgiving Day',
        'status': 'Closed',
    },
    {
        'date': '26.11.2021',
        'name': 'Thanksgiving Day',
        'status': '9:30 AM - 1:00 PM',
    },
    {
        'date': '24.12.2021',
        'name': 'Christmas',
        'status': 'Closed',
    },
    # ---------- 2022 -------------------
    {
        'date': '17.01.2022',
        'name': 'Martin Luther King Jr. Day',
        'status': 'Closed',
    },
    {
        'date': '21.02.2022',
        'name': 'Washington\'s Birthday',
        'status': 'Closed',
    },
    {
        'date': '15.04.2022',
        'name': 'Good Friday',
        'status': 'Closed',
    },
    {
        'date': '30.05.2022',
        'name': 'Memorial Day',
        'status': 'Closed',
    },
    {
        'date': '04.07.2022',
        'name': 'Independence Day',
        'status': 'Closed',
    },
    {
        'date': '05.09.2022',
        'name': 'Labor Day',
        'status': 'Closed',
    },
    {
        'date': '24.11.2022',
        'name': 'Thanksgiving Day',
        'status': 'Closed',
    },
    {
        'date': '25.11.2022',
        'name': 'Thanksgiving Day',
        'status': '9:30 AM - 1:00 PM',
    },
    {
        'date': '26.12.2022',
        'name': 'Christmas',
        'status': 'Closed',
    },
]


def is_holiday(current_datetime):
    for holiday in NYSE_HOLIDAYS:
        if current_datetime.strftime("%d.%m.%Y") == holiday['date'] and (holiday['status'] == 'Closed'):
            return True
    return False