"""
Main entry point for RSS Collector.
Orchestrates the overall RSS collection process.
"""
import argparse
import datetime
import json
import logging
import os
import sys
import time
from typing import Dict, List, Any, Optional

# Import specific exceptions for more granular handling
from json.decoder import JSONDecodeError
from requests.exceptions import RequestException # Assuming RSSFetcher uses requests or a similar library

from config_manager import ConfigManager
from rss_fetcher import RSSFetcher
from rss_parser import RSSParser
from storage_manager import StorageManager
from utils.logging_utils import setup_logging
from utils.proxy_utils import setup_proxy_environment # Assuming this function handles proxy setup

# Try importing initialize_scheduler from scheduler, handle if not found
try:
    from scheduler import initialize_scheduler
except ImportError:
    # If scheduler is not available, provide a placeholder or log a critical error
    # For this example, we'll log a critical error and assume scheduling won't work
    logging.critical("Could not import initialize_scheduler from scheduler. Scheduling functionality will be disabled.")
    initialize_scheduler = None # Set to None if import fails


logger = logging.getLogger(__name__)


class RSSCollector:
    """
    Main class to orchestrate RSS collection process.
    """

    def __init__(self, settings_path: str, feeds_path: str):
        """
        Initialize RSS collector with configuration.

        Args:
            settings_path: Path to the settings configuration file
            feeds_path: Path to the feeds configuration file
        """
        try:
            # ConfigManager is expected to handle FileNotFoundError during its init
            self.config_manager = ConfigManager(settings_path, feeds_path)

            # Initialize components
            self._init_components()

            # Setup required directories
            self._setup_directories()

            logger.info("RSS Collector initialized successfully")

        except (FileNotFoundError, ValueError, TypeError, JSONDecodeError) as e:
             logger.critical(f"Failed to initialize RSS Collector due to configuration error: {e}", exc_info=True)
             # Re-raise the exception for main() to handle program exit
             raise
        except Exception as e:
            logger.critical(f"An unexpected error occurred during RSS Collector initialization: {e}", exc_info=True)
            raise

    def _init_components(self):
        """Initialize all required components based on configuration."""
        try:
            # Get configuration values safely with defaults
            timeout = self.config_manager.get_config_value("networking.timeout_seconds", 30)
            retry_attempts = self.config_manager.get_config_value("networking.retry_attempts", 3)
            backoff_factor = self.config_manager.get_config_value("networking.backoff_factor", 2.0)
            # Assuming ProxyConfig and set_environment_variables are handled in run.py or similar entry point

            # Initialize RSS fetcher
            # Assuming RSSFetcher constructor can handle potential None values if config is missing
            self.rss_fetcher = RSSFetcher(
                timeout=timeout,
                retry_attempts=retry_attempts,
                backoff_factor=backoff_factor,
                # Assuming proxy_config is handled externally or within RSSFetcher based on environment variables
            )

            # Initialize RSS parser
            self.rss_parser = RSSParser()

            # Initialize storage manager
            base_dir = self.config_manager.get_config_value("storage.base_dir", "./feeds")
            if not base_dir:
                 # This case should ideally be caught by config validation, but added for safety
                 logger.critical("Storage base directory is not configured.")
                 raise ValueError("Storage base directory not configured.")

            self.storage_manager = StorageManager(base_dir)

            logger.info("All components initialized successfully")

        except Exception as e:
            logger.critical(f"Failed to initialize components: {e}", exc_info=True)
            raise

    def _setup_directories(self):
        """Setup required directories for the application."""
        try:
            # Get directory paths from config with defaults
            storage_dir = self.config_manager.get_config_value("storage.base_dir", "./feeds")
            log_dir = self.config_manager.get_config_value("logging.log_dir", "./logs")

            directories = [
                storage_dir,
                log_dir,
                "./config", # Assuming config directory is always relative to the script
                "./output",
                "./output/daily",
                "./output/jsonl"
                # Add other necessary directories based on config (e.g., storage.backup_dir)
            ]

            for directory in directories:
                try:
                    os.makedirs(directory, exist_ok=True)
                    logger.debug(f"Created/verified directory: {directory}")
                except OSError as e:
                     logger.error(f"Failed to create directory {directory}: {e}", exc_info=True)
                     # Decide if directory creation failure is critical enough to stop
                     # For now, log and continue, but a 'raise' might be needed depending on severity
                     pass


        except Exception as e:
            logger.critical(f"Failed to setup directories: {e}", exc_info=True)
            raise

    def run_collection(self):
        """
        Run the RSS collection process for all configured keywords.

        Returns:
            dict: Summary statistics including total articles, new articles, keywords, and errors
        """
        start_time = time.time()
        logger.info("Starting RSS collection process")

        # Initialize stats dictionary before the main try block
        stats = {
            "total_articles": 0,
            "total_new_articles": 0,
            "total_keywords": 0,
            "errors": 0,
            "success_rate": 0,
            "duration_seconds": 0
        }

        try:
            # Get keyword groups - ConfigManager should handle if not loaded
            keyword_groups = self.config_manager.get_keyword_groups()

            # Process each keyword group
            for group_index, group in enumerate(keyword_groups):
                # Added check for valid group structure
                if not isinstance(group, dict) and not isinstance(group, str):
                     logger.warning(f"Invalid keyword group entry at index {group_index}: {group}. Expected dict or str, skipping entry.")
                     stats["errors"] += 1
                     continue

                try:
                    # Extract keywords from the group
                    if isinstance(group, dict):
                        keywords = group.get("terms", [])
                        group_name = group.get("name", f"Group {group_index + 1}")
                        if not isinstance(keywords, list):
                            logger.warning(f"Invalid 'terms' type in keyword group: {group_name}. Expected list, skipping group.")
                            stats["errors"] += 1
                            continue
                    else: # Handle simple string keyword case
                        keywords = [group] if isinstance(group, str) and group.strip() else []
                        group_name = f"Keyword {group_index + 1}"

                    if not keywords:
                        logger.warning(f"No valid keywords found in group: {group_name}, skipping group.")
                        continue

                    logger.info(f"Processing keyword group: {group_name} with {len(keywords)} keywords")

                    # Process each keyword in the group
                    for keyword_index, keyword in enumerate(keywords):
                        # Added check for valid keyword term
                        if not isinstance(keyword, str) or not keyword.strip():
                             logger.warning(f"Invalid keyword term at index {keyword_index} in group \'{group_name}\': {keyword}. Skipping term.")
                             stats["errors"] += 1
                             continue

                        try:
                            stats["total_keywords"] += 1 # Count processed keywords here

                            # Fetch RSS feed
                            logger.info(f"Fetching RSS for keyword: {keyword}")
                            # Assuming fetch_rss handles network errors internally with retries
                            rss_content = self.rss_fetcher.fetch_rss(keyword)

                            if not rss_content:
                                logger.error(f"Failed to fetch RSS for keyword: {keyword}")
                                stats["errors"] += 1 # Increment error count
                                continue

                            # Parse RSS feed
                            # Assuming parse_rss handles parsing errors internally
                            parsed_data = self.rss_parser.parse_rss(rss_content, keyword)

                            if not parsed_data or not parsed_data.get("articles"):
                                logger.warning(f"No articles found or failed to parse for keyword: {keyword}")
                                continue # Not necessarily an error, just no data

                            # Store the parsed data and get storage statistics
                            articles_count = len(parsed_data.get("articles", [])) # Use .get for safety
                            # Assuming store_feed_data handles storage errors internally
                            storage_result = self.storage_manager.store_feed_data(parsed_data)

                            # Handle storage result - Check if storage_result is valid
                            if storage_result and isinstance(storage_result, dict):
                                new_articles_count = storage_result.get('new_articles', 0)
                                duplicates_count = storage_result.get('duplicates_found', 0)

                                # Update statistics
                                stats["total_articles"] += articles_count
                                stats["total_new_articles"] += new_articles_count

                                logger.info(f"Processed keyword \'{keyword}\': {articles_count} fetched, "
                                          f"{new_articles_count} new, {duplicates_count} duplicates")
                            else:
                                logger.error(f"Storage manager returned invalid result for keyword: {keyword}")
                                stats["errors"] += 1 # Consider this an error

                            # Pause between keywords if not the last one
                            if keyword_index < len(keywords) - 1:
                                pause_seconds = self.config_manager.get_config_value("networking.keyword_pause_seconds", 10)
                                if pause_seconds > 0: # Only pause if pause_seconds is positive
                                    logger.debug(f"Pausing for {pause_seconds} seconds before next keyword")
                                    time.sleep(pause_seconds)

                        except Exception as e: # Catching specific potential exceptions might be better here
                            logger.exception(f"Error processing keyword \'{keyword}\': {e}")
                            stats["errors"] += 1 # Increment error count


                    # Pause between groups if not the last one
                    if group_index < len(keyword_groups) - 1:
                        pause_minutes = self.config_manager.get_config_value("networking.group_pause_minutes", 5)
                        if pause_minutes > 0: # Only pause if pause_minutes is positive
                            logger.info(f"Pausing for {pause_minutes} minutes before next keyword group")
                            time.sleep(pause_minutes * 60)

                except Exception as e: # Catching specific potential exceptions might be better here
                    logger.exception(f"Error processing keyword group \'{group_name}\': {e}")
                    stats["errors"] += 1 # Increment error count

            # Calculate final statistics
            stats["duration_seconds"] = time.time() - start_time
            stats["success_rate"] = ((stats["total_keywords"] - stats["errors"]) / stats["total_keywords"] * 100) if stats["total_keywords"] > 0 else 0

            # Log comprehensive summary
            logger.info(f"RSS collection completed in {stats['duration_seconds']:.2f} seconds")
            logger.info(f"Total articles fetched: {stats['total_articles']}")
            logger.info(f"New articles added: {stats['total_new_articles']}")
            logger.info(f"Keywords processed: {stats['total_keywords']}")
            logger.info(f"Errors encountered: {stats['errors']}")
            logger.info(f"Success rate: {stats['success_rate']:.1f}%")

            return stats

        except Exception as e: # Catching broad exception as a final safeguard
            logger.critical(f"Critical error during collection process: {e}", exc_info=True)
            # Update duration in case of early exit
            stats["duration_seconds"] = time.time() - start_time
            stats["errors"] += 1 # Ensure errors is incremented on critical failure
            stats["success_rate"] = ((stats["total_keywords"] - stats["errors"]) / stats["total_keywords"] * 100) if stats["total_keywords"] > 0 else 0
            return stats # Return partial stats even on failure


