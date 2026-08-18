# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import re
from datetime import date, datetime, timedelta
from urllib.parse import quote, urlencode

import pytz

from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.date_utils import add


def convert_to_days(seconds=None, miliseconds=None):
    """
    Converts the given duration in seconds or miliseconds into days.

    :param int seconds: duration in seconds
    :param int miliseconds: duration in miliseconds
    :return: duration in days
    :rtype: int
    """
    if seconds:
        return seconds / 60 / 60 / 24
    elif miliseconds:
        return miliseconds / 1000 / 60 / 60 / 24
    return 0


def convert_to_date(
    date_add=None,
    seconds=None,
    miliseconds=None,
    expire_date=True,
    time_zone=None,
    format_date=None,
):
    if time_zone and isinstance(time_zone, str):
        time_zone = pytz.timezone(time_zone)
    if expire_date:
        if not date_add:
            date_add = date.today()
        return_date = add(
            date_add + timedelta(days=convert_to_days(seconds, miliseconds))
        )
    else:
        return_date = datetime.fromtimestamp(miliseconds / 1000, tz=time_zone)
    if format_date:
        return_date = return_date.strftime(format_date)
    return return_date


def convert_date_in_time(miliseconds, timezone=None):
    timezone = timezone if timezone else pytz.utc
    if isinstance(timezone, str):
        timezone = pytz.timezone(timezone)
    val_date = convert_to_date(
        miliseconds=miliseconds, expire_date=False, time_zone=timezone
    )
    current_date = datetime.now(timezone)
    diff_date = current_date - val_date
    seconds = diff_date.total_seconds()
    minutes = seconds / 60
    hours = minutes / 60
    days = hours / 24
    months = days / 30
    years = months / 12

    if seconds < 60:
        date_in_time = f"{int(seconds)} seconds"
    elif minutes < 60:
        date_in_time = f"{int(minutes)} minutes"
    elif hours < 24:
        date_in_time = f"{int(hours)} hours"
    elif days < 30:
        date_in_time = f"{int(days)} days"
    elif months < 12:
        date_in_time = f"{int(months)} months"
    else:
        years_exacts = int(years)
        months_exacts = int(months % 12)
        date_in_time = f"{years_exacts} years y {months_exacts} months"
    return date_in_time


def replace_repetitions(text, character_replace, character_new, repetitions):
    positions = [m.start() for m in re.finditer(re.escape(character_replace), text)]
    text_result = list(text)
    count = 0
    for repetition in repetitions:
        if int(repetition) - 1 < len(positions):
            if count == 0:
                start = positions[int(repetition) - 1]
                count += 1
            else:
                start = positions[int(repetition) - 1] - (
                    (len(character_replace) - 1) * count
                )
                count += 1
            fin = start + len(character_replace)
            text_result[start:fin] = character_new
    return "".join(text_result)


def social_url_encode(
    param_field, params_values, params_values_char_ignore, format_quote=False
):
    values = {param_field: params_values[param_field]}
    if isinstance(params_values[param_field], list):
        values = (
            "List("
            + ",".join(
                quote(str(param_value), safe=",")
                for param_value in params_values[param_field]
            )
            + ")"
        )
        url_format = f"{param_field}={quote(values, safe='()%,')}".replace("+", "")
    elif format_quote:
        url_format = (
            f"{param_field}={quote(str(params_values[param_field]), safe='()%,')}"
        )
    else:
        url_format = urlencode(values)
    if params_values_char_ignore and params_values_char_ignore.get(param_field, False):
        for params_values_char in params_values_char_ignore[param_field]:
            for key, character in params_values_char.items():
                if quote(character) in url_format and key == "all":
                    url_format = url_format.replace(quote(character), character)
                else:
                    url_format = replace_repetitions(
                        url_format, quote(character), character, key.split(",")
                    )
    return url_format


def _generate_timestamps(date_start=None, date_end=None):
    if isinstance(date_start, str):
        date_start = datetime.strptime(date_start, DEFAULT_SERVER_DATE_FORMAT)
    if isinstance(date_end, str):
        date_end = datetime.strptime(date_end, DEFAULT_SERVER_DATE_FORMAT)

    if date_start:
        date_start_time = date_start.timestamp() * 1000
    else:
        date_start_time = datetime.now().timestamp() * 1000

    if date_end:
        date_end_time = date_end.timestamp() * 1000
    else:
        date_end_time = date_start_time + (30 * 86400000)
    return int(date_start_time), int(date_end_time)


def get_weeks(start_date, end_date, freq="W-MON", env=None):
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date)

    result = []

    if freq == "D":
        current = start_date
        while current <= end_date:
            result.append(current.strftime("%d/%m/%Y"))
            current += timedelta(days=1)

    elif freq == "ME":
        current = start_date.replace(day=1)
        while current <= end_date:
            next_month = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
            last_day = next_month - timedelta(days=1)
            if last_day <= end_date:
                result.append(last_day.strftime("%m/%Y"))
            current = next_month

    elif freq == "W-MON":
        days_ahead = (0 - start_date.weekday()) % 7
        current = start_date + timedelta(days=days_ahead)
        while current <= end_date:
            result.append(current.strftime("%W/%Y"))
            current += timedelta(weeks=1)

    else:
        raise UserError(env._("Unsupported frequency: %(freq)s", freq=freq))

    return result
