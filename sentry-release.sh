#!/usr/bin/env bash

# Copyright 2019 Twixes

# This file is part of Somsiad - the Polish Discord bot.

# Somsiad is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

# Somsiad is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with Somsiad.
# If not, see <https://www.gnu.org/licenses/>.

source ./.env
VERSION=$(./version.py)
sentry-cli releases new -p "${SENTRY_PROJ:-somsiad}" "${SENTRY_PROJ:-somsiad}@$VERSION" --finalize
sentry-cli releases set-commits --auto "${SENTRY_PROJ:-somsiad}@$VERSION"