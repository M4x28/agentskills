"""YAML frontmatter parsing for SKILL.md files."""

from pathlib import Path
from typing import Optional

import strictyaml

from .errors import ParseError, ValidationError
from .models import ParameterDef, Parameters, SkillProperties


def find_skill_md(skill_dir: Path) -> Optional[Path]:
    """Find the SKILL.md file in a skill directory.

    Prefers SKILL.md (uppercase) but accepts skill.md (lowercase).

    Args:
        skill_dir: Path to the skill directory

    Returns:
        Path to the SKILL.md file, or None if not found
    """
    for name in ("SKILL.md", "skill.md"):
        path = skill_dir / name
        if path.exists():
            return path
    return None


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from SKILL.md content.

    Args:
        content: Raw content of SKILL.md file

    Returns:
        Tuple of (metadata dict, markdown body)

    Raises:
        ParseError: If frontmatter is missing or invalid
    """
    if not content.startswith("---"):
        raise ParseError("SKILL.md must start with YAML frontmatter (---)")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ParseError("SKILL.md frontmatter not properly closed with ---")

    frontmatter_str = parts[1]
    body = parts[2].strip()

    try:
        parsed = strictyaml.load(frontmatter_str)
        metadata = parsed.data
    except strictyaml.YAMLError as e:
        raise ParseError(f"Invalid YAML in frontmatter: {e}")

    if not isinstance(metadata, dict):
        raise ParseError("SKILL.md frontmatter must be a YAML mapping")

    if "metadata" in metadata and isinstance(metadata["metadata"], dict):
        metadata["metadata"] = {str(k): str(v) for k, v in metadata["metadata"].items()}

    return metadata, body


def _parse_parameter_list(raw: object, block_name: str) -> list[ParameterDef]:
    """Parse a list of parameter definitions from raw YAML data.

    Args:
        raw: The raw value of a ``required`` or ``optional`` block
        block_name: ``"required"`` or ``"optional"`` (used in error messages)

    Returns:
        List of :class:`ParameterDef` instances

    Raises:
        ParseError: If the structure is not a list of mappings with a ``name`` key
    """
    if not isinstance(raw, list):
        raise ParseError(
            f"parameters.{block_name} must be a list, got {type(raw).__name__}"
        )

    params: list[ParameterDef] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ParseError(
                f"parameters.{block_name}[{i}] must be a mapping, "
                f"got {type(item).__name__}"
            )
        if "name" not in item:
            raise ParseError(
                f"parameters.{block_name}[{i}] is missing required key 'name'"
            )
        if "description" not in item:
            raise ParseError(
                f"parameters.{block_name}[{i}] ('{item['name']}') "
                f"is missing required key 'description'"
            )
        params.append(
            ParameterDef(
                name=str(item["name"]),
                description=str(item["description"]),
                default=str(item["default"]) if "default" in item else None,
            )
        )
    return params


def _parse_parameters(raw: object) -> Parameters:
    """Parse the top-level ``parameters:`` block from raw YAML data.

    Args:
        raw: The raw value of the ``parameters`` frontmatter key

    Returns:
        :class:`Parameters` instance

    Raises:
        ParseError: If the structure is invalid
    """
    if not isinstance(raw, dict):
        raise ParseError(
            f"'parameters' frontmatter key must be a mapping, "
            f"got {type(raw).__name__}"
        )

    required: list[ParameterDef] = []
    optional: list[ParameterDef] = []

    if "required" in raw:
        required = _parse_parameter_list(raw["required"], "required")
    if "optional" in raw:
        optional = _parse_parameter_list(raw["optional"], "optional")

    return Parameters(required=required, optional=optional)


def read_properties(skill_dir: Path) -> SkillProperties:
    """Read skill properties from SKILL.md frontmatter.

    This function parses the frontmatter and returns properties.
    It does NOT perform full validation. Use validate() for that.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        SkillProperties with parsed metadata

    Raises:
        ParseError: If SKILL.md is missing or has invalid YAML
        ValidationError: If required fields (name, description) are missing
    """
    skill_dir = Path(skill_dir)
    skill_md = find_skill_md(skill_dir)

    if skill_md is None:
        raise ParseError(f"SKILL.md not found in {skill_dir}")

    content = skill_md.read_text()
    metadata, _ = parse_frontmatter(content)

    if "name" not in metadata:
        raise ValidationError("Missing required field in frontmatter: name")
    if "description" not in metadata:
        raise ValidationError("Missing required field in frontmatter: description")

    name = metadata["name"]
    description = metadata["description"]

    if not isinstance(name, str) or not name.strip():
        raise ValidationError("Field 'name' must be a non-empty string")
    if not isinstance(description, str) or not description.strip():
        raise ValidationError("Field 'description' must be a non-empty string")

    parameters: Optional[Parameters] = None
    if "parameters" in metadata:
        parameters = _parse_parameters(metadata["parameters"])

    return SkillProperties(
        name=name.strip(),
        description=description.strip(),
        license=metadata.get("license"),
        compatibility=metadata.get("compatibility"),
        allowed_tools=metadata.get("allowed-tools"),
        metadata=metadata.get("metadata"),
        parameters=parameters,
    )
