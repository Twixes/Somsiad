#!/usr/bin/env python3

# Copyright 2019 Twixes

# This file is part of Somsiad - the Polish Discord bot.

# Somsiad is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# Somsiad is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with Somsiad.
# If not, see <https://www.gnu.org/licenses/>.

from typing import Union, Tuple, List
import sys
import os
import sqlite3
import json
import data


class ServerDataManager:
    """Handles server-specific data."""
    servers_db_path = os.path.join(os.path.expanduser('~'), '.local', 'share', 'somsiad', 'servers.db')

    @staticmethod
    def dict_from_row(row: sqlite3.Row) -> dict:
        """Unpacks an sqlite3.Row object into a dictionary."""
        if row is None:
            return None
        else:
            return dict(zip(row.keys(), row))

    def __init__(self):
        """Connects to the servers database. Creates it if it doesn't exist yet.
        Creates a table containing known servers.
        """
        self.servers = {
            'ids': []
        }
        self.servers_db = sqlite3.connect(self.servers_db_path)
        self.servers_db.row_factory = sqlite3.Row
        self.servers_db_cursor = self.servers_db.cursor()
        self.servers_db_cursor.execute(
            '''CREATE TABLE IF NOT EXISTS servers(
                server_id INTEGER NOT NULL PRIMARY KEY
            )'''
        )
        self.servers_db.commit()
        self.load_all_server_dbs()

    def is_server_known(self, server_id: int) -> bool:
        """Returns whether the specified server is known."""
        return bool(server_id in self.load_servers_list())

    def load_servers_list(self) -> list:
        """Loads IDs of all known servers from the servers database."""
        self.servers_db_cursor.execute(
            'SELECT server_id FROM servers'
        )
        self.servers['ids'] = [int(server['server_id']) for server in self.servers_db_cursor.fetchall()]
        return self.servers['ids']

    def load_server(self, server_id: int, load_own_db: bool = True) -> dict:
        """Loads the specified server."""
        if not self.is_server_known(server_id):
            self.servers_db_cursor.execute(
                'INSERT INTO servers(server_id) VALUES(?)',
                (server_id,)
            )
            self.servers_db.commit()

        self.servers[server_id] = {}
        self.servers_db_cursor.execute(
            'SELECT * FROM servers WHERE server_id = ?',
            (server_id,)
        )
        self.servers[server_id].update(self.dict_from_row(self.servers_db_cursor.fetchone()))
        self.servers_db.commit()

        self.servers_db_cursor.execute(
            'SELECT * FROM pin_archive_channels WHERE server_id = ?',
            (server_id,)
        )
        pin = self.dict_from_row(self.servers_db_cursor.fetchone())
        if pin is not None: self.servers[server_id]['pin_channel_id'] = pin['channel_id']
        self.servers_db.commit()

        if load_own_db:
            self.load_own_server_db(server_id)

        return self.servers[server_id]

    def load_own_server_db(self, server_id: int) -> dict:
        """Load the specified server's own database."""
        server_db_path = os.path.join(os.path.expanduser('~'), '.local', 'share', 'somsiad', f'server_{server_id}.db')

        self.servers[server_id]['db'] = sqlite3.connect(server_db_path)
        self.servers[server_id]['db'].row_factory = sqlite3.Row
        self.servers[server_id]['db_cursor'] = self.servers[server_id]['db'].cursor()
        self.servers[server_id]['db_cursor'].execute(
            'PRAGMA foreign_keys = ON'
        )
        self.servers[server_id]['db'].commit()
        self.servers[server_id]['db_cursor'].execute(
            'SELECT name FROM sqlite_master WHERE type = "table"'
        )

        tables = [table['name'] for table in self.servers[server_id]['db_cursor'].fetchall()]

        for table in tables:
            self.servers[server_id][table] = {}
            self.servers[server_id]['db_cursor'].execute(
                f'SELECT * FROM {table}'
            )
            rows = [self.dict_from_row(row) for row in self.servers[server_id]['db_cursor'].fetchall()]
            self.servers[server_id][table] = rows

        return self.servers[server_id]

    def load_all_server_dbs(self) -> dict:
        """Loads all known servers."""
        for server_id in self.load_servers_list():
            self.load_server(server_id)
        return self.servers

    def ensure_table_existence_for_server(
            self, server_id: int, table_name: str, table_columns: Union[List[str], Tuple[str]]
    ):
        """Ensures that a table with the provided name exists in the database assigned to the server.
        If no such table exists, it is created with provided column specs.
        """
        self.load_server(server_id, load_own_db=True)
        self.servers[server_id]['db_cursor'].execute(
            f'CREATE TABLE IF NOT EXISTS {table_name}({", ".join(table_columns)})'
        )
        self.servers[server_id]['db'].commit()
        self.load_server(server_id, load_own_db=True)


class PinArchive(data.Base):
    server_id = data.Column(data.BigInteger, data.ForeignKey('servers.id'), primary_key=True)
    channel_id = data.Column(data.BigInteger)


server_data_manager = ServerDataManager()
server_data_manager.servers.pop('ids')

def migrate_from_db_to_sqlalchemy_pins():
    session = data.Session()
    session.add_all([
        PinArchive(server_id=server_id, channel_id=x['pin_channel_id'])
        for server_id, x in server_data_manager.servers.items() if 'pin_channel_id' in x
    ])
    session.commit()
    session.close()


def migrate_from_json_to_env():
    print('Migrating configuration from .json to .env... ')
    json_f_path = os.path.join(os.path.expanduser('~'), '.config', 'somsiad.json')
    env_f_path = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), '.env')
    if os.path.exists(json_f_path):
        with open(json_f_path, 'r') as json_f:
            configuration = json.load(json_f)
        with open(env_f_path, 'a') as env_f:
            for key, value in configuration.items():
                env_f.write(f'{key.upper()}={value}\n')
        os.remove(json_f_path)
        print(f'Done: moved from {json_f_path} to {env_f_path}')
    else:
        print(f'Skipped: no file at {json_f_path}')


if __name__ == '__main__':
    migrate_from_db_to_sqlalchemy_pins()
    migrate_from_json_to_env()