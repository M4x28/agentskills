"""Skill validation logic."""

import unicodedata
from pathlib import Path
from typing import Optional

from .errors import ParseError
from .parser import find_skill_md, parse_frontmatter

MAX_SKILL_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500
MAX_PARAM_NAME_LENGTH = 64
MAX_PARAM_DESCRIPTION_LENGTH = 120

# Allowed frontmatter fields per Agent Skills Spec
ALLOWED_FIELDS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
    "parameters",
}


def _validate_name(name: str, skill_dir: Path) -> list[str]:
    """Validate skill name format and directory match.

    Skill names support i18n characters (Unicode letters) plus hyphens.
    Names must be lowercase and cannot start/end with hyphens.
    """
    errors = []

    if not name or not isinstance(name, str) or not name.strip():
        errors.append("Field 'name' must be a non-empty string")
        return errors

    name = unicodedata.normalize("NFKC", name.strip())

    if len(name) > MAX_SKILL_NAME_LENGTH:
        errors.append(
            f"Skill name '{name}' exceeds {MAX_SKILL_NAME_LENGTH} character limit "
            f"({len(name)} chars)"
        )

    if name != name.lower():
        errors.append(f"Skill name '{name}' must be lowercase")

    if name.startswith("-") or name.endswith("-"):
        errors.append("Skill name cannot start or end with a hyphen")

    if "--" in name:
        errors.append("Skill name cannot contain consecutive hyphens")

    if not all(c.isalnum() or c == "-" for c in name):
        errors.append(
            f"Skill name '{name}' contains invalid characters. "
            "Only letters, digits, and hyphens are allowed."
        )

    if skill_dir:
        dir_name = unicodedata.normalize("NFKC", skill_dir.name)
        if dir_name != name:
            errors.append(
                f"Directory name '{skill_dir.name}' must match skill name '{name}'"
            )

    return errors


def _validate_description(description: str) -> list[str]:
    """Validate description format."""
    errors = []

    if not description or not isinstance(description, str) or not description.strip():
        errors.append("Field 'description' must be a non-empty string")
        return errors

    if len(description) > MAX_DESCRIPTION_LENGTH:
        errors.append(
            f"Description exceeds {MAX_DESCRIPTION_LENGTH} character limit "
            f"({len(description)} chars)"
        )

    return errors


def _validate_compatibility(compatibility: str) -> list[str]:
    """Validate compatibility format."""
    errors = []

    if not isinstance(compatibility, str):
        errors.append("Field 'compatibility' must be a string")
        return errors

    if len(compatibility) > MAX_COMPATIBILITY_LENGTH:
        errors.append(
            f"Compatibility exceeds {MAX_COMPATIBILITY_LENGTH} character limit "
            f"({len(compatibility)} chars)"
        )

    return errors


def _validate_parameter_list(raw: object, block: str) -> list[str]:
    """Validate a ``required`` or ``optional`` parameter list."""
    errors: list[str] = []

    if not isinstance(raw, list):
        errors.append(f"parameters.{block} must be a list")
        return errors

    seen_names: set[str] = set()

    for i, item in enumerate(raw):
        prefix = f"parameters.{block}[{i}]"

        if not isinstance(item, dict):
            errors.append(f"{prefix} must be a mapping")
            continue

        # name
        if "name" not in item:
            errors.append(f"{prefix} is missing required key 'name'")
        else:
            pname = str(item["name"])
            if not pname.strip():
                errors.append(f"{prefix}.name must be a non-empty string")
            elif len(pname) > MAX_PARAM_NAME_LENGTH:
                errors.append(
                    f"{prefix}.name '{pname}' exceeds "
                    f"{MAX_PARAM_NAME_LENGTH} character limit"
                )
            elif not all(c.isalnum() or c == "_" for c in pname):
                errors.append(
                    f"{prefix}.name '{pname}' must contain only "
                    "letters, digits, and underscores"
                )
            elif pname in seen_names:
                errors.append(
                    f"Duplicate parameter name '{pname}' in parameters.{block}"
                )
            else:
                seen_names.add(pname)

        # description
        if "description" not in item:
            errors.append(f"{prefix} is missing required key 'description'")
        else:
            pdesc = str(item["description"])
            if not pdesc.strip():
                errors.append(f"{prefix}.description must be a non-empty string")
            elif len(pdesc) > MAX_PARAM_DESCRIPTION_LENGTH:
                errors.append(
                    f"{prefix}.description exceeds "
                    f"{MAX_PARAM_DESCRIPTION_LENGTH} character limit "
                    f"(keep it short — it appears as an inline hint)"
                )

        # default (only meaningful on optional params, but not forbidden on required)
        if "default" in item and item["default"] is not None:
            if not isinstance(item["default"], (str, int, float, bool)):
                errors.append(f"{prefix}.default must be a scalar string value")

    return errors


