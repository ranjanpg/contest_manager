import logging
import os
from typing import List
from datetime import timezone, timedelta
from models import Contest, UserPerformance, ProblemTag
from .base_notifier import BaseNotifier

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Only the scope needed to create calendar events
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

CREDENTIALS_FILE = "secrets/credentials.json"
TOKEN_FILE = "secrets/token.json"


class CalendarNotifier(BaseNotifier):
    def __init__(self):
        self.service: Resource | None = self._authenticate()

    def _authenticate(self) -> Resource | None:
        """Authenticate using OAuth2 and return the Google Calendar service."""
        creds = None

        if not os.path.exists(CREDENTIALS_FILE):
            logger.error(
                f"'{CREDENTIALS_FILE}' not found. Please download it from Google Cloud Console "
                "and place it in the project root."
            )
            return None

        # Load existing token if available
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        # If no valid credentials, run the OAuth2 browser flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing Google OAuth token...")
                creds.refresh(Request())
            else:
                logger.info(
                    "No valid token found. Launching browser for Google OAuth authorization..."
                )
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token for future runs
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
            logger.info(f"Saved OAuth token to '{TOKEN_FILE}'.")

        return build("calendar", "v3", credentials=creds)

    def _event_already_exists(self, contest: Contest) -> bool:
        """Check if an event tagged with this contest's unique ID already exists."""
        if not self.service:
            return False
        try:
            events = (
                self.service.events()
                .list(
                    calendarId="primary",
                    privateExtendedProperty=f"contestId={contest.unique_key}",
                    singleEvents=True,
                )
                .execute()
            )
            return len(events.get("items", [])) > 0
        except HttpError:
            return False

    def _create_event(self, contest: Contest):
        """Create a single Google Calendar event for a contest."""
        if not self.service:
            return

        # Ensure timezone-aware datetime — treat naive datetimes as local time
        start_dt = contest.start_time
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        start_utc = start_dt.astimezone(timezone.utc)
        end_utc = start_utc + timedelta(seconds=contest.duration_seconds)

        event_body = {
            "summary": f"{contest.host.capitalize()}: {contest.name}",
            "description": f"Coding contest on {contest.host.capitalize()}.\n\nJoin at: {contest.url}",
            "start": {
                "dateTime": start_utc.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_utc.isoformat(),
                "timeZone": "UTC",
            },
            "source": {
                "title": contest.name,
                "url": contest.url,
            },
            "extendedProperties": {
                "private": {
                    "contestId": contest.unique_key,  # Unique contest key stored as a private extended property for dedup
                }
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 60},  # 1 hour before
                    {"method": "popup", "minutes": 15},  # 15 minutes before
                ],
            },
        }

        try:
            created = (
                self.service.events()
                .insert(calendarId="primary", body=event_body)
                .execute()
            )
            logger.info(
                f"Created Google Calendar event: '{created['summary']}' -> {created.get('htmlLink')}"
            )
            # logger.info(
            #     f"Would have created Google Calendar event: '{event_body['summary']}' -> {event_body['start']['dateTime']}"
            # )
        except HttpError as e:
            logger.error(
                f"Failed to create event for '{contest.name}': {e}", exc_info=True
            )

    def send_upcoming_contests(self, contests: List[Contest]):
        if not contests:
            return

        if not self.service:
            logger.warning(
                "Google Calendar service is unavailable. Skipping calendar notifications."
            )
            return

        logger.info(
            f"Creating Google Calendar events for {len(contests)} upcoming contests..."
        )
        created_count = 0
        skipped_count = 0

        for contest in contests:
            if self._event_already_exists(contest):
                logger.debug(f"Skipping duplicate event: '{contest.name}'")
                skipped_count += 1
            else:
                self._create_event(contest)
                created_count += 1

        logger.info(
            f"Calendar sync complete: {created_count} created, {skipped_count} skipped (already existed)."
        )

    def send_performance_report(
        self, performances: List[UserPerformance], tags: List[ProblemTag]
    ):
        # Calendar events do not make sense for performance reports.
        pass
