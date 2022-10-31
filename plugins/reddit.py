# Copyright 2020 Twixes

# This file is part of Somsiad - the Polish Discord bot.

# Somsiad is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# Somsiad is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with Somsiad.
# If not, see <https://www.gnu.org/licenses/>.

import datetime as dt
from somsiad import SomsiadMixin
import urllib.parse

import discord
from discord.ext import commands

from core import cooldown


class Reddit(commands.Cog, SomsiadMixin):
    async def fetch_subreddit_and_generate_embed(self, subreddit_name: str, is_nfsw_acceptable: bool) -> discord.Embed:
        url = f'https://www.reddit.com/r/{urllib.parse.quote_plus(subreddit_name)}'
        response = None
        status = None
        async with self.bot.session.get(f'{url}/about.json') as request:
            status = request.status
            response = await request.json()
        if status == 200 and response.get('kind') == 't5':
            about = response['data']
            is_nsfw = about['over18']
            if is_nsfw and not is_nfsw_acceptable:
                embed = self.bot.generate_embed('🔞', 'Treści NSFW nie są dozwolone na tym kanale')
            else:
                created_datetime = dt.datetime.fromtimestamp(about['created_utc'])
                emoji = '🔞' if is_nsfw else '📃'
                embed = self.bot.generate_embed(emoji, about['title'], about['public_description'], url=url)
                embed.add_field(name='Subskrybentów', value=f'{about["subscribers"]:n}')
                embed.add_field(name='Użytkowników online', value=f'{about["accounts_active"]:n}')
                embed.add_field(name='Utworzono', value=created_datetime.strftime('%-d %B %Y'))
                if not about['over18']:
                    if about.get('header_img'):
                        embed.set_thumbnail(url=about['header_img'])
                    if about.get('banner_background_image'):
                        embed.set_image(url=about['banner_background_image'])
        elif status == 403:
            if response.get('reason') == 'private':
                reason = 'prywatny'
            elif response.get('reason') == 'quarantined':
                reason = 'poddany kwarantannie'
            elif response.get('reason') == 'gold_only':
                reason = 'tylko dla użytkowników premium'
            else:
                reason = 'niedostępny'
            embed = self.bot.generate_embed('🙁', f'Podany subreddit jest {reason}')
        elif status == 404 or response.get('kind') != 't5':
            embed = self.bot.generate_embed('🙁', 'Nie znaleziono podanego subreddita')
        else:
            embed = self.bot.generate_embed('⚠️', 'Nie udało się połączyć z serwisem')
        embed.set_footer(text='Reddit', icon_url='https://www.reddit.com/favicon.ico')
        return embed

    async def fetch_user_and_generate_embed(self, username: str, is_nfsw_acceptable: bool) -> discord.Embed:
        url = f'https://www.reddit.com/user/{urllib.parse.quote_plus(username)}'
        response = None
        status = None
        async with self.bot.session.get(f'{url}/about.json') as request:
            status = request.status
            response = await request.json()
        if status == 200 and response.get('kind') == 't2':
            about = response['data']
            subreddit_present = about.get('subreddit') is not None
            is_nsfw = subreddit_present and about['subreddit']['over_18']
            if is_nsfw and not is_nfsw_acceptable:
                embed = self.bot.generate_embed('🔞', 'Treści NSFW nie są dozwolone na tym kanale')
            else:
                created_datetime = dt.datetime.fromtimestamp(about['created_utc'])
                today = dt.date.today()
                emoji = '👤'
                if (created_datetime.day, created_datetime.month) == (today.day, today.month):
                    emoji = '🎂'
                elif about['name'] == 'spez':
                    emoji = '‼️'
                elif about['is_employee']:
                    emoji = '❗️'
                elif is_nsfw:
                    emoji = '🔞'
                elif about['is_gold']:
                    emoji = '🏆'
                description = None
                if subreddit_present and about['subreddit'].get('banner_img'):
                    description = about['subreddit']['public_description']
                embed = self.bot.generate_embed(emoji, about['name'], description, url=url)
                embed.add_field(name='Karma z postów', value=f'{about["link_karma"]:n}')
                embed.add_field(name='Karma z komentarzy', value=f'{about["comment_karma"]:n}')
                embed.add_field(name='Utworzył konto', value=created_datetime.strftime('%-d %B %Y'))
                if about.get('icon_img'):
                    embed.set_thumbnail(url=about['icon_img'])
        elif status == 404 or response.get('kind') != 't2':
            embed = self.bot.generate_embed('🙁', 'Nie znaleziono podanego użytkownika')
        else:
            embed = self.bot.generate_embed('⚠️', f'Nie udało się połączyć z serwisem')
        embed.set_footer(text='Reddit', icon_url='https://www.reddit.com/favicon.ico')
        return embed

    @cooldown()
    @commands.command(aliases=['r', 'sub'])
    async def subreddit(self, ctx, subreddit_name):
        async with ctx.typing():
            embed = await self.fetch_subreddit_and_generate_embed(subreddit_name, ctx.channel.is_nsfw())
            await self.bot.send(ctx, embed=embed)

    @subreddit.error
    async def subreddit_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = self.bot.generate_embed('⚠️', 'Nie podano nazwy subreddita')
            embed.set_footer(text='Reddit', icon_url='https://www.reddit.com/favicon.ico')
            await self.bot.send(ctx, embed=embed)

    @cooldown()
    @commands.command(aliases=['u'])
    async def user(self, ctx, username):
        async with ctx.typing():
            embed = await self.fetch_user_and_generate_embed(username, ctx.channel.is_nsfw())
            await self.bot.send(ctx, embed=embed)

    @user.error
    async def user_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = self.bot.generate_embed('⚠️', 'Nie podano nazwy użytkownika')
            embed.set_footer(text='Reddit', icon_url='https://www.reddit.com/favicon.ico')
            await self.bot.send(ctx, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Reddit(bot))
