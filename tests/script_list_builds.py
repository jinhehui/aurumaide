"""List the most recent finished build on 'develop' for every project.

Usage:
    python -m tests.script_list_builds
"""

import logging
import sys
import warnings
from typing import Any

import urllib3

from aurumaide.utility.logger import initialize
from aurumaide.utility.teamcity import TeamCityAPIError, TeamCityClient, TeamCityError

BRANCH = "develop"


def _get_latest_build_on_branch(
    client: TeamCityClient,
    project_id: str,
    branch: str,
) -> dict[str, Any] | None:
    """Return the single most recent finished build for *project_id* on *branch*."""
    locator = (
        f"project:(id:{project_id}),"
        f"branch:{branch},"
        "state:finished,"
        "count:1"
    )
    data = client._get("/app/rest/builds", params={"locator": locator})
    builds: list[dict[str, Any]] = data.get("build", [])
    return builds[0] if builds else None


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

    print(f"Latest finished builds on '{BRANCH}' branch:\n")

    found = 0
    for project in projects:
        try:
            raw = _get_latest_build_on_branch(client, project.id, BRANCH)
        except TeamCityAPIError as exc:
            if exc.status_code == 404:
                continue
            print(f"  {project.name}  -- error: {exc}")
            continue
        except TeamCityError as exc:
            print(f"  {project.name}  -- error: {exc}")
            continue

        if raw is None:
            continue

        found += 1
        build = client._parse_build(raw)
        status_icon = "OK" if build.status == "SUCCESS" else build.status
        print(f"  {project.name}")
        print(f"    Build:   #{build.number}  ({build.build_type_id})")
        print(f"    Status:  {status_icon}    State: {build.state}")
        if build.start_date:
            print(f"    Started: {build.start_date}")
        if build.web_url:
            print(f"    URL:     {build.web_url}")
        print()

    if not found:
        print(f"No finished builds found on '{BRANCH}' for any project.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
