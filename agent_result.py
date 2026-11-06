from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class AgentResult:
    status: Literal["ok", "error"]
    result: Optional[str] = None
    error: Optional[str] = None
    source: Optional[str] = None
    def is_valid(self) -> bool:
        if self.source is not None and not self._has_text(self.source):
            return False
        if self.status == "ok":
            return self._has_text(self.result) and self.error is None
        if self.status == "error":
            return self._has_text(self.error) and self.result is None
        return False

    @staticmethod
    def _has_text(value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())
