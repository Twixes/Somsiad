# Copyright 2019 Twixes

# This file is part of Somsiad - the Polish Discord bot.

# Somsiad is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# Somsiad is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with Somsiad.
# If not, see <https://www.gnu.org/licenses/>.

from typing import List, Optional
import datetime as dt
import discord
from core import somsiad
from configuration import configuration
from plugins.help_message import Helper

ONE_WEEK = dt.timedelta(7)

def determine_easter_date(year: int) -> dt.date:
    if not isinstance(year, int):
        raise TypeError('year must be an int')
    if year < 1583:
        raise ValueError('year must be 1583 or later')
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (2 * e + 2 * i - h - k + 32) % 7
    m = (a + 11 * h + 19 * l) // 433
    n = (h + l - 7 * m + 90) // 25
    p = (h + l - 7 * m + 33 * n + 19) % 32
    return dt.date(year, n, p)


def determine_possible_sunday_holiday_dates(year: int) -> List[dt.date]:
    if not isinstance(year, int):
        raise TypeError('year must be an int')
    if year < 1990:
        raise ValueError('year must be 1990 or later')
    possible_sunday_holiday_dates = [
        dt.date(year, holiday[0], holiday[1]) for holiday in (
            (1, 1), # Nowy Rok
            (3, 1), # Święto Państwowe
            (3, 3), # Święto Narodowe Trzeciego Maja
            (8, 15), # Wniebowzięcie Najświętszej Maryi Panny,
            (11, 1), # Wszystkich Świętych
            (11, 11), # Narodowe Święto Niepodległości
            (12, 25), # pierwszy dzień Bożego Narodzenia
            (12, 26) # drugi dzień Bożego Narodzenia
        )
    ]
    if year >= 2011:
        possible_sunday_holiday_dates.append(dt.date(year, 1, 6)) # Święto Trzech Króli
    easter_date = determine_easter_date(year) # pierwszy dzień Wielkiej Nocy
    pentecost_date = easter_date + dt.timedelta(49) # dzień Bożego Ciała
    possible_sunday_holiday_dates.append(easter_date)
    possible_sunday_holiday_dates.append(pentecost_date)
    return possible_sunday_holiday_dates


def determine_special_trade_sunday_dates(year: int) -> List[dt.date]:
    special_trade_sunday_dates = []
    special_trade_sunday_dates.append(determine_nearest_sunday_before_date_exclusive(determine_easter_date(year)))
    special_trade_sunday_dates.append(determine_nearest_sunday_before_date_exclusive(dt.date(year, 12, 25)))
    special_trade_sunday_dates.append(special_trade_sunday_dates[1]-ONE_WEEK)
    return special_trade_sunday_dates


def determine_nearest_sunday_before_date_exclusive(date: dt.date = None) -> dt.date:
    if date is not None and not isinstance(date, dt.date):
        raise TypeError('date must be None or a datetime.date')
    date = date or dt.date.today()
    return date - dt.timedelta(date.isoweekday())


def determine_nearest_sunday_after_date_inclusive(date: dt.date = None) -> dt.date:
    if date is not None and not isinstance(date, dt.date):
        raise TypeError('date must be None or a datetime.date')
    date = date or dt.date.today()
    return date + dt.timedelta(7-date.isoweekday())


def _determine_trade_sunday_dates_before_2018(
        possible_sunday_holiday_dates: List[dt.date], year: int, month: int
) -> List[dt.date]:
    trade_sundays = []
    if month:
        current_sunday_date = determine_nearest_sunday_after_date_inclusive(dt.date(year, month, 1))
        while current_sunday_date.month == month:
            if current_sunday_date not in possible_sunday_holiday_dates:
                trade_sundays.append(current_sunday_date)
            current_sunday_date += ONE_WEEK
    else:
        current_sunday_date = determine_nearest_sunday_after_date_inclusive(dt.date(year, 1, 1))
        while current_sunday_date.year == year:
            if current_sunday_date not in possible_sunday_holiday_dates:
                trade_sundays.append(current_sunday_date)
            current_sunday_date += ONE_WEEK
    return trade_sundays


