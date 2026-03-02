"""List TeamCity projects using bearer token auth.

Usage:
    python -m tests.script_list_projects
"""

import logging
import sys
import warnings

import urllib3

from aurumaide.utility.logger import initialize
from aurumaide.utility.teamcity import TeamCityClient, TeamCityError


def main() -> int:
    initialize()

    # Suppress InsecureRequestWarning from console; route to file log instead
    warnings.filterwarnings(
        "ignore", category=urllib3.exceptions.InsecureRequestWarning
    )
    logging.captureWarnings(True)

    try:
        client = TeamCityClient(verify_ssl=False)
    except TeamCityError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    try:
        projects = client.list_projects()
    except TeamCityError as exc:
        print(f"Failed to list projects: {exc}", file=sys.stderr)
        return 1

    if not projects:
        print("No projects found.")
        return 0

    print(f"Found {len(projects)} project(s):\n")
    for i, project in enumerate(projects, 1):
        print(f"  {i:>3}. {project.name}")
        print(f"       ID:   {project.id}")
        if project.href:
            print(f"       href: {project.href}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
