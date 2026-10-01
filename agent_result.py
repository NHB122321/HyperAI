from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentResult:
    status: str
    result: Optional[str] = None
    error: Optional[str] = None
    source: Optional[str] = None