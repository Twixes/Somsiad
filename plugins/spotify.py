# Copyright 2018 Twixes

# This file is part of Somsiad - the Polish Discord bot.

# Somsiad is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# Somsiad is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with Somsiad.
# If not, see <https://www.gnu.org/licenses/>.

from difflib import SequenceMatcher
import discord
from somsiad import somsiad
from utilities import TextFormatter
from plugins.youtube import youtube


@somsiad.bot.command(aliases=['kanał', 'kanal'])
@discord.ext.commands.cooldown(
    1, somsiad.conf['command_cooldown_per_user_in_seconds'], discord.ext.commands.BucketType.user
)
@discord.ext.commands.guild_only()
async def spotify(ctx):
    """Shares the song currently played on Spotify."""
    if isinstance(ctx.author.activity, discord.activity.Spotify):
        embed = discord.Embed(
            title=f':arrow_forward: {ctx.author.activity.title}',
            color=somsiad.color
        )
        embed.set_thumbnail(url=ctx.author.activity.album_cover_url)
        embed.add_field(name='Autorstwa', value=', '.join(ctx.author.activity.artists))
        embed.add_field(name='Z albumu', value=ctx.author.activity.album)
        embed.add_field(
            name='Długość', value=TextFormatter.minutes_and_seconds(ctx.author.activity.duration.total_seconds())
        )
        embed.add_field(
            name='Posłuchaj na Spotify', value=f'https://open.spotify.com/track/{ctx.author.activity.track_id}',
            inline=False
        )

        # Search for the song on YouTube
        youtube_search_query = f'{ctx.author.activity.title} {" ".join(ctx.author.activity.artists)}'
        youtube_search_result = youtube.search(youtube_search_query)
        # Add a link to a YouTube video if a match was found
        if (
                youtube_search_result and
                SequenceMatcher(None, youtube_search_query, youtube_search_result[0]['snippet']['title']).ratio() > 0.25
        ):
            video_id = youtube_search_result[0]['id']['videoId']
            video_thumbnail_url = youtube_search_result[0]['snippet']['thumbnails']['medium']['url']
            embed.add_field(
                name='Posłuchaj na YouTube', value=f'https://www.youtube.com/watch?v={video_id}', inline=False
            )
            embed.set_image(url=video_thumbnail_url)

        embed.set_footer(
            text='Spotify',
            icon_url='https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/'
            'Spotify_logo_without_text.svg/60px-Spotify_logo_without_text.svg.png'
        )
    else:
        embed = discord.Embed(
            title=f':stop_button: Nie słuchasz w tym momencie niczego na Spotify',
            color=somsiad.color
        )

    await ctx.send(f'{ctx.author.mention}', embed=embed)