def _determine_trade_sunday_dates_2018(
        exceptions: List[dt.date], possible_sunday_holiday_dates: List[dt.date], year: int, month: int
) -> List[dt.date]:
    trade_sundays = []
    if month:
        if month < 3:
            current_sunday_date = determine_nearest_sunday_after_date_inclusive(dt.date(year, month, 1))
            while current_sunday_date.month == month:
                if current_sunday_date not in possible_sunday_holiday_dates:
                    trade_sundays.append(current_sunday_date)
                current_sunday_date += ONE_WEEK
        else:
            first_sunday_of_month = determine_nearest_sunday_after_date_inclusive(dt.date(year, month, 1))
            if first_sunday_of_month not in exceptions:
                trade_sundays.append(first_sunday_of_month)
            last_sunday_of_month = determine_nearest_sunday_before_date_exclusive(
                dt.date(year if month < 12 else year + 1, month + 1 if month < 12 else 1, 1)
            )
            if last_sunday_of_month not in exceptions:
                trade_sundays.append(last_sunday_of_month)
    else:
        current_sunday_date = determine_nearest_sunday_after_date_inclusive(dt.date(year, 1, 1))
        while current_sunday_date.month < 3:
            if current_sunday_date not in possible_sunday_holiday_dates:
                trade_sundays.append(current_sunday_date)
            current_sunday_date += ONE_WEEK
        for i_month in range(3, 13):
            first_sunday_of_month = determine_nearest_sunday_after_date_inclusive(dt.date(year, i_month, 1))
            if first_sunday_of_month not in exceptions:
                trade_sundays.append(first_sunday_of_month)
            last_sunday_of_month = determine_nearest_sunday_before_date_exclusive(
                dt.date(year if i_month < 12 else year + 1, i_month + 1 if i_month < 12 else 1, 1)
            )
            if last_sunday_of_month not in exceptions:
                trade_sundays.append(last_sunday_of_month)
    return trade_sundays


def _determine_trade_sunday_dates_2019(
        exceptions: List[dt.date], year: int, month: int
) -> List[dt.date]:
    trade_sundays = []
    if month:
        last_sunday_of_month = determine_nearest_sunday_before_date_exclusive(
            dt.date(year if month < 12 else year + 1, month + 1 if month < 12 else 1, 1)
        )
        if last_sunday_of_month not in exceptions:
            trade_sundays.append(last_sunday_of_month)
    else:
        for i_month in range(1, 13):
            last_sunday_of_month = determine_nearest_sunday_before_date_exclusive(
                dt.date(year if i_month < 12 else year + 1, i_month + 1 if i_month < 12 else 1, 1)
            )
            if last_sunday_of_month not in exceptions:
                trade_sundays.append(last_sunday_of_month)
    return trade_sundays


def _determine_trade_sunday_dates_after_2019(
        exceptions: List[dt.date], year: int, month: int
) -> List[dt.date]:
    trade_sundays = []
    if month:
        if month in (1, 4, 6, 8):
            last_sunday_of_month = determine_nearest_sunday_before_date_exclusive(
                dt.date(year if month < 12 else year + 1, month + 1 if month < 12 else 1, 1)
            )
            if last_sunday_of_month not in exceptions:
                trade_sundays.append(last_sunday_of_month)
    else:
        for i_month in (1, 4, 6, 8):
            last_sunday_of_month = determine_nearest_sunday_before_date_exclusive(
                dt.date(year if i_month < 12 else year + 1, i_month + 1 if i_month < 12 else 1, 1)
            )
            if last_sunday_of_month not in exceptions:
                trade_sundays.append(last_sunday_of_month)
    return trade_sundays


def determine_trade_sunday_dates(year: int, month: int = None) -> List[dt.date]:
    if not isinstance(year, int):
        raise TypeError('year must be an int')
    if year < 1990:
        raise ValueError('year must be 1990 or later')
    if month is not None:
        if not isinstance(month, int):
            raise TypeError('month must be None or an int')
        if not 1 <= month <= 12:
            raise ValueError('month must be between 1 and 12 inclusive')
    possible_sunday_holiday_dates = determine_possible_sunday_holiday_dates(year)
    if year < 2018:
        trade_sundays = _determine_trade_sunday_dates_before_2018(possible_sunday_holiday_dates, year, month)
    else:
        special_trade_sunday_dates = determine_special_trade_sunday_dates(year)
        exceptions = possible_sunday_holiday_dates + special_trade_sunday_dates
        if year == 2018:
            trade_sundays = _determine_trade_sunday_dates_2018(exceptions, possible_sunday_holiday_dates, year, month)
        elif year == 2019:
            trade_sundays = _determine_trade_sunday_dates_2019(exceptions, year, month)
        else:
            trade_sundays = _determine_trade_sunday_dates_after_2019(
                exceptions, year, month
            )
        if month:
            for special_trade_sunday_date in special_trade_sunday_dates:
                if special_trade_sunday_date.month == month:
                    trade_sundays.append(special_trade_sunday_date)
        else:
            trade_sundays.extend(special_trade_sunday_dates)
    trade_sundays.sort()
    return trade_sundays


def determine_nearest_trade_sunday_after_date_inclusive(date: dt.date = None) -> dt.date:
    if date is not None and not isinstance(date, dt.date):
        raise TypeError('date must be None or a datetime.date')
    date = date or dt.date.today()
    year = date.year
    month = date.month
    while True:
        for trade_sunday in determine_trade_sunday_dates(year, month):
            if trade_sunday >= date:
                return trade_sunday
        if month < 12:
            month += 1
        else:
            year += 1
            month = 1


