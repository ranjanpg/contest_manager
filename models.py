from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Contest:
    id: str
    name: str
    host: str  # 'codeforces', 'leetcode', etc.
    start_time: datetime
    duration_seconds: int
    url: str

    @property
    def unique_key(self) -> str:
        """Unique contest key stored as a private extended property for dedup"""
        return f"{self.host}:{self.id}"


@dataclass
class UserPerformance:
    username: str
    host: str
    contest_id: str
    rating_change: Optional[int]
    new_rating: Optional[int]
    rank: Optional[int]


@dataclass
class ProblemTag:
    username: str
    host: str
    tag_name: str
    solved_count: int
