"""Print a hash of a new site password, for the SITE_PASSWORD_HASH setting.

Usage: `uv run hash-password`. The password is read without being shown and
never written anywhere; only the hash is printed.
"""

import sys
from getpass import getpass

from games_server.auth.passwords import hash_password


def main() -> None:
    password = getpass("New site password: ")
    if not password:
        sys.exit("The password must not be empty.")
    if getpass("Repeat it: ") != password:
        sys.exit("The passwords did not match.")
    print(hash_password(password))


if __name__ == "__main__":
    main()