def run_pipeline(config_manager: ConfigManager):
    """
    Run the RSS pipeline with the given configuration.

    Args:
        config_manager: Configuration manager instance

    Returns:
        Collection results dictionary or None if initialization fails critically.
    """
    try:
        # Initialize RSSCollector - it will handle its own initialization errors
        collector = RSSCollector(config_manager.settings_path, config_manager.feeds_path)
        return collector.run_collection()
    except Exception as e:
        # Errors during initialization or collection are logged by RSSCollector
        # No need to re-log here, just return None to indicate failure
        return None


def main():
    """
    Main entry point for the script.
    """
    parser = argparse.ArgumentParser(
        description="RSS Collector - Intelligent RSS feed collection and processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --run-now                    # Run collection immediately
  python main.py --schedule                   # Start scheduler
  python main.py --run-now --schedule         # Run now and then start scheduler
  python main.py --config-dir custom_config --run-now  # Use custom config directory
        """
    )
    parser.add_argument(
        "--config-dir",
        default="config",
        help="Path to configuration directory (default: config)"
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run collection immediately"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Start scheduler for automatic collection"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="RSS Collector v1.0.0"
    )

    args = parser.parse_args()

    # Setup logging as early as possible
    log_level = 'DEBUG' if args.debug else 'INFO'
    setup_logging(log_level=log_level) # Configure logging before any other significant operations

    try:
        logger.info("Application started.")

        # Setup configuration paths
        config_dir = args.config_dir
        settings_path = os.path.join(config_dir, 'settings.json')
        feeds_path = os.path.join(config_dir, 'feeds.json')

        # Initialize configuration manager - ConfigManager handles file existence and JSON errors during its init
        config_manager = ConfigManager(settings_path, feeds_path)

        # Setup proxy environment - Assuming this reads proxy settings from config_manager.settings
        setup_proxy_environment(config_manager.settings) # Pass the settings dictionary

        # Handle immediate run
        if args.run_now:
            logger.info("Running immediate collection")
            # Use the run_pipeline wrapper
            stats = run_pipeline(config_manager)
            if stats is not None:
                logger.info(f"Immediate collection summary: {json.dumps(stats, indent=2)}")
            else:
                 logger.error("Immediate collection failed.")
                 sys.exit(1)


        # Handle scheduler
        if args.schedule:
            if initialize_scheduler: # Check if scheduler was successfully imported
                logger.info("Preparing to start scheduler")
                # Pass the config_manager instance to initialize_scheduler
                scheduler = initialize_scheduler(config_manager)
                if scheduler:
                    logger.info("Starting scheduler - Press Ctrl+C to stop")
                    try:
                        scheduler.start()
                        # Keep the main thread alive while scheduler runs in the background
                        # A more robust approach might use threading.Event
                        while True:
                            time.sleep(1)
                    except (KeyboardInterrupt, SystemExit):
                        logger.info("Scheduler stopped by user or system signal")
                        if scheduler.running: # Check if scheduler is running before trying to shutdown
                            scheduler.shutdown() # Use shutdown for cleaner exit
                    except Exception as scheduler_e:
                        logger.critical(f"Error during scheduler execution: {scheduler_e}", exc_info=True)
                        if scheduler.running:
                            scheduler.shutdown() # Ensure shutdown on error
                        sys.exit(1) # Exit on critical scheduler error
                else:
                    logger.error("Failed to initialize scheduler.")
                    sys.exit(1) # Exit if scheduler initialization failed
            else:
                logger.warning("Scheduler functionality is disabled due to import errors.")


        # Show help if no action specified
        if not args.run_now and not args.schedule:
            logger.warning("No action specified. Use --run-now or --schedule")
            parser.print_help()

    except (KeyboardInterrupt, SystemExit):
        logger.info("Process interrupted by user or system signal.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"An unexpected critical error occurred in main execution: {e}", exc_info=True)
        sys.exit(1)
    # No finally block needed here for proxy environment variables if setup_proxy_environment handles cleanup

if __name__ == "__main__":
    main()
