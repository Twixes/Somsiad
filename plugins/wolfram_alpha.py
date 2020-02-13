# Copyright 2020 Twixes

# This file is part of Somsiad - the Polish Discord bot.

# Somsiad is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# Somsiad is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with Somsiad.
# If not, see <https://www.gnu.org/licenses/>.

from typing import Optional
import aiohttp
from discord.ext import commands
from core import somsiad
from configuration import configuration


class WolframAlpha(commands.Cog):
    API_URL = 'https://api.wolframalpha.com/v2/query'
    API_PARAMS = {
        'appid': configuration['wolfram_alpha_app_id'],
        'output': 'json'
    }

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def fetch_pods(self, query: str) -> Optional[dict]:
        try:
            async with aiohttp.ClientSession() as session:
                params = {'input': query, **self.API_PARAMS}
                async with session.get(self.API_URL, headers=self.bot.HEADERS, params=params) as request:
                    if request.status == 200:
                        response = await request.json(content_type='text/plain;charset=utf-8')
                        result = response['queryresult']
                        if result['success']:
                            return result['pods']
                        else:
                            return None
                    else:
                        return None
        except aiohttp.client_exceptions.ClientConnectorError:
            return None

    @commands.command(
        aliases=['wolframalpha', 'wolfram', 'wa', 'kalkulator', 'oblicz', 'policz', 'przelicz', 'konwertuj']
    )
    @commands.cooldown(
        1, configuration['command_cooldown_per_user_in_seconds'], commands.BucketType.user
    )
    async def wolfram_alpha(self, ctx, *, query):
        async with ctx.typing():
            pods = await self.fetch_pods(query)
            embed = self.bot.generate_embed('🧠', 'Wyniki z Wolfram Alpha')
            thumbnail = None
            image = None
            entries = 0
            if pods:
                for pod in pods[:15]:
                    subpods_data = [
                        f'```Mathematica\n{subpod["plaintext"]}```' for subpod in pod['subpods']
                        if subpod.get('plaintext')
                    ]
                    subpods_presentation = ''.join(subpods_data)
                    is_pod_image = pod['id'].startswith('Image')
                    is_pod_chart = pod['id'].startswith(('Plot', 'Timeline'))
                    if is_pod_image or is_pod_chart or not subpods_presentation:
                        subpod_image = pod['subpods'][0]['img']
                        subpod_image['proportions'] = int(subpod_image['width']) / int(subpod_image['height'])
                        if image is None and not is_pod_image:
                            image = subpod_image
                        elif thumbnail is None:
                            if subpod_image['proportions'] <= 1 or is_pod_image:
                                thumbnail = subpod_image
                            elif subpod_image['proportions'] > image['proportions']:
                                thumbnail = image
                                image = subpod_image
                    elif len(subpods_presentation) <= 1024 and entries + len(subpods_data) <= 15:
                        embed.add_field(name=pod['title'], value=subpods_presentation, inline=False)
                        entries += len(subpods_data)
                if thumbnail is not None:
                    embed.set_thumbnail(url=thumbnail['src'])
                if image is not None:
                    embed.set_image(url=image['src'])
            else:
                embed = self.bot.generate_embed('🙁', f'Brak wyników dla zapytania "{query}"')
        await self.bot.send(ctx, embed=embed)


somsiad.add_cog(WolframAlpha(somsiad))
