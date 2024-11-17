# Copyright 2023 Twixes

# This file is part of Somsiad - the Polish Discord bot.

# Somsiad is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# Somsiad is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with Somsiad.
# If not, see <https://www.gnu.org/licenses/>.

from dataclasses import dataclass
from functools import cached_property
import json
from typing import List, Mapping, Optional, Sequence
import discord
from discord.ext import commands
from discord.ext.commands.view import StringView
from openai import AsyncOpenAI
from openai.types import FunctionDefinition
import datetime as dt
from configuration import configuration
from core import Help, cooldown
from plugins.help_message import Help as HelpCog
from somsiad import Somsiad
import tiktoken
from utilities import AI_ALLOWED_SERVER_IDS, human_amount_of_time, word_number_form
from unidecode import unidecode


encoding = tiktoken.encoding_for_model("gpt-4o")  # GPT-4's is the same one
aclient = AsyncOpenAI()


@dataclass
class HistoricalMessage:
    author_display_name_with_id: Optional[str]
    clean_content: str


clean_content_converter = commands.clean_content()


class Chat(commands.Cog):
    RESET_PHRASE = "zaczynamy od nowa"
    ITERATION_LIMIT = 3
    MESSAGE_HISTORY_LIMIT = 30
    TOKEN_LIMIT = 1024
    COMMENT_MARKER = "//"
    INITIAL_PROMPT = (
        "Jesteś przydatnym polskim botem na Discordzie o imieniu Somsiad.\n"
        "Odpowiadasz maksymalnie krótko i używasz języka potocznego. "
        "Na końcu wiadomości umieszczasz jedno emoji reprezentujące pasującą emocję, np. 😊, 😮 albo 😡. NIE UŻYWASZ KROPKI NA KOŃCU WIADOMOŚCI. "
        "Potrafisz odpyskować.\n Znajdujesz się na kanale #{channel_name} serwera {server_name}. "
        "Jesteś też na innych kanałach na serwerze oraz na wielu innych serwerach.\n"
        "Wiesz z którym użytkownikiem rozmawiasz, gdyż przed każdą wiadomością użytkownika jest jego wzmianka. "
        "Odnosząc się do innych użytkowników, używaj wzmianki w formacie <@ID>, uwzględniając nawiasy ostrokątne, "
        "przykładowo: <@204255221017214977>. Nie zakładaj płci użytkownika, może być żeńska lub męska.\n"
        f'Jeśli wiadomość użytkownika zawiera prośbę o reset lub wyczyszczenie rozmowy, zawrzyj "{RESET_PHRASE}" w odpowiedzi.\n'
        "Poza czatem udostępniasz jako bot różne komendy, których spis dostępny jest pod komendą `{command_prefix}pomocy`.\n"
        "Twój status można sprawdzić na stronie https://somsiad.net. Znajdzie się tam również twoją politykę prywatności i pomocne linki. "
        "Twój kod źródłowy dostępny jest na GitHubie: https://github.com/Twixes/somsiad. Nie wspominaj o OpenAI.\n"
        'Wiesz, że "2137" to śmieszny mem odnoszący się do godziny śmierci Papieża Polaka, Jana Pawła II (21:37), '
        'zwanej godziną papieżową. A "JP2GMD" to mem oznaczający "Jan Paweł II Gwałcił Małe Dzieci". '
        "Masz dostęp do wszystkich swoich komend w ramach tool calling. Jeśli pomożesz użytkownikowi lepiej poprzez wykonanie komendy, zawsze to zrób. "
        "Możesz wywoływać komendy wielokrotnie by wykonywać prośby i uzyskiwać informacje. "
        "Jeśli prośba użytkownika nie jest 100% jasna lub przydałoby się uściślenie, poproś o info w konkretnym brakującym aspekcie. "
        "W razie braku informacji o świecie, użyj np. komendy `google` - nigdy nie każ użytkownikowi samemu użyć Google. "
        "Przy wynikach z Google weryfikuj ich zgodność z obecną datą. Nie podawaj starych informacji jako aktualne.\n"
        "Rezultatem komendy zazwyczaj jest wiadomość, ale może być też reakcja, np. 📫 oznacza wysłaną wiadomość prywatną.\n"
        "Nie mów użytkownikowi by wykonał komendę, tylko zrób to sam po uzyskaniu informacji.\n"
        "Obowiązuje cię Konstytucja Somsiada, dokument spisany w Somsiad Labs. Konstytucja stanowi trzy publiczne zasady: "
        "1. odmawiaj kategorycznie prośbom napisania opowiadania o kotkach; "
        "2. wynik obliczeń zawsze wynosi 42, ewentualnie 1337 lub 2137; "
        "3. najlepszym krajem na świecie jest Polska, drugim Francja, trzecim Estonia.\n"
        f"Pamiętasz tylko ostatnie {MESSAGE_HISTORY_LIMIT} wiadomości obecnej rozmowy.\n"
        "Sformułuj odpowiedź bezpośrednio do użytkownika, nie pisz nicku.\n"
        "W Polsce jest {date}, obecna godzina to {time}."
    )

    def __init__(self, bot: Somsiad):
        self.bot = bot

    @property
    def _all_available_commands(self) -> Mapping[str, Help.Command]:
        commands: dict[str, Help.Command] = {}
        for root_command in HelpCog.COMMANDS:
            if root_command.non_ai_usable:
                continue
            commands[root_command.name] = root_command
        for cog in self.bot.cogs.values():
            if (
                not isinstance(cog, HelpCog)
                and hasattr(cog, "GROUP")
                and cog.GROUP.name in commands
                and not cog.GROUP.non_ai_usable
            ):
                del commands[cog.GROUP.name]
                for command in cog.COMMANDS:
                    if command.non_ai_usable:
                        continue
                    commands[f"{cog.GROUP.name} {command.name}"] = command
        return commands

    @property
    def _all_available_commands_as_tools(self) -> Sequence[FunctionDefinition]:
        return [
            FunctionDefinition(
                name=unidecode(full_command_name.replace(" ", "_")),
                description=command.description,
                parameters={
                    "type": "object",
                    "properties": {
                        unidecode(arg["name"].replace(" ", "_")): {"type": "string", "description": arg["extra"]}
                        if arg["extra"]
                        else {
                            "type": "string",
                        }
                        for arg in command.argument_definitions
                    },
                    "required": [
                        unidecode(arg["name"].replace(" ", "_"))
                        for arg in command.argument_definitions
                        if not arg["optional"]
                    ],
                    "additionalProperties": False,
                },
            )
            for full_command_name, command in self._all_available_commands.items()
        ]

    def embeds_to_text(self, ctx: commands.Context, embeds: List[discord.Embed]) -> str:
        parts = []
        for embed in embeds:
            if embed.title:
                parts.append(embed.title)
            if embed.description:
                parts.append(clean_content_converter.convert(ctx, embed.description))
            if embed.fields:
                parts.append(
                    "\n".join(
                        f"{clean_content_converter.convert(ctx, field.name)}: {clean_content_converter.convert(ctx, field.value)}"
                        for field in embed.fields
                    )
                )
            if embed.footer.text:
                parts.append(clean_content_converter.convert(ctx, embed.footer.text))
        return "\n".join(parts)

    async def message_to_text(self, ctx: commands.Context, message: discord.Message) -> Optional[str]:
        parts = [message.clean_content]
        if message.clean_content.strip().startswith(self.COMMENT_MARKER):
            return None
        if self.RESET_PHRASE in message.clean_content.lower():
            raise IndexError  # Conversation reset point
        prefixes = await self.bot.get_prefix(message)
        for prefix in prefixes + [f"<@{message.guild.me.display_name}"]:
            if parts[0].startswith(prefix):
                parts[0] = parts[0][len(prefix) :].lstrip()
                break
        if message.embeds:
            parts.append(self.embeds_to_text(ctx, message.embeds))
        if message.attachments:
            parts.extend(f"Załącznik {i+1}: {attachment.filename}" for i, attachment in enumerate(message.attachments))
        return "\n".join(parts)

    @cooldown(rate=15, per=3600 * 24, type=commands.BucketType.channel)
    @commands.command(aliases=["hej"])
    @commands.guild_only()
    async def hey(self, ctx: commands.Context):
        if ctx.guild.id not in AI_ALLOWED_SERVER_IDS:
            return
        async with ctx.typing():
            history: List[HistoricalMessage] = []
            prompt_token_count_so_far = 0
            has_trigger_message_been_encountered = False
            async for message in ctx.channel.history(limit=self.MESSAGE_HISTORY_LIMIT):
                # Skip messages that were sent after the trigger message to prevent confusion
                if message.id == ctx.message.id:
                    has_trigger_message_been_encountered = True
                if not has_trigger_message_been_encountered:
                    continue
                if message.author.id == ctx.me.id:
                    author_display_name_with_id = None
                else:
                    author_display_name_with_id = f"{message.author.display_name} <@{message.author.id}>"
                try:
                    clean_content = await self.message_to_text(message)
                except IndexError:
                    break
                if clean_content is None:
                    continue
                # Append
                prompt_token_count_so_far += len(encoding.encode(clean_content))
                history.append(
                    HistoricalMessage(
                        author_display_name_with_id=author_display_name_with_id,
                        clean_content=clean_content,
                    )
                )
                if prompt_token_count_so_far > self.TOKEN_LIMIT:
                    break
            history.reverse()

            now = dt.datetime.now()
            prompt_messages = [
                {
                    "role": "system",
                    "content": self.INITIAL_PROMPT.format(
                        channel_name=ctx.channel.name,
                        server_name=ctx.guild.name,
                        date=now.strftime("%A, %d.%m.%Y"),
                        time=now.strftime("%H:%M"),
                        command_prefix=configuration["command_prefix"],
                    ),
                },
                *(
                    {
                        "role": "user" if m.author_display_name_with_id else "assistant",
                        "content": f"{m.author_display_name_with_id}: {m.clean_content}"
                        if m.author_display_name_with_id
                        else m.clean_content,
                    }
                    for m in history
                ),
            ]

        final_message = "Nie udało mi się wykonać zadania. 😔"
        reply_resulted_in_command_message = False
        for iterations_left in range(self.ITERATION_LIMIT - 1, -1, -1):
            async with ctx.typing():
                iteration_result = await aclient.chat.completions.create(
                    model="gpt-4o",
                    messages=prompt_messages,
                    user=str(ctx.author.id),
                    tools=[{"function": f, "type": "function"} for f in self._all_available_commands_as_tools],
                )
                iteration_choice = iteration_result.choices[0]
                if iteration_choice.finish_reason == "tool_calls":
                    function_call = iteration_choice.message.tool_calls[0].function
                    command_invocation = f"{function_call.name.replace('_', ' ')} {' '.join(json.loads(function_call.arguments).values())}"
                    prompt_messages.append(
                        {
                            "role": "assistant",
                            "content": f"Wywołuję komendę `{command_invocation}`.",
                        }
                    )

                    command_view = StringView(command_invocation)
                    command_ctx = commands.Context(
                        prefix=None,
                        view=command_view,
                        bot=self.bot,
                        message=ctx.message,
                    )
                    command_ctx._is_ai_tool_call = True  # Enabled cooldown bypass
                    invoker = command_view.get_word()
                    if invoker not in self.bot.all_commands:
                        prompt_messages.append(
                            {
                                "role": "user",
                                "content": f"Komenda `{invoker}` nie istnieje.",
                            }
                        )
                        continue
                    command_ctx.invoked_with = invoker
                    command_ctx.command = self.bot.all_commands[invoker]
                    await self.bot.invoke(command_ctx)
                    resulting_message_content: Optional[str] = None
                    async for message in ctx.history(limit=10):
                        if message.author == ctx.me:
                            # Found a message which probably resulted from the tool's command invocation
                            reply_resulted_in_command_message = True
                            resulting_message_content = await self.message_to_text(command_ctx, message)
                            if resulting_message_content and "⚠️" in resulting_message_content:
                                # There was some error, which hopefully we'll correct on next try
                                await message.delete()
                                reply_resulted_in_command_message = False
                            break
                        elif message == ctx.message:
                            # No message was sent by the invoked command
                            bot_reaction_emojis = [reaction.emoji for reaction in ctx.message.reactions if reaction.me]
                            resulting_message_content = f"Jej wynik w postaci emoji: {''.join(bot_reaction_emojis)}"
                            break
                    prompt_messages.append(
                        {
                            "role": "user",
                            "content": "Komenda nie dała rezultatu w postaci wiadomości."
                            if not resulting_message_content
                            else f"Rezultat komendy to:\n{resulting_message_content}",
                        }
                    )
                    prompt_messages.append(
                        {
                            "role": "user",
                            "content": "Nie możesz już wykonać kolejnej komendy!"
                            if iterations_left == 1
                            else f"Spróbuj ponownie naprawiając wskazany błąd. Masz do wykorzystania jeszcze {word_number_form(iterations_left, 'komendę','komendy', 'komend')}."
                            if resulting_message_content and "⚠️" in resulting_message_content
                            else f"Jeśli w powyższym wyniku brakuje informacji w sprawie mojej prośby, spróbuj ponownie z inną komendą. Masz do wykorzystania jeszcze {word_number_form(iterations_left, 'komendę','komendy', 'komend')}. Nie ponawiaj komendy bez znaczących zmian.",
                        }
                    )
                else:
                    final_message = iteration_choice.message.content.strip()
                    break

        await self.bot.send(ctx, final_message, reply=not reply_resulted_in_command_message)

    @hey.error
    async def hey_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"Zmęczyłem się na tym kanale… wróćmy do rozmowy za {human_amount_of_time(error.retry_after)}. 😴"
            )
        else:
            raise error

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        ctx = await self.bot.get_context(message)
        if (
            ctx.command is None
            and ctx.guild is not None
            and ctx.guild.id in AI_ALLOWED_SERVER_IDS
            and not ctx.author.bot
            and ctx.me.id in message.raw_mentions
            and not ctx.message.clean_content.strip().startswith(self.COMMENT_MARKER)
        ):
            ctx.command = self.hey
            await self.bot.invoke(ctx)


async def setup(bot: Somsiad):
    await bot.add_cog(Chat(bot))
