import schedule
import time
import logging
import os
from database import Database

from contest_hosts.codeforces import Codeforces
from contest_hosts.leetcode import LeetCode
from notifications.email_notifier import EmailNotifier
from notifications.calendar_notifier import CalendarNotifier

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self):
        self.db = Database()
        self.hosts = [Codeforces(), LeetCode()]

        self.email_notifier = EmailNotifier()
        self.calendar_notifier = CalendarNotifier()
        self.notifiers = [self.calendar_notifier]

        # Load user settings from env (fallback to prompts in main if needed)
        self.cf_username = os.environ.get("CODEFORCES_USERNAME")
        self.lc_username = os.environ.get("LEETCODE_USERNAME")

    def fetch_and_notify_upcoming_contests(self):
        logger.info("Checking for upcoming contests...")
        all_upcoming = []

        for host in self.hosts:
            contests = host.get_contests()
            for c in contests:
                logger.debug(f"processing contest {c}")
                upserted = self.db.save_contest(c)
                logger.info(f"Contest {c.name} upserted: {upserted}")
                # Only notify about NEW contests
                if upserted:
                    all_upcoming.append(c)

        if all_upcoming:
            for notifier in self.notifiers:
                notifier.send_upcoming_contests(all_upcoming)

    def fetch_and_notify_performance(self):
        logger.info("Checking user performances...")

        if self.cf_username:
            cf = self.hosts[0]
            perfs = cf.get_user_performance(self.cf_username)
            tags = cf.get_user_problem_tags(self.cf_username)
            for p in perfs:
                self.db.save_user_performance(p)
            for t in tags:
                self.db.save_problem_tag(t)

            new_perfs = self.db.get_unnotified_performances(
                self.cf_username, "codeforces"
            )
            if new_perfs:
                logger.info(
                    f"Sending Codeforces performance report for {len(new_perfs)} new contest(s)."
                )
                self.email_notifier.send_performance_report(new_perfs, tags)
                self.db.mark_performances_notified(
                    self.cf_username, "codeforces", [p.contest_id for p in new_perfs]
                )
            else:
                logger.info("No new Codeforces performances to notify about.")

        if self.lc_username:
            lc = self.hosts[1]
            perfs = lc.get_user_performance(self.lc_username)
            tags = lc.get_user_problem_tags(self.lc_username)
            for p in perfs:
                self.db.save_user_performance(p)
            for t in tags:
                self.db.save_problem_tag(t)

            new_perfs = self.db.get_unnotified_performances(
                self.lc_username, "leetcode"
            )
            if new_perfs:
                logger.info(
                    f"Sending LeetCode performance report for {len(new_perfs)} new contest(s)."
                )
                self.email_notifier.send_performance_report(new_perfs, tags)
                self.db.mark_performances_notified(
                    self.lc_username, "leetcode", [p.contest_id for p in new_perfs]
                )
            else:
                logger.info("No new LeetCode performances to notify about.")

    def run(self):
        logger.info("Scheduler started. Press Ctrl+C to exit.")
        # Run immediately on startup
        self.fetch_and_notify_upcoming_contests()
        self.fetch_and_notify_performance()

        # Schedule future runs
        schedule.every().day.at("09:00").do(self.fetch_and_notify_upcoming_contests)
        schedule.every().sunday.at("18:00").do(self.fetch_and_notify_performance)

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Wait one minute
        except KeyboardInterrupt:
            logger.info("Scheduler exiting gracefully.")
