# Copyright 2020 Twixes

# This file is part of Somsiad - the Polish Discord bot.

# Somsiad is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# Somsiad is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with Somsiad.
# If not, see <https://www.gnu.org/licenses/>.

import datetime as dt

import psycopg2
from discord.ext import commands

import data
from utilities import text_snippet, utc_to_naive_local


class Invocation(data.MemberRelated, data.ChannelRelated, data.Base):
    MAX_ERROR_LENGTH = 300

    message_id = data.Column(data.BigInteger, primary_key=True)
    prefix = data.Column(data.String(max(23, data.Server.COMMAND_PREFIX_MAX_LENGTH)), nullable=False)
    full_command = data.Column(data.String(100), nullable=False, index=True)
    root_command = data.Column(data.String(100), nullable=False, index=True)
    created_at = data.Column(data.DateTime, nullable=False)
    exited_at = data.Column(data.DateTime)
    error = data.Column(data.String(MAX_ERROR_LENGTH))


class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        with data.session(commit=True) as session:
            invocation = Invocation(
                message_id=ctx.message.id,
                server_id=ctx.guild.id if ctx.guild is not None else None,
                channel_id=ctx.channel.id,
                user_id=ctx.author.id,
                prefix=ctx.prefix,
                full_command=ctx.command.qualified_name,
                root_command=str(ctx.command.root_parent or ctx.command.qualified_name),
                created_at=utc_to_naive_local(ctx.message.created_at),
            )
            try:
                session.add(invocation)
            except psycopg2.Error:
                pass

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        with data.session(commit=True) as session:
            invocation = session.query(Invocation).get(ctx.message.id)
            invocation.exited_at = dt.datetime.now()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        with data.session(commit=True) as session:
            invocation = session.query(Invocation).get(ctx.message.id)
            if invocation is not None:
                invocation.exited_at = dt.datetime.now()
                invocation.error = text_snippet(
                    str(error).replace('Command raised an exception: ', ''), Invocation.MAX_ERROR_LENGTH
                )


def setup(bot: commands.Bot):
    bot.add_cog(Commands(bot))
