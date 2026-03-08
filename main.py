import os
import logging
from dotenv import load_dotenv
from scheduler import Scheduler

DEBUG_MODE = os.getenv("DEBUG") == "1"
LOG_DIR = "logs" if DEBUG_MODE else "/var/log/contest_manager"

# Create log directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/contest_manager.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def main():
    # Load environment variables from .env file
    load_dotenv()

    logger.info("Initializing Contest Manager ...")

    # Check if necessary environment variables are set
    required_vars = ["EMAIL_SENDER", "EMAIL_PASSWORD", "EMAIL_RECIPIENT"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        logger.warning(
            "Missing environment variables for email notifications: "
            f"{', '.join(missing_vars)}"
        )
        logger.warning(
            "Please configure them in your .env file to enable email alerts."
        )

    logger.info(
        "Tracking Codeforces user: "
        f"{os.environ.get('CODEFORCES_USERNAME', 'Not Set')}"
    )
    logger.info(
        "Tracking LeetCode user: "
        f"{os.environ.get('LEETCODE_USERNAME', 'Not Set')}"
    )

    try:
        scheduler = Scheduler()
        scheduler.run()
    except Exception as e:
        logger.error(f"Fatal Error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
