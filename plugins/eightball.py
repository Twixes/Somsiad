import discord
import asyncio
from discord.ext.commands import Bot
from discord.ext import commands
import random
import os
from somsiad_helper import *


@client.command(aliases=['8ball', '8'])
@commands.cooldown(1, 15, commands.BucketType.user)
@commands.guild_only()
async def eightball(ctx, *args):
    """Returns 8ball answer."""
    with open(os.path.join(bot_dir, 'data', '8ball_responses.txt')) as f:
        responses = [line.strip() for line in f.readlines()]
    
    response = random.choice(responses)
    await ctx.send('{}, '.format(ctx.author.mention) + "\n:8ball: " + response)
