"""Create a TeamCity access token using basic auth.

Usage:
    python -m tests.script_create_token
"""

import getpass
import os
import sys
from datetime import UTC, datetime

from dotenv import load_dotenv

from aurumaide.utility.teamcity import TeamCityError
from aurumaide.utility.teamcity_token import TeamCityTokenManager


def main() -> int:
    load_dotenv()

    username = os.environ.get("TEAMCITY_USERNAME", "")
    if not username:
        username = input("TeamCity username: ")

    password = os.environ.get("TEAMCITY_PASSWORD", "")
    if not password:
        password = getpass.getpass("TeamCity password: ")

    try:
        mgr = TeamCityTokenManager(
            username=username,
            password=password,
            verify_ssl=False,
        )
    except TeamCityError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    token_name = f"aurumaide-{timestamp}"

    try:
        token = mgr.create_token(name=token_name)
    except TeamCityError as exc:
        print(f"Failed to create token: {exc}", file=sys.stderr)
        return 1

    print("Token created successfully:")
    print(f"  Name:       {token.name}")
    print(f"  Value:      {token.value}")
    if token.expiration_time:
        print(f"  Expires:    {token.expiration_time}")
    print()
    print("Save this value — it cannot be retrieved later.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
