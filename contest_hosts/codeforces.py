import logging
from typing import List
from datetime import datetime, timezone
from models import Contest, UserPerformance, ProblemTag
from .host import BaseHost
import requests

logger = logging.getLogger(__name__)


class Codeforces(BaseHost):
    def __init__(self):
        super().__init__("https://codeforces.com/api")

    def _signed_request(self, method_name: str, params: dict = None) -> dict:
        import time
        import random
        import string
        import hashlib
        import os

        if params is None:
            params = {}

        api_key = os.environ.get("CODEFORCES_KEY")
        api_secret = os.environ.get("CODEFORCES_SECRET")

        if api_key and api_secret:
            params["apiKey"] = api_key
            params["time"] = str(int(time.time()))

            # Sort params by keys, then by values (if keys are equal)
            sorted_params = sorted([(k, str(v)) for k, v in params.items()])
            query_string = "&".join([f"{k}={v}" for k, v in sorted_params])

            rand_str = "".join(
                random.choices(string.ascii_lowercase + string.digits, k=6)
            )

            text_to_hash = f"{rand_str}/{method_name}?{query_string}#{api_secret}"
            api_sig = (
                rand_str + hashlib.sha512(text_to_hash.encode("utf-8")).hexdigest()
            )

            params["apiSig"] = api_sig

        response = requests.get(f"{self.url}/{method_name}", params=params)
        return response.json()

    def get_contests(self) -> List[Contest]:
        data = self._signed_request("contest.list")

        if data.get("status") != "OK":
            logger.error(f"Error parsing codeforces contests: {data}")
            return []

        logger.debug(f"Codeforces getUpcomingContests Response: {data}")

        upcoming_contests = []
        for c in data.get("result", []):
            if c.get("phase") == "BEFORE":
                # Codeforces provides timestamp in seconds
                start_time = datetime.fromtimestamp(
                    c["startTimeSeconds"], tz=timezone.utc
                )
                upcoming_contests.append(
                    Contest(
                        id=str(c["id"]),
                        name=c["name"],
                        host="codeforces",
                        start_time=start_time,
                        duration_seconds=c["durationSeconds"],
                        url=f"https://codeforces.com/contest/{c['id']}",
                    )
                )
        return upcoming_contests

    def get_user_performance(self, username: str) -> List[UserPerformance]:
        data = self._signed_request("user.rating", {"handle": username})

        if data.get("status") != "OK":
            logger.error(f"Error fetching codeforces rating for {username}: {data}")
            return []

        logger.debug(f"Codeforces get_user_performance Response: {data}")

        performances = []
        for p in data.get("result", []):
            performances.append(
                UserPerformance(
                    username=username,
                    host="codeforces",
                    contest_id=str(p["contestId"]),
                    rating_change=p["newRating"] - p["oldRating"],
                    new_rating=p["newRating"],
                    rank=p["rank"],
                )
            )
        return performances

    def get_user_problem_tags(self, username: str) -> List[ProblemTag]:
        data = self._signed_request("user.status", {"handle": username})

        if data.get("status") != "OK":
            logger.error(f"Error fetching codeforces status for {username}: {data}")
            return []

        logger.debug(f"Codeforces get_user_problem_tags Response: {data}")

        tag_counts = {}
        for submission in data.get("result", []):
            if submission.get("verdict") == "OK":
                tags = submission.get("problem", {}).get("tags", [])
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return [
            ProblemTag(
                username=username, host="codeforces", tag_name=tag, solved_count=count
            )
            for tag, count in tag_counts.items()
        ]
