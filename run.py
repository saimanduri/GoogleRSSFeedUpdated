#!/usr/bin/env python3
"""
Main entry point for the Google News RSS Ingestion Pipeline.
This script initializes the system and starts the scheduler.
"""
import os
import sys
import argparse
import logging
from pathlib import Path

# Ensure the project root is in the Python path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from src.utils.logging_utils import setup_logging
from src.config_manager import ConfigManager
from src.scheduler import initialize_scheduler, Scheduler
from src.utils.proxy_utils import ProxyConfig, set_environment_variables
from src.rss_fetcher import RSSFetcher
from src.rss_parser import RSSParser
# Import specific exceptions you want to handle more granularly
from requests.exceptions import RequestException # Example for network errors
from json.decoder import JSONDecodeError # Example for JSON errors

logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Google News RSS Ingestion Pipeline'
    )
    parser.add_argument(
        '--config-dir', 
        type=str, 
        default='config',
        help='Path to configuration directory'
    )
    parser.add_argument(
        '--run-now', 
        action='store_true',
        help='Run once immediately instead of scheduling'
    )
    parser.add_argument(
        '--debug', 
        action='store_true',
        help='Enable debug logging'
    )

    return parser.parse_args()

def main():
    """Main entry point for the application."""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Create necessary directories if they don't exist
    for directory in ['logs', 'feeds']:
        os.makedirs(directory, exist_ok=True)
    
    # Setup logging
    log_level = 'DEBUG' if args.debug else None
    setup_logging(log_level=log_level, log_dir='logs') # Using the setup_logging function directly
    logger.info("Starting RSS Ingestion Pipeline")

    config_manager = None # Initialize to None for finally block access
    try:
        # Load configuration
        config_path = Path(args.config_dir)
        settings_path = config_path / 'settings.json'
        feeds_path = config_path / 'feeds.json'
        
        if not settings_path.exists() or not feeds_path.exists():
            logger.error(f"Configuration files not found at {config_path}. Please ensure 'settings.json' and 'feeds.json' exist.")
            logger.error("You can run the setup_directories.py script to create default configuration files.")
            sys.exit(1) # Exit since configuration is essential

        config_manager = ConfigManager(
            settings_path=str(settings_path),
            feeds_path=str(feeds_path)
        )

        # Configure proxy if enabled
        proxy_settings = config_manager.get_config_value("proxy", {})
        proxy_config = ProxyConfig(**proxy_settings)
        
        if proxy_config.enabled:
            set_environment_variables(proxy_config)
            # Optional: Test proxy connectivity
            logger.info("Testing proxy connectivity...")
            if not proxy_config.test_connectivity():
                logger.critical("Proxy connectivity test failed. Cannot proceed with fetching.")
                # Decide whether to exit or proceed without proxy based on requirements
                # For this example, we'll exit as proxy seems configured but not working
                sys.exit(1) 
            logger.info("Proxy connectivity test successful.")

        # Initialize components
        # Using .get_config_value with default for robustness
        timeout = config_manager.get_config_value("networking.timeout_seconds", 30)
        retry_attempts = config_manager.get_config_value("networking.retry_attempts", 3)
        backoff_factor = config_manager.get_config_value("networking.backoff_factor", 2.0)

        rss_fetcher = RSSFetcher(
            timeout=timeout,
            retry_attempts=retry_attempts,
            backoff_factor=backoff_factor,
            proxy_config=proxy_config # Pass the initialized proxy config
        )

        rss_parser = RSSParser()

        storage_base_dir = config_manager.get_config_value("storage.base_dir", "./feeds")
        storage_manager = StorageManager(storage_base_dir)

        # Import run_pipeline here to avoid circular dependency issues if main imports run_pipeline wrapper
        # Assuming run_pipeline is defined in src/main.py
        try:
            from src.main import run_pipeline
        except ImportError:
            logger.critical("Could not import run_pipeline from src.main.py. Ensure the file and function exist.")
            sys.exit(1)


        if args.run_now:
            # Run once immediately without scheduling
            logger.info("Running pipeline immediately (one-time execution)")
            run_pipeline(config_manager, rss_fetcher, rss_parser, storage_manager)
        elif config_manager.get_config_value("schedule.times"):
            # Start the scheduler
            logger.info("Initializing scheduler")
            # Define the job function that the scheduler will run
            def scheduled_collection_job():
                 # Wrap the pipeline run in a try-except to log job-specific errors
                 try:
                     run_pipeline(config_manager, rss_fetcher, rss_parser, storage_manager)
                 except Exception as job_e:
                     logger.error(f"Error during scheduled job execution: {job_e}", exc_info=True)


            scheduler = initialize_scheduler(config_manager, scheduled_collection_job)
            try:
                scheduler.start()
                logger.info("Scheduler started. Press Ctrl+C to stop.")
                # Keep the main thread alive while scheduler runs in the background
                # This is a simple way; more complex apps might use signals or events
                while True:
                    import time
                    time.sleep(1) # Keep main thread alive
            except (KeyboardInterrupt, SystemExit):
                logger.info("Scheduler stopped by user/system signal")
                scheduler.shutdown() # Use shutdown for cleaner exit
            except Exception as scheduler_e:
                logger.error(f"Error during scheduler operation: {scheduler_e}", exc_info=True)
                scheduler.shutdown() # Ensure shutdown on error
        else:
             logger.warning("No run action (--run-now or --schedule) specified in command line arguments or schedule times configured in settings.json. Exiting.")


    # More granular exception handling
    except FileNotFoundError as fnf_e:
        logger.critical(f"Required file not found: {fnf_e}. Ensure all configuration and source files are in place.", exc_info=True)
        sys.exit(1)
    except JSONDecodeError as json_e:
        logger.critical(f"Error decoding JSON configuration file: {json_e}. Check your config files for syntax errors.", exc_info=True)
        sys.exit(1)
    except RequestException as req_e:
        logger.critical(f"Network error during initialization: {req_e}. Check your internet connection, proxy settings, or firewall.", exc_info=True)
        sys.exit(1)
    except ImportError as im_e:
        logger.critical(f"Import error: {im_e}. Check your Python environment and project structure.", exc_info=True)
        sys.exit(1)
    except Exception as e:
        logger.critical(f"An unexpected fatal error occurred: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Clean up environment variables set for proxy if necessary
        # Accessing proxy_config safely in finally block
        if 'proxy_config' in locals() and proxy_config.enabled:
             proxy_config.unset_environment_variables()

if __name__ == "__main__":
    main()