def _validate_parameters(raw: object) -> list[str]:
    """Validate the top-level ``parameters:`` frontmatter block."""
    errors: list[str] = []

    if not isinstance(raw, dict):
        errors.append(
            f"'parameters' frontmatter key must be a mapping, "
            f"got {type(raw).__name__}"
        )
        return errors

    allowed_param_keys = {"required", "optional"}
    extra = set(raw.keys()) - allowed_param_keys
    if extra:
        errors.append(
            f"Unexpected keys in parameters block: {', '.join(sorted(extra))}. "
            f"Only 'required' and 'optional' are allowed."
        )

    if "required" in raw:
        errors.extend(_validate_parameter_list(raw["required"], "required"))
    if "optional" in raw:
        errors.extend(_validate_parameter_list(raw["optional"], "optional"))

    # Check for duplicate names across required and optional
    if "required" in raw and "optional" in raw:
        req_names = {
            str(p["name"])
            for p in raw["required"]
            if isinstance(p, dict) and "name" in p
        }
        opt_names = {
            str(p["name"])
            for p in raw["optional"]
            if isinstance(p, dict) and "name" in p
        }
        overlap = req_names & opt_names
        if overlap:
            errors.append(
                f"Parameter name(s) appear in both required and optional: "
                f"{', '.join(sorted(overlap))}"
            )

    return errors


def _validate_metadata_fields(metadata: dict) -> list[str]:
    """Validate that only allowed fields are present."""
    errors = []

    extra_fields = set(metadata.keys()) - ALLOWED_FIELDS
    if extra_fields:
        errors.append(
            f"Unexpected fields in frontmatter: {', '.join(sorted(extra_fields))}. "
            f"Only {sorted(ALLOWED_FIELDS)} are allowed."
        )

    return errors


def validate_metadata(metadata: dict, skill_dir: Optional[Path] = None) -> list[str]:
    """Validate parsed skill metadata.

    This is the core validation function that works on already-parsed metadata,
    avoiding duplicate file I/O when called from the parser.

    Args:
        metadata: Parsed YAML frontmatter dictionary
        skill_dir: Optional path to skill directory (for name-directory match check)

    Returns:
        List of validation error messages. Empty list means valid.
    """
    errors = []
    errors.extend(_validate_metadata_fields(metadata))

    if "name" not in metadata:
        errors.append("Missing required field in frontmatter: name")
    else:
        errors.extend(_validate_name(metadata["name"], skill_dir))

    if "description" not in metadata:
        errors.append("Missing required field in frontmatter: description")
    else:
        errors.extend(_validate_description(metadata["description"]))

    if "compatibility" in metadata:
        errors.extend(_validate_compatibility(metadata["compatibility"]))

    if "parameters" in metadata:
        errors.extend(_validate_parameters(metadata["parameters"]))

    return errors


def validate(skill_dir: Path) -> list[str]:
    """Validate a skill directory.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        List of validation error messages. Empty list means valid.
    """
    skill_dir = Path(skill_dir)

    if not skill_dir.exists():
        return [f"Path does not exist: {skill_dir}"]

    if not skill_dir.is_dir():
        return [f"Not a directory: {skill_dir}"]

    skill_md = find_skill_md(skill_dir)
    if skill_md is None:
        return ["Missing required file: SKILL.md"]

    try:
        content = skill_md.read_text()
        metadata, _ = parse_frontmatter(content)
    except ParseError as e:
        return [str(e)]

    return validate_metadata(metadata, skill_dir)
