"""Download a TeamCity build log and save it to the default out directory.

Looks up a build by its display number and build-type ID to resolve the
internal build ID, then downloads the full log.

Usage:
    python -m tests.script_download_build_log [BUILD_NUMBER [BUILD_TYPE_ID]]

Defaults to build #2574 of GitRc2_CiReleasePackage.
"""

import logging
import os
import sys
import warnings
from typing import Any

import urllib3

from aurumaide.teamcity.client import TeamCityClient, TeamCityError
from aurumaide.utility.logger import get_out_dir, get_timestamp, initialize

DEFAULT_BUILD_NUMBER = "2574"
DEFAULT_BUILD_TYPE_ID = "GitRc2_CiReleasePackage"


def _find_build_by_number(
    client: TeamCityClient,
    build_number: str,
    build_type_id: str,
) -> dict[str, Any] | None:
    """Resolve a build number + type to a full build dict."""
    locator = (
        f"buildType:{build_type_id},"
        f"number:{build_number},"
        "count:1"
    )
    data = client._get("/app/rest/builds", params={"locator": locator})
    builds: list[dict[str, Any]] = data.get("build", [])
    return builds[0] if builds else None


def main() -> int:
    initialize()

    warnings.filterwarnings(
        "ignore", category=urllib3.exceptions.InsecureRequestWarning
    )
    logging.captureWarnings(True)

    build_number = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BUILD_NUMBER
    build_type_id = (
        sys.argv[2] if len(sys.argv) > 2 else DEFAULT_BUILD_TYPE_ID
    )

    try:
        client = TeamCityClient(verify_ssl=False)
    except TeamCityError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    # Resolve build number → internal ID
    print(
        f"Looking up build #{build_number} "
        f"in {build_type_id}..."
    )
    try:
        raw = _find_build_by_number(client, build_number, build_type_id)
    except TeamCityError as exc:
        print(f"Failed to look up build: {exc}", file=sys.stderr)
        return 1

    if raw is None:
        print(
            f"Build #{build_number} not found in {build_type_id}.",
            file=sys.stderr,
        )
        return 1

    build = client._parse_build(raw)
    print(
        f"Found build id={build.id}  status={build.status}  "
        f"branch={build.branch}"
    )

    # Download log
    print("Downloading build log...")
    try:
        log_text = client.download_build_log(build.id)
    except TeamCityError as exc:
        print(f"Failed to download build log: {exc}", file=sys.stderr)
        return 1

    stamp = get_timestamp(timespec="seconds")
    filename = f"build-{build_number}-{stamp}.log"
    path = os.path.join(get_out_dir(), filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(log_text)

    print(f"Saved to {path} ({len(log_text)} characters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
