import sqlite3
import os
from typing import List
from models import Contest, UserPerformance, ProblemTag
from datetime import datetime

_DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contests.db")


class Database:
    def __init__(self, db_path: str = _DEFAULT_DB):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Contests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contests (
                    id TEXT,
                    name TEXT,
                    host TEXT,
                    start_time TIMESTAMP,
                    duration_seconds INTEGER,
                    url TEXT,
                    PRIMARY KEY (id, host)
                )
            """)

            # User Performance table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_performance (
                    username TEXT,
                    host TEXT,
                    contest_id TEXT,
                    rating_change INTEGER,
                    new_rating INTEGER,
                    rank INTEGER,
                    is_notified BOOLEAN NOT NULL DEFAULT 0,
                    PRIMARY KEY (username, host, contest_id)
                )
            """)

            # Safe migration: add is_notified if the table already existed without it,
            # then mark all pre-existing rows as notified so they are not re-sent.
            try:
                cursor.execute(
                    "ALTER TABLE user_performance ADD COLUMN is_notified BOOLEAN NOT NULL DEFAULT 0"
                )
                cursor.execute("UPDATE user_performance SET is_notified = 1")
            except Exception:
                pass  # Column already exists, nothing to do

            # Problem Tags table for analytics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS problem_tags (
                    username TEXT,
                    host TEXT,
                    tag_name TEXT,
                    solved_count INTEGER,
                    PRIMARY KEY (username, host, tag_name)
                )
            """)

            conn.commit()

    def save_contest(self, contest: Contest) -> bool:
        upserted = False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO contests
                (id, name, host, start_time, duration_seconds, url)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id, host) DO UPDATE SET
                    name            = excluded.name,
                    start_time      = excluded.start_time,
                    duration_seconds = excluded.duration_seconds,
                    url             = excluded.url
                WHERE
                    name != excluded.name 
                    OR start_time != excluded.start_time 
                    OR duration_seconds != excluded.duration_seconds
                    OR url != excluded.url
            """,
                (
                    contest.id,
                    contest.name,
                    contest.host,
                    contest.start_time.isoformat(),
                    contest.duration_seconds,
                    contest.url,
                ),
            )
            if cursor.rowcount > 0:
                upserted = True
            conn.commit()
            return upserted

    def get_upcoming_contests(self) -> List[Contest]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                """
                SELECT id, name, host, start_time, duration_seconds, url 
                FROM contests 
                WHERE start_time > ? 
                ORDER BY start_time ASC
            """,
                (now,),
            )

            contests = []
            for row in cursor.fetchall():
                start_time = datetime.fromisoformat(row[3])
                contests.append(
                    Contest(
                        id=row[0],
                        name=row[1],
                        host=row[2],
                        start_time=start_time,
                        duration_seconds=row[4],
                        url=row[5],
                    )
                )
            return contests

    def save_user_performance(self, perf: UserPerformance):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Upsert: insert new row with is_notified=0, or update mutable fields
            # without touching is_notified so already-notified rows stay notified.
            cursor.execute(
                """
                INSERT INTO user_performance
                (username, host, contest_id, rating_change, new_rating, rank, is_notified)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(username, host, contest_id) DO UPDATE SET
                    rating_change = excluded.rating_change,
                    new_rating    = excluded.new_rating,
                    rank          = excluded.rank
            """,
                (
                    perf.username,
                    perf.host,
                    perf.contest_id,
                    perf.rating_change,
                    perf.new_rating,
                    perf.rank,
                ),
            )
            conn.commit()

    def get_user_performance(self, username: str, host: str) -> List[UserPerformance]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT contest_id, rating_change, new_rating, rank 
                FROM user_performance 
                WHERE username = ? AND host = ?
            """,
                (username, host),
            )

            perfs = []
            for row in cursor.fetchall():
                perfs.append(
                    UserPerformance(
                        username=username,
                        host=host,
                        contest_id=row[0],
                        rating_change=row[1],
                        new_rating=row[2],
                        rank=row[3],
                    )
                )
            return perfs

    def save_problem_tag(self, tag: ProblemTag):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO problem_tags
                (username, host, tag_name, solved_count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(username, host, tag_name) DO UPDATE SET
                    solved_count = excluded.solved_count
            """,
                (tag.username, tag.host, tag.tag_name, tag.solved_count),
            )
            conn.commit()

    def get_problem_tags(self, username: str, host: str) -> List[ProblemTag]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT tag_name, solved_count 
                FROM problem_tags 
                WHERE username = ? AND host = ?
            """,
                (username, host),
            )

            tags = []
            for row in cursor.fetchall():
                tags.append(
                    ProblemTag(
                        username=username,
                        host=host,
                        tag_name=row[0],
                        solved_count=row[1],
                    )
                )
            return tags

    def get_unnotified_performances(
        self, username: str, host: str
    ) -> List[UserPerformance]:
        """Return performances where is_notified = 0 (not yet sent)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT contest_id, rating_change, new_rating, rank
                FROM user_performance
                WHERE username = ? AND host = ? AND is_notified = 0
            """,
                (username, host),
            )
            return [
                UserPerformance(
                    username=username,
                    host=host,
                    contest_id=row[0],
                    rating_change=row[1],
                    new_rating=row[2],
                    rank=row[3],
                )
                for row in cursor.fetchall()
            ]

    def mark_performances_notified(
        self, username: str, host: str, contest_ids: List[str]
    ):
        """Mark the given contest performances as notified."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                UPDATE user_performance SET is_notified = 1
                WHERE username = ? AND host = ? AND contest_id = ?
            """,
                [(username, host, cid) for cid in contest_ids],
            )
            conn.commit()
