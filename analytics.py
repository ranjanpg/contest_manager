from typing import List
from models import ProblemTag, UserPerformance


class AnalyticsEngine:
    """Provides basic performance metrics for a user."""

    @staticmethod
    def identify_weaknesses(
        tags: List[ProblemTag], max_weaknesses: int = 5
    ) -> List[str]:
        """
        Identify weakest topics based on solved counts.
        (A very simple heuristic: tags with the fewest solved counts are considered 'weakest')
        """
        sorted_tags = sorted(tags, key=lambda t: t.solved_count)
        return [t.tag_name for t in sorted_tags[:max_weaknesses]]

    @staticmethod
    def identify_strengths(tags: List[ProblemTag], max_strengths: int = 5) -> List[str]:
        """
        Identify strongest topics based on solved counts.
        """
        sorted_tags = sorted(tags, key=lambda t: t.solved_count, reverse=True)
        return [t.tag_name for t in sorted_tags[:max_strengths]]

    @staticmethod
    def calculate_recent_trend(performances: List[UserPerformance]) -> str:
        """Calculate recent rating trend (last 3 contests)."""
        if not performances:
            return "No recent performance data."

        recent = performances[-3:] if len(performances) > 3 else performances

        upward = 0
        downward = 0

        for p in recent:
            if p.rating_change is not None:
                if p.rating_change > 0:
                    upward += 1
                elif p.rating_change < 0:
                    downward += 1

        if upward > downward:
            return "Upward trend"
        elif downward > upward:
            return "Downward trend"
        else:
            return "Stable trend"
