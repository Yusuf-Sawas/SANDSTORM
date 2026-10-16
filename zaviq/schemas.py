"""Data models for the Dune planning workflow.

The output models stay plain on purpose: the same classes are sent to Gemini
as the response schema, so they avoid features that schema conversion may not
support. Safety rules live in validators, which run on the parsed result.

Unknown keys in model output are dropped by Pydantic, so anything that gets
saved is exactly what these models define.
"""

import re
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_PROMPT_CHARS = 2000

_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


def _non_blank(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must not be empty or only whitespace")
    return stripped


class DuneRequest(BaseModel):
    """A user's project idea. Surrounding whitespace is removed; blank input is rejected."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=MAX_PROMPT_CHARS)

    @field_validator("prompt")
    @classmethod
    def prompt_is_usable(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("prompt must not contain NUL characters")
        return _non_blank(value, "prompt")


class ArchitectureComponent(BaseModel):
    """One part of the proposed system and its responsibility."""

    name: str
    responsibility: str


class Milestone(BaseModel):
    """A stage of work, its tasks, and the checks that show it is done."""

    name: str
    tasks: list[str]
    acceptance_criteria: list[str]


class ProposedFile(BaseModel):
    """A suggested file path. Suggestions are text only; nothing is created on disk."""

    path: str
    purpose: str

    @field_validator("path")
    @classmethod
    def path_is_safe_and_relative(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            raise ValueError("path must not be empty")
        if "\\" in candidate or "\x00" in candidate:
            raise ValueError("path must use forward slashes and contain no NUL characters")
        if candidate.startswith(("/", "~")) or _WINDOWS_DRIVE.match(candidate):
            raise ValueError("path must be relative, not absolute")
        parts = PurePosixPath(candidate).parts
        if not parts:
            raise ValueError("path must name a file")
        if ".." in parts:
            raise ValueError("path must not contain '..' segments")
        return candidate


class DunePlan(BaseModel):
    """The structured plan the model must return. It is validated before anything is saved."""

    summary: str
    assumptions: list[str]
    clarifying_questions: list[str]
    architecture: list[ArchitectureComponent]
    milestones: list[Milestone]
    proposed_files: list[ProposedFile]
    risks: list[str]

    @field_validator("summary")
    @classmethod
    def summary_is_present(cls, value: str) -> str:
        return _non_blank(value, "summary")

    @field_validator("milestones")
    @classmethod
    def at_least_one_milestone(cls, value: list[Milestone]) -> list[Milestone]:
        if not value:
            raise ValueError("a plan needs at least one milestone")
        return value
