# Copyright 2018 ondondil & Twixes

# This file is part of Somsiad - the Polish Discord bot

# Somsiad is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# Somsiad is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with Somsiad.
# If not, see <https://www.gnu.org/licenses/>.

import os
from discord.ext.commands import Bot

class Configurator:
    configuration_file_path = None
    configuration_file = None
    configuration_required = None
    configuration = {}

    def __init__(self, configuration_file_path, configuration_required=None):
        self.configuration_file_path = configuration_file_path
        self.configuration_required = configuration_required

        if configuration_required is None:
            self.read()
        else:
            self.ensure_completeness()

    def write_key_value(self, key, value):
        """Writes a key-value pair to the configuration file."""
        with open(self.configuration_file_path, 'a') as self.configuration_file:
            self.configuration_file.write(f'{key}={self.configuration[key]}\n')

    def obtain_key_value(self, key, default_value, instruction, step_number=None):
        """Asks the CLI user to input a setting."""
        while True:
            if step_number is None:
                self.configuration[key] = input(f'{instruction}:\n')
            else:
                self.configuration[key] = input(f'{step_number}. {instruction}:\n')

            if self.configuration[key].strip() == '':
                if default_value is None:
                    continue
                else:
                    self.configuration[key] = default_value
                    break
            else:
                break

        self.write_key_value(key, self.configuration[key])

    def ensure_completeness(self):
        """Loads the configuration from the file specified during class initialization and ensures
            that all required keys are present. If not, the CLI user is asked to input missing settings.
            If the file doesn't exist yet, configuration is started from scratch."""
        was_configuration_changed = False
        step_number = 1

        if os.path.exists(self.configuration_file_path):
            self.read()

        if self.configuration_required is not None:
            if self.configuration is {} or self.configuration is None:
                for key_required in self.configuration_required:
                    self.obtain_key_value(key_required[0], key_required[1], key_required[2], step_number)
                    step_number += 1
                was_configuration_changed = True
            else:
                for key_required in self.configuration_required:
                    is_key_required_present = False
                    for key in self.configuration:
                        if key == key_required[0]:
                            is_key_required_present = True
                            break
                    if not is_key_required_present:
                        self.obtain_key_value(key_required[0], key_required[1], key_required[2], step_number)
                        was_configuration_changed = True
                    step_number += 1

        if was_configuration_changed:
            print(f'Gotowe! Konfigurację zapisano w {self.configuration_file_path}.')

        return self.configuration

    def read(self):
        """Loads the configuration from the file specified during class initialization."""
        with open(self.configuration_file_path, 'r') as self.configuration_file:
            for line in self.configuration_file.readlines():
                if not line.strip().startswith('#'):
                    line = line.strip().split('=')
                    self.configuration[line[0].strip()] = line[1].strip() if len(line) >= 2 else None

        return self.configuration

    def info(self, verbose=False):
        """Returns a string presenting the current configuration in a human-readable form. Can print to the console."""
        if self.configuration_required is not None:
            info = ''
            for key_required in self.configuration_required:
                if key_required[4] is None:
                    line = f'{key_required[3]}: {self.configuration[key_required[0]]}'
                elif key_required[4] == 'password':
                    line = f'{key_required[3]}: {"*" * len(self.configuration[key_required[0]])}'
                elif isinstance(key_required[4], tuple) and len(key_required[4]) == 2:
                    unit_noun_variant = key_required[4][0] if int(conf[key_required[0]]) == 1 else key_required[4][1]
                    line = f'{key_required[3]}: {self.configuration[key_required[0]]} {unit_noun_variant}'
                else:
                    line = f'{key_required[3]}: {self.configuration[key_required[0]]} {key_required[4]}'
                info += line + '\n'
                if verbose: print(line)

            line = f'Ścieżka pliku konfiguracyjnego: {self.configuration_file_path}'
            info += line + '\n'
            if verbose: print(line)

            return info.strip('\n')

def get_fellow_server_member(server, args):
    if len(args) == 1 and args[0].startswith('<@') and args[0].endswith('>'):
        user = server.get_member(int(args[0].strip('<@!>')))
    else:
        username = ''
        for arg in args:
            username += arg + ' '
        username = username.strip()
        user = server.get_member_named(username)

    return user

def does_member_have_elevated_permissions(member):
    return member.guild_permissions.administrator

# Initialize configuration
conf_required = [
    # (key, default_value, instruction, description, unit,)
    ('discord_token', None, 'Wprowadź discordowy token bota', 'Token bota', None,),
    ('google_key', None, 'Wprowadź klucz API Google', 'Klucz API Google', None,),
    ('reddit_id', None, 'Wprowadź ID aplikacji redditowej', 'ID aplikacji redditowej', None,),
    ('reddit_secret', None, 'Wprowadź szyfr aplikacji redditowej', 'Szyfr aplikacji redditowej', None,),
    ('reddit_username', None, 'Wprowadź redditową nazwę użytkownika', 'Redditowa nazwa użytkownika', None,),
    ('reddit_password', None, 'Wprowadź hasło do konta na Reddicie', 'Hasło do konta na Reddicie', 'password',),
    ('reddit_account_min_age_days', 14, 'Wprowadź minimalny wiek weryfikowanego konta na Reddicie '
        '(w dniach, domyślnie 14)', 'Minimalny wiek weryfikowanego konta na Reddicie', ('dzień', 'dni',),),
    ('reddit_account_min_karma', 0, 'Wprowadź minimalną karmę weryfikowanego konta na Reddicie (domyślnie 0)',
        'Minimalna karma weryfikowanego konta na Reddicie', None,),
    ('goodreads_key', None, 'Wprowadź klucz API Goodreads', 'Klucz API Goodreads', None,),
    ('user_command_cooldown_seconds', 1, 'Wprowadź cooldown wywołania komendy przez użytkownika '
        '(w sekundach, domyślnie 1)', 'Cooldown wywołania komendy przez użytkownika', ('sekunda', 'sekund',),),
    ('command_prefix', '!', 'Wprowadź prefiks komend (domyślnie !)', 'Prefiks komend', None),
]

conf_file_path = os.path.join(os.path.expanduser('~'), '.config', 'somsiad.conf')
configurator = Configurator(conf_file_path, conf_required)
conf = configurator.configuration

bot_dir = os.getcwd()

brand_color = 0x7289da

client = Bot(description='Zawsze pomocny Somsiad', command_prefix=conf['command_prefix'])

client.remove_command('help') # Replaced with the 'help_direct' plugin
