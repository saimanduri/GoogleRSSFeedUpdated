#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rss_fetcher.py - Module for fetching RSS feeds using requests and proxy.
"""

import time
import random
import logging
import concurrent.futures
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from user_agent import generate_user_agent
import requests # Import requests

# Import helper functions and schemas
from src.utils.helpers import (
    construct_google_news_url,
    clean_text, # Although clean_text is mainly used in parser, keep import if any direct use here
    normalize_date, # Although normalize_date is mainly used in parser, keep import if any direct use here
    create_article_hash, # Although create_article_hash is mainly used in parser, keep import if any direct use here
    validate_json_structure,
    retry_with_backoff, # Import retry_with_backoff from helpers
    RSS_FEED_SCHEMA # Import schema from helpers
)
from src.utils.proxy_utils import (
    ProxyConfig,
    create_proxy_aware_session
)
from src.rss_parser import RSSParser

# Setup logger
# Assuming setup_module_logger is available in logging_utils
from utils.logging_utils import setup_module_logger
logger = setup_module_logger(__name__)


class RSSFetcher:
    """
    Class for fetching RSS feeds using a requests session with proxy support.
    Relies on RSSParser for parsing the fetched content.
    """

    def __init__(self, timeout: int = 30,
                 max_retries: int = 3, request_delay: float = 1.0,
                 proxy_config: Optional[ProxyConfig] = None,
                 parser: RSSParser = None): # Expect parser to be injected
        """
        Initialize the RSS Fetcher with configuration and dependencies.

        Args:
            timeout (int): Request timeout in seconds.
            max_retries (int): Maximum number of retries for failed requests.
            request_delay (float): Delay between requests in seconds.
            proxy_config (Optional[ProxyConfig]): Proxy configuration.
            parser (RSSParser): RSSParser instance for parsing fetched content.
        """
        if parser is None:
             logger.error("RSSParser instance not provided to RSSFetcher.")
             # Depending on how critical, could raise an error or try to create one,
             # but injection is the intended pattern.
             # For now, will allow None but log an error.
             pass # Consider raising ValueError("RSSParser instance must be provided")


        self.timeout = timeout
        self.max_retries = max_retries
        self.request_delay = request_delay
        self.proxy_config = proxy_config
        self.parser = parser # Store the injected parser

        # Create a requests session with proxy configuration
        self.session = create_proxy_aware_session(self.proxy_config)

        logger.debug("RSSFetcher initialized with requests session and parser")


    def _build_url(self, keyword: str) -> str:
        """
        Build the Google News RSS URL for a given keyword.

        Args:
            keyword (str): Keyword to search for

        Returns:
            str: URL for the RSS feed
        """
        # Uses construct_google_news_url from helpers
        return construct_google_news_url(keyword)

    def _fetch_raw_content(self, url: str) -> Optional[str]:
        """
        Fetches raw RSS feed content from the given URL with retries and backoff.

        Args:
            url (str): URL of the RSS feed

        Returns:
            Optional[str]: Raw feed content (text) or None if fetch failed after retries.
        """
        def fetch():
            headers = {
                'User-Agent': generate_user_agent(), # Use a dynamic UA
                'Accept': 'application/rss+xml, application/xml, text/xml;q=0.9',
                'Accept-Language': 'en-US,en;q=0.5'
            }

            logger.debug(f"Attempting to fetch {url}")
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            logger.debug(f"Successfully fetched {url}")
            return response.text

        # Retry with backoff strategy
        try:
            # retry_with_backoff handles logging attempts/failures internally
            raw_content = retry_with_backoff(
                func=fetch,
                max_retries=self.max_retries,
                initial_delay=1, # Use a small initial delay for retries
                backoff_factor=2.0,
                logger=logger # Pass logger to retry_with_backoff for logging
            )
            return raw_content

        except Exception as e:
            # Final failure after all retries
            logger.error(f"Final attempt failed to fetch feed from {url}: {str(e)}")
            return None


    def fetch_feed(self, keyword: str) -> Optional[Dict]:
        """
        Fetches raw content for a keyword, parses it, and returns structured feed data.

        Args:
            keyword (str): Keyword to search for

        Returns:
            Optional[Dict]: Parsed feed data dictionary or None if fetching/parsing failed.
        """
        logger.info(f"Starting fetch and parse for keyword: '{keyword}'")
        # Build the URL
        url = self._build_url(keyword)

        # Add jitter to delay to prevent predictable patterns and be polite
        jitter = random.uniform(0, 0.5)
        time.sleep(self.request_delay + jitter) # Add delay before fetching

        # Fetch the raw content
        raw_content = self._fetch_raw_content(url)
        if not raw_content:
            logger.error(f"Failed to get raw content for keyword: '{keyword}'")
            return None

        # Parse the raw content using the injected parser
        if self.parser is None:
            logger.error("Cannot parse content: RSSParser instance is not available.")
            return None

        logger.info(f"Parsing raw content for keyword: '{keyword}'")
        try:
            parsed_feed_data = self.parser.parse_rss(raw_content, keyword)
            logger.info(f"Parsing completed for keyword: '{keyword}'. Extracted {len(parsed_feed_data.get('articles', []))} articles.")

        except Exception as e:
            logger.exception(f"Error during parsing for keyword '{keyword}': {e}")
            return None


        # The structure returned by parser should already be close to the desired format,
        # including 'fetched_at', 'query', 'source_url', and 'articles'.
        # We can optionally add/override metadata here if needed.
        # Ensuring 'fetched_at' reflects when the fetch+parse process finished for this keyword is reasonable.
        parsed_feed_data['fetched_at'] = datetime.now().isoformat()
        parsed_feed_data['query'] = keyword # Ensure query is correct

        # The source_url should ideally come from the parser if available from the feed itself,
        # but using the fetched URL as a fallback is also fine.
        if not parsed_feed_data.get('source_url'):
             parsed_feed_data['source_url'] = url


        # Validate the final structured feed data
        if not validate_json_structure(parsed_feed_data, RSS_FEED_SCHEMA):
            logger.error(f"Invalid final feed structure for keyword '{keyword}'. Validation failed.")
            # Log the data that failed validation for debugging
            # logger.debug(f"Data that failed validation: {json.dumps(parsed_feed_data, indent=2)}")
            return None

        logger.debug(f"Successfully fetched and parsed feed for keyword: '{keyword}'")

        return parsed_feed_data
