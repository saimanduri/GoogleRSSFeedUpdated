"""
Configuration manager for RSS Collector.
Handles loading and validation of configuration settings.
"""
import json
import logging
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from json.decoder import JSONDecodeError # Import specific exception

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages configuration loading and keyword extraction.
    """

    def __init__(self, settings_path: str, feeds_path: str):
        """
        Initialize configuration manager.

        Args:
            settings_path: Path to main settings file (settings.json)
            feeds_path: Path to feeds configuration file (feeds.json)
        """
        self.settings_path = settings_path
        self.feeds_path = feeds_path
        self.settings = None
        self.feeds_config = None

        logger.debug(f"ConfigManager initialized with settings: {settings_path}, feeds: {feeds_path}")

        # Load configurations and handle FileNotFoundError specifically during init
        try:
            self._load_all_configs()
        except FileNotFoundError as e:
            logger.critical(f"Fatal: Configuration file not found: {e}. Please ensure settings.json and feeds.json exist in the config directory.", exc_info=True)
            # Re-raise the exception as it's a critical failure during initialization
            raise

    def _load_all_configs(self):
        """Load all configuration files."""
        self.settings = self._load_json_file(self.settings_path, "settings")
        self.feeds_config = self._load_json_file(self.feeds_path, "feeds")

        # Validate configurations
        self._validate_settings()
        self._validate_feeds_config()

    def _load_json_file(self, file_path: str, config_type: str) -> Dict[str, Any]:
        """
        Load a JSON configuration file.

        Args:
            file_path: Path to JSON file
            config_type: Type of config for error messages

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
            Exception: For any other errors during file loading.
        """
        try:
            # Redundant os.path.exists check removed, relying on open()
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            logger.info(f"Loaded {config_type} configuration from {file_path}")
            return config

        except FileNotFoundError:
            # Re-raise FileNotFoundError to be handled by the caller (e.g., __init__ or main)
            raise
        except JSONDecodeError as e:
            logger.error(f"Invalid JSON in {config_type} configuration file \'{file_path}\': {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading {config_type} configuration from \'{file_path}\': {e}")
            raise

    def _validate_settings(self):
        """Validate settings configuration."""
        if not self.settings:
            raise ValueError("Settings configuration is empty")

        # Define required sections and their expected types or structures
        required_sections = {
            "networking": dict,
            "storage": dict,
            "logging": dict,
            "schedule": dict
        }

        for section, expected_type in required_sections.items():
            if section not in self.settings:
                logger.warning(f"Missing required configuration section: \'{section}\', using defaults")
                self.settings[section] = {} # Initialize with empty dict if missing
            elif not isinstance(self.settings[section], expected_type):
                 raise TypeError(f"Invalid type for configuration section \'{section}\'. Expected {expected_type.__name__}")

        # Set defaults for missing values (improved logic to handle nested defaults)
        self._set_default_settings()

        # Add more specific validation for key values
        self._validate_specific_settings()

        logger.info("Settings configuration validated")

    def _validate_specific_settings(self):
        """Validate specific key values within settings."""
        # Validate networking settings
        networking = self.settings.get("networking", {})
        if not isinstance(networking.get("timeout_seconds"), (int, float)):
             raise TypeError("Invalid type for 'networking.timeout_seconds'. Expected int or float.")
        if not isinstance(networking.get("retry_attempts"), int):
             raise TypeError("Invalid type for 'networking.retry_attempts'. Expected int.")
        if not isinstance(networking.get("backoff_factor"), (int, float)):
             raise TypeError("Invalid type for 'networking.backoff_factor'. Expected int or float.")
        if not isinstance(networking.get("keyword_pause_seconds"), (int, float)):
             raise TypeError("Invalid type for 'networking.keyword_pause_seconds'. Expected int or float.")
        if not isinstance(networking.get("group_pause_minutes"), (int, float)):
             raise TypeError("Invalid type for 'networking.group_pause_minutes'. Expected int or float.")


        # Validate storage settings
        storage = self.settings.get("storage", {})
        if not storage.get("base_dir") or not isinstance(storage.get("base_dir"), str):
             raise TypeError("Missing or invalid type for 'storage.base_dir'. Expected non-empty string.")

        # Validate schedule settings
        schedule = self.settings.get("schedule", {})
        if "times" not in schedule or not isinstance(schedule["times"], list):
             raise TypeError("Missing or invalid type for 'schedule.times'. Expected a list of times.")
        # Optional: Add validation for the time format strings in schedule["times"] if needed
        if "timezone" in schedule and not isinstance(schedule["timezone"], str):
             raise TypeError("Invalid type for 'schedule.timezone'. Expected a string.")


        # Validate logging settings
        logging_settings = self.settings.get("logging", {})
        if "level" in logging_settings and not isinstance(logging_settings["level"], str):
             raise TypeError("Invalid type for 'logging.level'. Expected a string.")
        # Add more logging validation as needed (e.g., valid log levels)


        # Validate features settings (example)
        features = self.settings.get("features", {})
        if "deduplication_enabled" in features and not isinstance(features["deduplication_enabled"], bool):
            raise TypeError("Invalid type for 'features.deduplication_enabled'. Expected boolean.")


    def _validate_feeds_config(self):
        """Validate feeds configuration."""
        if not self.feeds_config:
            raise ValueError("Feeds configuration is empty")

        if "keywords" not in self.feeds_config:
            raise ValueError("Missing \'keywords\' section in feeds configuration")

        keywords = self.feeds_config["keywords"]
        if not isinstance(keywords, list) or len(keywords) == 0:
            raise ValueError("Keywords must be a non-empty list")

        # Optional: Add validation for the structure of keyword entries
        for i, entry in enumerate(keywords):
            if isinstance(entry, dict):
                if "name" not in entry or not isinstance(entry["name"], str):
                     raise ValueError(f"Invalid keyword group at index {i}: missing or invalid 'name'")
                if "terms" not in entry or not isinstance(entry["terms"], list) or len(entry["terms"]) == 0:
                     raise ValueError(f"Invalid keyword group at index {i}: missing or invalid 'terms' list")
                for j, term in enumerate(entry["terms"]):
                    if not isinstance(term, str) or not term.strip():
                        raise ValueError(f"Invalid keyword term at index {j} in group '{entry['name']}': Expected non-empty string.")
            elif isinstance(entry, str):
                 if not entry.strip():
                     raise ValueError(f"Invalid simple keyword entry at index {i}: Expected non-empty string.")
            else:
                 raise ValueError(f"Invalid keyword entry at index {i}: Expected a dictionary or a string.")


        # Optional: Validate rss_sources section
        rss_sources = self.feeds_config.get("rss_sources", {})
        if "google_news_base_url" in rss_sources and not isinstance(rss_sources["google_news_base_url"], str):
             raise TypeError("Invalid type for 'rss_sources.google_news_base_url'. Expected a string.")
        if "user_agent" in rss_sources and not isinstance(rss_sources["user_agent"], str):
             raise TypeError("Invalid type for 'rss_sources.user_agent'. Expected a string.")


        logger.info("Feeds configuration validated")

    def _set_default_settings(self):
        """Recursively set default values for missing settings."""
        defaults = {
            "networking": {
                "timeout_seconds": 30,
                "retry_attempts": 3,
                "backoff_factor": 2.0,
                "keyword_pause_seconds": 10,
                "group_pause_minutes": 5,
                "user_agent": "RSS-Collector/1.0 (+https://example.com/bot)"
            },
            "storage": {
                "base_dir": "./feeds",
                "cleanup_days": 30,
                "create_jsonl": True,
                "backup_enabled": False
            },
            "logging": {
                "level": "INFO",
                "log_dir": "./logs",
                "max_log_files": 10,
                "log_rotation": "daily"
            },
            "schedule": {
                "times": ["05:00", "14:00"],
                "timezone": "Asia/Kolkata",
                "enabled": True
            },
            "features": {
                "deduplication_enabled": True,
                "content_hashing": True,
                "statistics_enabled": True,
                "proxy_support": True
            }
        }

        def merge_dicts(source, default):
            """Recursively merges default dict into source dict."""
            for key, value in default.items():
                if key not in source:
                    source[key] = value
                elif isinstance(value, dict) and isinstance(source[key], dict):
                    merge_dicts(source[key], value)
                # No else: existing values in source take precedence

        # Merge defaults with existing settings
        merge_dicts(self.settings, defaults)


    def get_keywords(self) -> List[str]:
        """
        Extract all keywords from feeds configuration.

        Returns:
            List of all keywords/terms to fetch

        Raises:
            ValueError: If feeds configuration is not loaded or keywords section is invalid.
            TypeError: If keyword structure is invalid.
        """
        if not self.feeds_config:
            logger.error("Feeds configuration not loaded when trying to get keywords.")
            # Depending on desired behavior, could return [] or raise a specific error
            return [] # Returning empty list as a safe default

        keywords = []

        try:
            keyword_groups = self.feeds_config.get("keywords", [])

            if not isinstance(keyword_groups, list):
                 raise TypeError("Feeds configuration 'keywords' section must be a list.")

            for group in keyword_groups:
                if isinstance(group, dict):
                    # Handle grouped keywords
                    terms = group.get("terms", [])
                    if not isinstance(terms, list):
                        logger.warning(f"Invalid 'terms' type in keyword group: {group}. Expected list, skipping group.")
                        continue
                    keywords.extend(terms)
                elif isinstance(group, str):
                    # Handle simple string keywords
                    keywords.append(group)
                else:
                    logger.warning(f"Invalid keyword entry type: {group}. Expected dict or str, skipping entry.")


            # Remove duplicates while preserving order
            unique_keywords = []
            seen = set()
            for keyword in keywords:
                if isinstance(keyword, str) and keyword.strip(): # Ensure keyword is a non-empty string
                    if keyword not in seen:
                        unique_keywords.append(keyword)
                        seen.add(keyword)
                else:
                    logger.warning(f"Skipping invalid keyword value: {keyword}")

            logger.info(f"Extracted {len(unique_keywords)} unique keywords")
            return unique_keywords

        except Exception as e: # Catching broad exception as a safeguard, re-evaluate if more specific exceptions can cover all cases
            logger.error(f"Error extracting keywords from feeds configuration: {e}", exc_info=True)
            return []


    def get_keyword_groups(self) -> List[Dict[str, Any]]:
        """
        Get keyword groups with their metadata.

        Returns:
            List of keyword group dictionaries
        """
        if not self.feeds_config:
             logger.warning("Feeds configuration not loaded, returning empty keyword groups.")
             return []
        return self.feeds_config.get("keywords", [])

    def get_config_value(self, key_path: str, default=None):
        """
        Get configuration value using dot notation.

        Args:
            key_path: Dot-separated path to configuration value (e.g., "storage.base_dir")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if not self.settings:
            logger.warning(f"Settings configuration not loaded when trying to get value for '{key_path}'. Returning default.")
            return default

        keys = key_path.split('.')
        value = self.settings

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value
