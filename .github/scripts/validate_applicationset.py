#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys

import yaml


def load_config(filename):
    with open(filename, "r", encoding="utf-8") as f:
        document = yaml.safe_load(f) or {}

    tribes = document.get("tribes", {})

    if not isinstance(tribes, dict):
        raise ValueError("'tribes' must be a YAML mapping")

    return tribes


def load_files(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return [
            line.strip()
            for line in f
            if line.strip()
        ]


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        required=True,
        help="Tribe/project configuration",
    )

    parser.add_argument(
        "--files",
        required=True,
        help="ApplicationSets to validate",
    )

    args = parser.parse_args()

    config = load_config(args.config)
    filenames = load_files(args.files)

    if not filenames:
        print("No enabled ApplicationSets to validate.")
        return

    errors = []

    for filename in filenames:
        path = Path(filename)

        print()
        print("============================================================")
        print(f"Validating: {filename}")
        print("============================================================")

        # ----------------------------------------------------
        # Validate directory structure:
        #
        # <tribe>/<environment>/applicationset.yaml
        # ----------------------------------------------------

        if len(path.parts) != 3:
            errors.append(
                f"{filename}: invalid path. Expected "
                "<tribe>/<environment>/applicationset.yaml"
            )

            continue

        tribe = path.parts[0]
        environment = path.parts[1]

        print(f"Tribe:       {tribe}")
        print(f"Environment: {environment}")

        # ----------------------------------------------------
        # Validate tribe exists and is enabled
        # ----------------------------------------------------

        if tribe not in config:
            errors.append(
                f"{filename}: tribe '{tribe}' is not configured"
            )

            continue

        tribe_config = config[tribe]

        if not tribe_config.get("enabled", False):
            errors.append(
                f"{filename}: tribe '{tribe}' is not enabled"
            )

            continue

        allowed_projects = tribe_config.get(
            "allowed_projects",
            [],
        )

        if not allowed_projects:
            errors.append(
                f"{filename}: no allowed projects configured "
                f"for tribe '{tribe}'"
            )

            continue

        print(
            "Allowed projects: "
            + ", ".join(allowed_projects)
        )

        # ----------------------------------------------------
        # Parse YAML
        # ----------------------------------------------------

        try:
            with open(
                filename,
                "r",
                encoding="utf-8",
            ) as f:
                manifest = yaml.safe_load(f)

        except Exception as exc:
            errors.append(
                f"{filename}: YAML parsing error: {exc}"
            )

            continue

        if not isinstance(manifest, dict):
            errors.append(
                f"{filename}: YAML document must contain an object"
            )

            continue

        # ----------------------------------------------------
        # apiVersion
        # ----------------------------------------------------

        api_version = manifest.get("apiVersion")

        if api_version != "argoproj.io/v1alpha1":
            errors.append(
                f"{filename}: apiVersion must be "
                "'argoproj.io/v1alpha1'"
            )

        # ----------------------------------------------------
        # kind
        # ----------------------------------------------------

        kind = manifest.get("kind")

        if kind != "ApplicationSet":
            errors.append(
                f"{filename}: kind must be 'ApplicationSet'"
            )

        # ----------------------------------------------------
        # metadata
        # ----------------------------------------------------

        metadata = manifest.get("metadata")

        if not isinstance(metadata, dict):
            errors.append(
                f"{filename}: metadata is required"
            )

        elif not metadata.get("name"):
            errors.append(
                f"{filename}: metadata.name is required"
            )

        # ----------------------------------------------------
        # spec
        # ----------------------------------------------------

        spec = manifest.get("spec")

        if not isinstance(spec, dict):
            errors.append(
                f"{filename}: spec is required"
            )

            continue

        if not spec.get("generators"):
            errors.append(
                f"{filename}: spec.generators is required"
            )

        # ----------------------------------------------------
        # template
        # ----------------------------------------------------

        template = spec.get("template")

        if not isinstance(template, dict):
            errors.append(
                f"{filename}: spec.template is required"
            )

            continue

        template_spec = template.get("spec")

        if not isinstance(template_spec, dict):
            errors.append(
                f"{filename}: spec.template.spec is required"
            )

            continue

        # ----------------------------------------------------
        # Argo CD project
        # ----------------------------------------------------

        project = template_spec.get("project")

        if not project:
            errors.append(
                f"{filename}: "
                "spec.template.spec.project is required"
            )

            continue

        print(f"Actual project:  {project}")

        # ----------------------------------------------------
        # Validate project against tribe mapping
        # ----------------------------------------------------

        if project not in allowed_projects:
            errors.append(
                f"{filename}: Argo CD project '{project}' "
                f"is not allowed for tribe '{tribe}'. "
                f"Allowed projects: "
                f"{', '.join(allowed_projects)}"
            )

            print("Result:          FAIL")

        else:
            print("Result:          PASS")

    if errors:
        print()
        print("============================================================")
        print("APPLICATIONSET VALIDATION FAILED")
        print("============================================================")

        for error in errors:
            print(f"ERROR: {error}")

        sys.exit(1)

    print()
    print("============================================================")
    print("All ApplicationSets passed validation.")
    print("============================================================")


if __name__ == "__main__":
    main()