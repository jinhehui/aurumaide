"""Start a TeamCity build and print the queued build details.

Usage:
    python -m tests.script_start_build [BUILD_TYPE_ID [BRANCH]]

Defaults to GitRc2_ReleasePackage on the 'develop' branch.
"""

import logging
import sys
import warnings

import urllib3

from aurumaide.teamcity.client import TeamCityClient, TeamCityError
from aurumaide.utility.logger import initialize

DEFAULT_BUILD_TYPE_ID = "GitRc2_ReleasePackage"
DEFAULT_BRANCH = "develop"


def main() -> int:
    initialize()

    warnings.filterwarnings(
        "ignore", category=urllib3.exceptions.InsecureRequestWarning
    )
    logging.captureWarnings(True)

    build_type_id = (
        sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BUILD_TYPE_ID
    )
    branch = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_BRANCH

    try:
        client = TeamCityClient(verify_ssl=False)
    except TeamCityError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    print(f"Starting build {build_type_id} on branch '{branch}'...")

    try:
        build = client.start_build(
            build_type_id=build_type_id,
            branch=branch,
            personal=False,
        )
    except TeamCityError as exc:
        print(f"Failed to start build: {exc}", file=sys.stderr)
        return 1

    print("\nBuild queued successfully:\n")
    print(f"  ID:       {build.id}")
    if build.number:
        print(f"  Number:   #{build.number}")
    print(f"  State:    {build.state}")
    if build.status:
        print(f"  Status:   {build.status}")
    print(f"  Branch:   {build.branch}")
    print(f"  Personal: {build.personal}")
    if build.web_url:
        print(f"  URL:      {build.web_url}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
