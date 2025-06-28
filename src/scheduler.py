"""
Scheduler for RSS collection jobs.
Handles periodic execution of RSS collection tasks.
"""
import logging
import schedule
import time
import threading
from datetime import datetime
from typing import List, Callable, Optional, Dict, Any
import pytz

# Assuming setup_module_logger is available in logging_utils
from utils.logging_utils import setup_module_logger

logger = setup_module_logger(__name__)

class Scheduler:
    """
    Manages scheduled execution of RSS collection tasks.
    """

    def __init__(self, times: List[str], collection_job_func: Callable[[], Optional[Dict[str, Any]]], timezone: str = "Asia/Kolkata"):
        """
        Initialize the scheduler.

        Args:
            times: List of times in HH:MM format (e.g., ["05:00", "14:00"])
            collection_job_func: Callable function to execute for collection.
                                 Should return a dictionary of stats or None.
            timezone: Timezone for scheduling (default: Asia/Kolkata)
        """
        self.times = times
        self.collection_job_func = collection_job_func
        self.timezone = timezone
        self.running = False
        self.thread = None

        # Setup timezone
        try:
            self.tz = pytz.timezone(timezone)
            logger.info(f"Scheduler initialized with timezone: {timezone}")
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone: {timezone}, using system default")
            self.tz = None

        logger.debug(f"Scheduler initialized for times: {times}")


    def _run_job_safely(self):
        """
        Run the job function with error handling.
        """
        if not self.collection_job_func:
            logger.error("No collection job function defined")
            return

        try:
            logger.info("Executing scheduled collection job...")
            start_time = time.time()

            # Execute the job
            result = self.collection_job_func()

            duration = time.time() - start_time
            logger.info(f"Scheduled job completed in {duration:.2f} seconds")

            # Log job results if available
            if isinstance(result, dict):
                total_new_articles = result.get('total_new_articles', 0)
                keywords_processed = result.get('keywords_processed', 0)
                errors = result.get('errors', 0)
                logger.info(f"Job summary: {total_new_articles} new articles from {keywords_processed} keywords ({errors} errors)")


        except Exception as e:
            logger.error(f"Error executing scheduled job: {e}", exc_info=True)

    def start(self):
        """
        Start the scheduler in a separate thread.
        """
        if self.running:
            logger.warning("Scheduler is already running")
            return

        self.running = True

        # Clear any existing jobs from previous runs or instances
        schedule.clear()

        # Schedule jobs for each specified time
        for time_str in self.times:
             try:
                # Basic validation for time format
                datetime.strptime(time_str, "%H:%M").time()
                schedule.every().day.at(time_str).do(self._run_job_safely)
                logger.info(f"Scheduled collection job at {time_str}")
             except ValueError:
                 logger.error(f"Invalid time format in schedule: {time_str}. Skipping.")
             except Exception as e:
                 logger.error(f"Error scheduling job at {time_str}: {e}", exc_info=True)


        if not schedule.get_jobs():
            logger.warning("No valid jobs scheduled. Scheduler will not run any tasks.")
            self.running = False # Stop if no jobs were scheduled
            return


        # Start scheduler thread
        # Use a lock to prevent scheduler from running jobs before the thread is fully started (less critical with BlockingScheduler but good practice)
        # self._start_lock = threading.Lock()
        # self._start_lock.acquire() # Acquire lock before starting thread

        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()

        # self._start_lock.release() # Release lock after thread starts

        logger.info("Scheduler started in a separate thread.")

    def stop(self):
        """
        Stop the scheduler.
        """
        if not self.running:
            logger.warning("Scheduler is not running")
            return

        logger.info("Stopping scheduler...")
        self.running = False

        # Wait for thread to finish (with a timeout)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                 logger.warning("Scheduler thread did not terminate cleanly.")
            else:
                 logger.info("Scheduler thread stopped.")


        # Clear scheduled jobs
        schedule.clear()

        logger.info("Scheduler stopped")

    def _scheduler_loop(self):
        """
        Main scheduler loop running in separate thread.
        """
        logger.debug("Scheduler loop started")

        # self._start_lock.acquire() # Wait for start signal (less critical with BlockingScheduler but good practice)
        # self._start_lock.release()

        while self.running:
            try:
                # Run pending jobs
                schedule.run_pending()

                # Sleep for a short period
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                time.sleep(5)  # Wait longer after error

        logger.debug("Scheduler loop stopped")

    def get_next_run_time(self) -> Optional[datetime]:
        """
        Get the next scheduled run time.

        Returns:
            Next run time as datetime or None if no jobs scheduled
        """
        try:
            jobs = schedule.get_jobs()
            if not jobs:
                return None

            # Get the next run time from all jobs
            next_runs = [job.next_run for job in jobs if job.next_run]

            if next_runs:
                next_run = min(next_runs)

                # schedule library uses naive datetime, assume local time unless timezone is explicitly handled
                # For simplicity and to match requirement of offline VM with potential IST, let's assume system time is correct or handle TZ
                # If self.tz is set, we can try to localize, but schedule works with naive datetimes
                # A more robust solution for timezones with 'schedule' might involve ensuring the system time and timezone are correctly set on the VM.
                # Returning naive datetime from schedule library as is for now.
                return next_run # This is a naive datetime in system's local time


            return None

        except Exception as e:
            logger.error(f"Error getting next run time: {e}", exc_info=True)
            return None

    def get_status(self) -> dict:
        """
        Get scheduler status information.

        Returns:
            Dictionary with scheduler status
        """
        try:
            next_run = self.get_next_run_time()

            status = {
                "running": self.running,
                "scheduled_times": self.times,
                "timezone": self.timezone, # Note: schedule library works with naive datetimes, actual execution time depends on system TZ
                "next_run": next_run.isoformat() if next_run else None,
                "jobs_count": len(schedule.get_jobs()),
                "thread_alive": self.thread.is_alive() if self.thread else False
            }

            return status

        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}", exc_info=True)
            return {"error": str(e)}

    def run_now(self):
        """
        Execute the collection job immediately (outside of schedule).
        """
        if not self.collection_job_func:
            logger.error("No collection job function defined")
            return

        logger.info("Running collection job immediately...")
        self._run_job_safely()


# Top-level function to initialize the scheduler, called by run.py
def initialize_scheduler(config_manager: ConfigManager, run_pipeline_func: Callable[[], Optional[Dict[str, Any]]]) -> Optional[Scheduler]:
     """
     Initializes and configures the scheduler based on the application settings.

     Args:
         config_manager: The ConfigManager instance with loaded settings.
         run_pipeline_func: The function to call for each scheduled collection run.

     Returns:
         A configured Scheduler instance, or None if scheduling is not configured or invalid.
     """
     try:
         schedule_times = config_manager.get_config_value("schedule.times", [])
         timezone = config_manager.get_config_value("schedule.timezone", "Asia/Kolkata") # Get timezone from config

         if not schedule_times:
             logger.warning("No schedule times configured in settings.")
             return None

         # Create and configure the scheduler instance
         scheduler = Scheduler(times=schedule_times, collection_job_func=run_pipeline_func, timezone=timezone)

         # Jobs are added in the scheduler.start() method when using the 'schedule' library in this manner.
         # The scheduler.start() method will call schedule.clear() and then schedule jobs based on the times provided.

         logger.info(f"Scheduler initialized with {len(schedule_times)} schedule times.")

         return scheduler

     except Exception as e:
         logger.exception(f"Failed to initialize scheduler: {e}")
         return None
