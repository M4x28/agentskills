"""Data models for Agent Skills."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParameterDef:
    """Definition of a single skill parameter.

    Attributes:
        name: Snake-case parameter identifier (e.g. ``company_name``)
        description: Human-readable hint shown to the user (≤120 chars recommended)
        default: Pre-filled default value for optional parameters (None for required)
    """

    name: str
    description: str
    default: Optional[str] = None

    def to_dict(self) -> dict:
        result = {"name": self.name, "description": self.description}
        if self.default is not None:
            result["default"] = self.default
        return result


@dataclass
class Parameters:
    """Structured parameter block parsed from a SKILL.md frontmatter.

    Attributes:
        required: Parameters the skill needs to function correctly
        optional: Parameters that improve output but have sensible defaults
    """

    required: list[ParameterDef] = field(default_factory=list)
    optional: list[ParameterDef] = field(default_factory=list)

    def to_dict(self) -> dict:
        result: dict = {}
        if self.required:
            result["required"] = [p.to_dict() for p in self.required]
        if self.optional:
            result["optional"] = [p.to_dict() for p in self.optional]
        return result


@dataclass
class SkillProperties:
    """Properties parsed from a skill's SKILL.md frontmatter.

    Attributes:
        name: Skill name in kebab-case (required)
        description: What the skill does and when the model should use it (required)
        license: License for the skill (optional)
        compatibility: Compatibility information for the skill (optional)
        allowed_tools: Tool patterns the skill requires (optional, experimental)
        metadata: Key-value pairs for client-specific properties (defaults to
            empty dict; omitted from to_dict() output when empty)
        parameters: Structured parameter definitions for client-side auto-fill
            (optional). Supporting clients render a guided prompt template when
            the user invokes the skill; non-supporting clients safely ignore it.
    """

    name: str
    description: str
    license: Optional[str] = None
    compatibility: Optional[str] = None
    allowed_tools: Optional[str] = None
    metadata: dict[str, str] = field(default_factory=dict)
    parameters: Optional[Parameters] = None

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        result = {"name": self.name, "description": self.description}
        if self.license is not None:
            result["license"] = self.license
        if self.compatibility is not None:
            result["compatibility"] = self.compatibility
        if self.allowed_tools is not None:
            result["allowed-tools"] = self.allowed_tools
        if self.metadata:
            result["metadata"] = self.metadata
        if self.parameters is not None:
            result["parameters"] = self.parameters.to_dict()
        return result
