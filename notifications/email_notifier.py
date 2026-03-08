import smtplib
import logging
from email.message import EmailMessage
from typing import List
import os
from models import Contest, UserPerformance, ProblemTag
from .base_notifier import BaseNotifier

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    def __init__(self):
        self.sender_email = os.environ.get("EMAIL_SENDER")
        self.sender_password = os.environ.get("EMAIL_PASSWORD")
        self.recipient_email = os.environ.get("EMAIL_RECIPIENT")

    def _send_email(self, subject: str, content: str):
        if not all([self.sender_email, self.sender_password, self.recipient_email]):
            logger.warning("Email credentials not fully configured in environment.")
            return

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = self.recipient_email
        msg.set_content(content)

        try:
            # Assuming Gmail SMTP for this example
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(self.sender_email, self.sender_password)
                smtp.send_message(msg)
            logger.info(f"Successfully sent email: {subject}")
        except Exception as e:
            logger.error(f"Failed to send email. Error: {e}", exc_info=True)

    def send_upcoming_contests(self, contests: List[Contest]):
        if not contests:
            return

        subject = f"Upcoming Contests Alert ({len(contests)} contests)"

        content = "Here are your upcoming coding contests:\n\n"
        for c in contests:
            duration_hours = c.duration_seconds / 3600
            content += f"- {c.name} ({c.host.capitalize()})\n"
            content += f"  Time: {c.start_time.strftime('%Y-%m-%d %H:%M')}\n"
            content += f"  Duration: {duration_hours:.1f} hours\n"
            content += f"  Link: {c.url}\n\n"

        self._send_email(subject, content)

    def send_performance_report(
        self, performances: List[UserPerformance], tags: List[ProblemTag]
    ):
        if not performances:
            return

        subject = "Your Weekly Contest Performance Report"

        content = "Here is an overview of your recent performances:\n\n"
        for p in performances:
            sign = "+" if p.rating_change and p.rating_change > 0 else ""
            change_str = f"{sign}{p.rating_change}" if p.rating_change else "N/A"
            content += f"- {p.host.capitalize()} {p.contest_id}\n"
            content += f"  Rank: {p.rank}\n"
            content += f"  Rating Change: {change_str} -> {p.new_rating}\n\n"

        if tags:
            content += "\nTopic Strengths/Weaknesses (Based on problems solved):\n"
            # simple sorting by count to highlight strengths
            sorted_tags = sorted(tags, key=lambda x: x.solved_count, reverse=True)
            for top_tag in sorted_tags[:5]:
                content += f"  - {top_tag.tag_name}: {top_tag.solved_count} solved\n"

            content += "\nNeeds improvement:\n"
            for bottom_tag in sorted_tags[-5:]:  # Simple heuristic
                content += (
                    f"  - {bottom_tag.tag_name}: {bottom_tag.solved_count} solved\n"
                )

        self._send_email(subject, content)
