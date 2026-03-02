"""List all build configurations in a TeamCity project with latest builds.

Looks up the project by name (case-insensitive), then lists its build
configurations together with the most recent finished build for each.

Usage:
    python -m tests.script_list_build_types [PROJECT_NAME]

Defaults to 'Quantifi' when no argument is given.
"""

import logging
import sys
import warnings
from typing import Any

import urllib3

from aurumaide.utility.logger import initialize
from aurumaide.utility.teamcity import (
    Build,
    Project,
    TeamCityAPIError,
    TeamCityClient,
    TeamCityError,
)

DEFAULT_PROJECT_NAME = "Quantifi"


def _find_project_by_name(
    client: TeamCityClient, name: str
) -> Project | None:
    """Return the first project whose name matches *name* (case-insensitive)."""
    projects = client.list_projects()
    for p in projects:
        if p.name.lower() == name.lower():
            return p
    return None


def _get_latest_build(
    client: TeamCityClient, build_type_id: str
) -> Build | None:
    """Return the latest finished build for *build_type_id*, or None."""
    try:
        return client.get_latest_build(build_type_id)
    except TeamCityAPIError as exc:
        if exc.status_code == 404:
            return None
        raise


def main() -> int:
    initialize()

    # Suppress InsecureRequestWarning from console; route to file log instead
    warnings.filterwarnings(
        "ignore", category=urllib3.exceptions.InsecureRequestWarning
    )
    logging.captureWarnings(True)

    project_name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROJECT_NAME

    try:
        client = TeamCityClient(verify_ssl=False)
    except TeamCityError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    try:
        project = _find_project_by_name(client, project_name)
    except TeamCityError as exc:
        print(f"Failed to list projects: {exc}", file=sys.stderr)
        return 1

    if project is None:
        print(f"Project '{project_name}' not found.\n", file=sys.stderr)
        print("Available projects:\n", file=sys.stderr)
        try:
            for p in client.list_projects():
                print(f"  {p.name:<30s}  (id: {p.id})", file=sys.stderr)
        except TeamCityError:
            pass
        return 1

    try:
        data = client._get(
            f"/app/rest/projects/id:{project.id}/buildTypes"
        )
    except TeamCityError as exc:
        print(f"Failed to list build types: {exc}", file=sys.stderr)
        return 1

    build_types: list[dict[str, Any]] = data.get("buildType", [])

    if not build_types:
        print(
            f"No build configurations found in "
            f"'{project.name}' (id: {project.id})."
        )
        return 0

    print(
        f"Found {len(build_types)} build configuration(s) in "
        f"'{project.name}' (id: {project.id}):\n"
    )
    for i, bt in enumerate(build_types, 1):
        bt_id: str = bt.get("id", "")
        print(f"  {i:>3}. {bt.get('name', '')}")
        print(f"       ID:        {bt_id}")
        if bt.get("projectId"):
            print(f"       Project:   {bt['projectId']}")
        if bt.get("href"):
            print(f"       href:      {bt['href']}")
        if bt.get("webUrl"):
            print(f"       URL:       {bt['webUrl']}")

        # Latest finished build
        build = _get_latest_build(client, bt_id)
        if build is None:
            print("       Build:     (none)")
        else:
            status = "OK" if build.status == "SUCCESS" else build.status
            print(f"       Build:     #{build.number}  {status}")
            if build.start_date:
                print(f"       Started:   {build.start_date}")
            if build.web_url:
                print(f"       Build URL: {build.web_url}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
