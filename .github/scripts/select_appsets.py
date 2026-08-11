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


def environment_to_directory(environment):
    environment = environment.strip()

    if not environment:
        raise ValueError("Environment cannot be empty")

    if "/" in environment or "\\" in environment:
        raise ValueError(
            f"Invalid environment '{environment}'. "
            "Environment must be a directory name only."
        )

    if environment in [".", ".."]:
        raise ValueError(
            f"Invalid environment '{environment}'."
        )

    return environment


def application_sets_for_tribe(tribe):
    tribe_path = Path(tribe)

    if not tribe_path.exists():
        return []

    return sorted(
        str(path)
        for path in tribe_path.glob("*/applicationset.yaml")
        if path.is_file()
    )


def validate_target_tribe(target_tribe, current_config):
    if not target_tribe:
        print("ERROR: --target-tribe was provided but is empty.")
        sys.exit(1)

    if "/" in target_tribe or "\\" in target_tribe:
        print("ERROR: target tribe must be a directory name only.")
        print(f"Received: {target_tribe}")
        sys.exit(1)

    if target_tribe not in current_config:
        print()
        print("ERROR: Target tribe is not configured.")
        print(f"Target tribe: {target_tribe}")
        print()
        print("Configured tribes:")

        for tribe in sorted(current_config.keys()):
            print(f"  - {tribe}")

        sys.exit(1)

    if not current_config[target_tribe]["enabled"]:
        print()
        print("ERROR: Target tribe is configured but not enabled.")
        print(f"Target tribe: {target_tribe}")
        print()
        print("Enable it first in:")
        print()
        print("  .github/config/tribe-projects.yaml")
        print()
        print("Example:")
        print()
        print(f"{target_tribe}:")
        print("  enabled: true")

        sys.exit(1)


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

    parser.add_argument(
        "--target-tribe",
        required=False,
        help="Select only ApplicationSets for one tribe",
    )

    parser.add_argument(
        "--target-environment",
        required=False,
        help="Select only one environment",
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

    if args.target_tribe or args.target_environment:
        if not args.target_tribe or not args.target_environment:
            print()
            print("ERROR: --target-tribe and --target-environment must be used together.")
            sys.exit(1)

        target_tribe = args.target_tribe.strip()
        target_environment = args.target_environment.strip()
        target_directory = environment_to_directory(target_environment)

        print()
        print("============================================================")
        print("Target selection")
        print("============================================================")
        print(f"Target tribe:       {target_tribe}")
        print(f"Target environment: {target_environment}")
        print(f"Target directory:   {target_directory}")

        validate_target_tribe(
            target_tribe,
            current_config,
        )

        target_file = (
            Path(target_tribe)
            / target_directory
            / "applicationset.yaml"
        )

        if not target_file.exists():
            print()
            print("ERROR: Selected ApplicationSet file does not exist.")
            print(f"Expected file: {target_file}")
            print()
            print("Environment and directory names are expected to match.")
            print()
            print("Examples:")
            print("  target_environment dev    -> directory dev")
            print("  target_environment uat    -> directory uat")
            print("  target_environment prd    -> directory prd")
            print("  target_environment int-au -> directory int-au")
            sys.exit(1)

        print(f"SELECTED: {target_file}")
        selected.add(str(target_file))

    elif args.all_enabled:
        for tribe in enabled_tribes:
            for filename in application_sets_for_tribe(tribe):
                selected.add(filename)

    else:
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