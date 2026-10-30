"""Shared validation primitives only; no financial or regulatory domain rules."""

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RuleError(ValueError):
    pass
