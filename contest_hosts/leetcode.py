import logging
from typing import List
from datetime import datetime, timezone
import requests
from models import Contest, UserPerformance, ProblemTag
from .host import BaseHost

logger = logging.getLogger(__name__)


class LeetCode(BaseHost):
    def __init__(self):
        super().__init__("https://leetcode.com/graphql")

    def get_contests(self) -> List[Contest]:
        query = """
        query getUpcomingContests {
            topTwoContests {
                title
                titleSlug
                startTime
                duration
            }
        }
        """
        response = requests.post(self.url, json={"query": query})
        data = response.json()

        logger.debug(f"Leetcode getUpcomingContests Response: {data}")

        if "errors" in data:
            logger.error(f"Error parsing leetcode contests: {data['errors']}")
            return []

        upcoming_contests = []
        for c in data.get("data", {}).get("topTwoContests", []):
            start_time = datetime.fromtimestamp(c["startTime"], tz=timezone.utc)
            upcoming_contests.append(
                Contest(
                    id=c["titleSlug"],
                    name=c["title"],
                    host="leetcode",
                    start_time=start_time,
                    duration_seconds=c["duration"],
                    url=f"https://leetcode.com/contest/{c['titleSlug']}",
                )
            )
        return upcoming_contests

    def get_user_performance(self, username: str) -> List[UserPerformance]:
        query = """
        query userContestRankingInfo($username: String!) {
            userContestRankingHistory(username: $username) {
                contest {
                    titleSlug
                }
                rating
                ranking
            }
        }
        """
        response = requests.post(
            self.url, json={"query": query, "variables": {"username": username}}
        )
        data = response.json()

        if "errors" in data:
            logger.error(
                f"Error fetching leetcode rating for {username}: {data['errors']}"
            )
            return []

        logger.debug(f"Leetcode get_user_performance Response: {data}")

        performances = []
        history = data.get("data", {}).get("userContestRankingHistory", [])
        history = [
            h for h in history if h["rating"] is not None and h["rating"] > 0
        ]  # Leetcode returns empty entries for unattended contests

        for i, p in enumerate(history):
            new_rating = int(p["rating"])
            old_rating = (
                int(history[i - 1]["rating"]) if i > 0 else 1500
            )  # Default starting rating is 1500

            performances.append(
                UserPerformance(
                    username=username,
                    host="leetcode",
                    contest_id=p["contest"]["titleSlug"],
                    rating_change=new_rating - old_rating,
                    new_rating=new_rating,
                    rank=p["ranking"],
                )
            )
        return performances

    def get_user_problem_tags(self, username: str) -> List[ProblemTag]:
        query = """
        query userSkillStats($username: String!) {
            matchedUser(username: $username) {
                tagProblemCounts {
                    advanced {
                        tagName
                        problemsSolved
                    }
                    intermediate {
                        tagName
                        problemsSolved
                    }
                    fundamental {
                        tagName
                        problemsSolved
                    }
                }
            }
        }
        """
        response = requests.post(
            self.url, json={"query": query, "variables": {"username": username}}
        )
        data = response.json()

        if "errors" in data or not data.get("data", {}).get("matchedUser"):
            logger.error(
                f"Error fetching leetcode tags for {username}: {data.get('errors', 'User not found')}"
            )
            return []

        logger.debug(f"Leetcode get_user_problem_tags Response: {data}")

        tags_data = data["data"]["matchedUser"]["tagProblemCounts"]
        problem_tags = []

        for difficulty, tags in tags_data.items():
            for t in tags:
                if t["problemsSolved"] > 0:
                    problem_tags.append(
                        ProblemTag(
                            username=username,
                            host="leetcode",
                            tag_name=t["tagName"],
                            solved_count=t["problemsSolved"],
                        )
                    )

        return problem_tags
