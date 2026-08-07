#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys

import yaml


def load_config(filename):
    if not filename or not Path(filename).exists():
        return {}

    with open(filename, "r", encoding="utf-8") as f:
        document = yaml.safe_load(f) or {}

    tribes = document.get("tribes", {})

    if not isinstance(tribes, dict):
        raise ValueError("'tribes' must be a YAML mapping")

    result = {}

    for tribe, config in tribes.items():

        if not isinstance(config, dict):
            raise ValueError(
                f"Configuration for tribe '{tribe}' must be a mapping"
            )

        enabled = config.get("enabled", False)
        allowed_projects = config.get("allowed_projects", [])

        if not isinstance(enabled, bool):
            raise ValueError(
                f"'enabled' for tribe '{tribe}' must be true or false"
            )

        if not isinstance(allowed_projects, list):
            raise ValueError(
                f"'allowed_projects' for tribe '{tribe}' must be a list"
            )

        if not allowed_projects:
            raise ValueError(
                f"Tribe '{tribe}' must contain at least one allowed project"
            )

        result[tribe] = {
            "enabled": enabled,
            "allowed_projects": sorted(
                str(project) for project in allowed_projects
            ),
        }

    return result


def load_changed_files(filename):
    if not Path(filename).exists():
        return []

    with open(filename, "r", encoding="utf-8") as f:
        return [
            line.strip().lstrip("./")
            for line in f
            if line.strip()
        ]


def application_sets_for_tribe(tribe):
    tribe_path = Path(tribe)

    if not tribe_path.exists():
        return []

    return [
        str(path)
        for path in tribe_path.glob("*/applicationset.yaml")
        if path.is_file()
    ]


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        required=True,
        help="Current tribe/project configuration",
    )

    parser.add_argument(
        "--base-config",
        required=False,
        help="Configuration from the base commit",
    )

    parser.add_argument(
        "--changed-files",
        required=True,
        help="File containing changed ApplicationSet paths",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output file containing ApplicationSets to process",
    )

    parser.add_argument(
        "--all-enabled",
        action="store_true",
        help="Select all ApplicationSets belonging to enabled tribes",
    )

    args = parser.parse_args()

    try:
        current_config = load_config(args.config)
        base_config = load_config(args.base_config)

    except Exception as exc:
        print(f"ERROR: Invalid tribe configuration: {exc}")
        sys.exit(1)

    enabled_tribes = {
        tribe
        for tribe, config in current_config.items()
        if config["enabled"]
    }

    print()
    print("============================================================")
    print("Enabled tribes")
    print("============================================================")

    for tribe in sorted(enabled_tribes):
        projects = ", ".join(
            current_config[tribe]["allowed_projects"]
        )

        print(f"{tribe}: {projects}")

    selected = set()

    # --------------------------------------------------------
    # workflow_dispatch
    #
    # Process ALL ApplicationSets from enabled tribes.
    # --------------------------------------------------------

    if args.all_enabled:

        for tribe in enabled_tribes:

            for filename in application_sets_for_tribe(tribe):
                selected.add(filename)

    else:

        # ----------------------------------------------------
        # Normal PR / push behavior:
        #
        # Select changed ApplicationSets only if their tribe
        # is currently enabled.
        # ----------------------------------------------------

        changed_files = load_changed_files(
            args.changed_files
        )

        print()
        print("============================================================")
        print("Changed ApplicationSets")
        print("============================================================")

        for filename in changed_files:

            path = Path(filename)

            if len(path.parts) != 3:
                print(
                    f"SKIPPED: {filename} "
                    "(unexpected directory structure)"
                )
                continue

            tribe = path.parts[0]

            if tribe not in current_config:
                print(
                    f"SKIPPED: {filename} "
                    f"(tribe '{tribe}' is not configured)"
                )
                continue

            if not current_config[tribe]["enabled"]:
                print(
                    f"SKIPPED: {filename} "
                    f"(tribe '{tribe}' is disabled)"
                )
                continue

            print(f"SELECTED: {filename}")
            selected.add(filename)

        # ----------------------------------------------------
        # Configuration changes
        #
        # If an enabled tribe's configuration changed,
        # process ALL of its ApplicationSets.
        #
        # This handles:
        #
        # enabled: false -> true
        #
        # and changes to allowed_projects.
        # ----------------------------------------------------

        print()
        print("============================================================")
        print("Tribe configuration changes")
        print("============================================================")

        for tribe in sorted(enabled_tribes):

            current = current_config.get(tribe)
            previous = base_config.get(tribe)

            if current != previous:

                print(
                    f"Configuration changed for enabled tribe: {tribe}"
                )

                for filename in application_sets_for_tribe(tribe):

                    print(
                        f"SELECTED due to config change: {filename}"
                    )

                    selected.add(filename)

    # --------------------------------------------------------
    # Write result
    # --------------------------------------------------------

    selected = sorted(selected)

    with open(args.output, "w", encoding="utf-8") as f:

        for filename in selected:
            f.write(filename + "\n")

    print()
    print("============================================================")
    print("ApplicationSets selected")
    print("============================================================")

    if not selected:
        print("None")

    for filename in selected:
        print(filename)

    print()
    print(f"Total: {len(selected)}")


if __name__ == "__main__":
    main()