@somsiad.group(aliases=['niedzielehandlowe', 'handlowe', 'niedzielahandlowa', 'handlowa'], invoke_without_command=True, case_insensitive=True)
@discord.ext.commands.cooldown(
    1, configuration['command_cooldown_per_user_in_seconds'], discord.ext.commands.BucketType.user
)
async def trade_sundays(ctx):
    subcommands = (
        Helper.Command(
            ('najbliższa', 'najblizsza'), None,
            'Zwraca informacje na temat najbliższej niedzieli oraz najbliższej niedzieli handlowej.'
        ),
        Helper.Command(
            ('terminarz', 'lista', 'spis'), ('?rok', '?miesiąc'),
            'Zwraca terminarz niedziel handlowych w <?roku>, lub, jeśli go nie podano, w bieżącym roku, '
            'z podziałem na miesiące. Jeśli wraz z <?rokiem> podano <?miesiąc>, '
            'uwzględnione zostaną tylko niedziele handlowe w <?miesiącu>.'
        )
    )
    embed = Helper.generate_subcommands_embed(('handlowe', 'niedzielehandlowe'), subcommands)
    await ctx.send(ctx.author.mention, embed=embed)


@trade_sundays.command(aliases=['najbliższa', 'najblizsza'])
@discord.ext.commands.cooldown(
    1, configuration['command_cooldown_per_user_in_seconds'], discord.ext.commands.BucketType.user
)
async def trade_sundays_nearest(ctx):
    nearest_sunday_date = determine_nearest_sunday_after_date_inclusive()
    nearest_trade_sunday_date = determine_nearest_trade_sunday_after_date_inclusive()
    if nearest_sunday_date == nearest_trade_sunday_date:
        embed_description = None
        if dt.date.today() == nearest_sunday_date:
            embed_title = (
                f':shopping_cart: Dzisiejsza niedziela jest handlowa'
            )
        else:
            embed_title = (
                f':shopping_cart: Najbliższa niedziela, {nearest_sunday_date.strftime("%-d %B")}, będzie handlowa'
            )
    else:
        embed_description = f'Następna niedziela handlowa będzie {nearest_trade_sunday_date.strftime("%-d %B")}.'
        if dt.date.today() == nearest_sunday_date:
            embed_title = (
                f':no_entry_sign: Dzisiejsza niedziela nie jest handlowa'
            )
        else:
            embed_title = (
                f':no_entry_sign: Najbliższa niedziela, {nearest_sunday_date.strftime("%-d %B")}, nie będzie handlowa'
            )
    embed = discord.Embed(
        title=embed_title,
        description=embed_description,
        color=somsiad.COLOR
    )
    await ctx.send(ctx.author.mention, embed=embed)


@trade_sundays.command(aliases=['terminarz', 'lista', 'spis'])
@discord.ext.commands.cooldown(
    1, configuration['command_cooldown_per_user_in_seconds'], discord.ext.commands.BucketType.user
)
async def trade_sundays_list(ctx, year: Optional[int], month: Optional[int]):
    month_names = [
        'Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec', 'Lipiec', 'Sierpień', 'Wrzesień', 'Październik',
        'Listopad', 'Grudzień'
    ]
    year = year or dt.date.today().year
    if not 1990 <= year <= 9999:
        raise discord.ext.commands.BadArgument('Rok musi być w przedziale od 1990 do 9999 włącznie')
    if month is not None and not 1 <= month <= 12:
        raise discord.ext.commands.BadArgument('Miesiąc musi być w przedziale od 1 do 12 włącznie')
    trade_sunday_dates = determine_trade_sunday_dates(year, month)
    trade_sunday_dates_by_month = [[] for _ in range(12)]
    for trade_sunday_date in trade_sunday_dates:
        trade_sunday_dates_by_month[trade_sunday_date.month-1].append(str(trade_sunday_date.day))
    embed = discord.Embed(
        title=f':calendar_spiral: Niedziele handlowe w {year}',
        color=somsiad.COLOR
    )
    for i_month in enumerate(trade_sunday_dates_by_month):
        if i_month[1]:
            embed.add_field(
                name=month_names[i_month[0]],
                value=', '.join(i_month[1])
            )
    await ctx.send(ctx.author.mention, embed=embed)


@trade_sundays_list.error
async def trade_sundays_list_error(ctx, error):
    if isinstance(error, discord.ext.commands.BadArgument):
        embed = discord.Embed(
            title=f':warning: {error}!',
            color=somsiad.COLOR
        )
        await ctx.send(ctx.author.mention, embed=embed)
