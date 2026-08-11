#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys

import yaml


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        required=True,
        help="Environment to cluster config file",
    )

    parser.add_argument(
        "--environment",
        required=True,
        help="Environment name or directory name",
    )

    args = parser.parse_args()

    config_file = Path(args.config)
    environment = args.environment.strip()

    if not config_file.exists():
        print(
            f"ERROR: Config file does not exist: {config_file}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not environment:
        print("ERROR: Environment cannot be empty", file=sys.stderr)
        sys.exit(1)

    if "/" in environment or "\\" in environment:
        print(
            f"ERROR: Invalid environment '{environment}'. "
            "Environment must be a directory name only.",
            file=sys.stderr,
        )
        sys.exit(1)

    if environment in [".", ".."]:
        print(
            f"ERROR: Invalid environment '{environment}'.",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(config_file, "r", encoding="utf-8") as f:
        document = yaml.safe_load(f) or {}

    allowed_clusters = document.get("allowed_clusters", [])
    environments = document.get("environments", {})

    if allowed_clusters and not isinstance(allowed_clusters, list):
        print(
            "ERROR: 'allowed_clusters' must be a YAML list",
            file=sys.stderr,
        )
        sys.exit(1)

    if not isinstance(environments, dict):
        print(
            "ERROR: 'environments' must be a YAML mapping",
            file=sys.stderr,
        )
        sys.exit(1)

    if environment not in environments:
        print(
            f"ERROR: Environment '{environment}' is not configured in {config_file}",
            file=sys.stderr,
        )
        print(file=sys.stderr)
        print("Configured environments:", file=sys.stderr)

        for configured_environment in sorted(environments.keys()):
            print(f"  - {configured_environment}", file=sys.stderr)

        sys.exit(1)

    environment_config = environments[environment]

    if not isinstance(environment_config, dict):
        print(
            f"ERROR: Environment '{environment}' must be a mapping",
            file=sys.stderr,
        )
        sys.exit(1)

    cluster = environment_config.get("cluster")

    if not cluster:
        print(
            f"ERROR: Environment '{environment}' does not define a cluster",
            file=sys.stderr,
        )
        sys.exit(1)

    cluster = str(cluster).strip()

    if allowed_clusters and cluster not in allowed_clusters:
        print(
            f"ERROR: Cluster '{cluster}' for environment '{environment}' "
            "is not listed in allowed_clusters",
            file=sys.stderr,
        )
        sys.exit(1)

    print(cluster)


if __name__ == "__main__":
    main()