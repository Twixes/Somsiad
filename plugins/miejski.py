# Copyright 2020 Twixes

# This file is part of Somsiad - the Polish Discord bot.

# Somsiad is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# Somsiad is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with Somsiad.
# If not, see <https://www.gnu.org/licenses/>.

import datetime as dt
import urllib.parse
from discord.ext import commands
from core import cooldown
from bs4 import BeautifulSoup


class Miejski(commands.Cog):
    FOOTER_TEXT = 'Miejski'
    API_URL = 'https://api.urbandictionary.com/v0/define'

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    @cooldown()
    async def miejski(self, ctx, *, query):
        """Returns Urban Dictionary word definition."""
        query_url_safe = urllib.parse.quote_plus(query.replace(' ', '+',))
        url = f'https://www.miejski.pl/slowo-{query_url_safe}'
        async with self.bot.session.get(url) as request:
            if request.status == 200:
                soup = BeautifulSoup(await request.text(), features='html.parser')
                result = soup.article # get top definition
                timestamp = dt.datetime.strptime(
                    result.find(class_='published-date').string.replace('Data dodania: ', ''), '%Y-%m-%d'
                )
                embed = self.bot.generate_embed(
                    None, result.h1.string, url=f'{url}#{result["id"]}', timestamp=timestamp
                )
                definition = result.p
                embed.add_field(name='Definicja', value=definition.get_text().strip(), inline=False)
                example = result.blockquote
                if example is not None:
                    embed.add_field(name='Przykład', value=f'*{example.get_text().strip()}*', inline=False)
                rating = int(result.find(class_='rating').string)
                embed.add_field(name='👍👎', value=f'{rating:n}')
            elif request.status == 404:
                embed = self.bot.generate_embed('🙁', f'Brak wyników dla terminu "{query}"')
            else:
                embed = self.bot.generate_embed('⚠️', 'Nie udało się połączyć z serwisem')
        embed.set_footer(text=self.FOOTER_TEXT)
        await self.bot.send(ctx, embed=embed)

    @miejski.error
    async def miejski_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = self.bot.generate_embed('⚠️', 'Musisz podać termin do sprawdzenia')
            embed.set_footer(text=self.FOOTER_TEXT)
            await self.bot.send(ctx, embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Miejski(bot))
