"""
Helper functions for RSS Collector.
Contains utility functions for URL construction and date handling.
"""
import hashlib
import json
import urllib.parse
import time
import random
from datetime import datetime
from dateutil import parser as date_parser
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def construct_google_news_url(keyword: str, language: str = "en", country: str = "IN") -> str:
    """
    Construct a Google News RSS URL for a given keyword.
    
    Args:
        keyword: Search term or phrase
        language: Language code (default: "en")
        country: Country code (default: "IN")
    
    Returns:
        Complete Google News RSS URL
    """
    # URL encode the keyword to handle spaces and special characters
    encoded_keyword = urllib.parse.quote_plus(keyword)
    
    # Base Google News RSS URL
    base_url = "https://news.google.com/rss/search"
    
    # Construct query parameters
    params = {
        'q': encoded_keyword,
        'hl': language,
        'gl': country,
        'ceid': f"{country}:{language}"
    }
    
    # Build the complete URL
    query_string = urllib.parse.urlencode(params)
    complete_url = f"{base_url}?{query_string}"
    
    logger.debug(f"Constructed Google News URL for keyword '{keyword}': {complete_url}")
    return complete_url


def normalize_date(date_string: str) -> str:
    """
    Normalize date strings to a consistent ISO format for LLM processing.
    
    Args:
        date_string: Raw date string from RSS feed
    
    Returns:
        Normalized date string in ISO format or original string if parsing fails
    """
    if not date_string or not date_string.strip():
        return ""
    
    try:
        # Parse the date string using dateutil parser (handles many formats)
        parsed_date = date_parser.parse(date_string)
        
        # Convert to ISO format (YYYY-MM-DDTHH:MM:SSZ)
        normalized = parsed_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        logger.debug(f"Normalized date '{date_string}' to '{normalized}'")
        return normalized
        
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse date '{date_string}': {e}")
        # Return original string if parsing fails
        return date_string.strip()


def clean_text(text: str, max_length: int = None) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Raw text to clean
        max_length: Maximum length to truncate to (optional)
    
    Returns:
        Cleaned text string
    """
    if not text:
        return ""
    
    import re

    # Remove HTML tags
    cleaned = re.sub(r'<[^>]+>', ' ', text)

    # Remove HTML entities
    cleaned = re.sub(r'&[a-zA-Z0-9#]+;', ' ', cleaned)

    # Strip whitespace
    cleaned = cleaned.strip()
    
    # Normalize whitespace (replace multiple spaces/newlines with single space)
    import re
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Truncate if max_length specified
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip() + "..."
    
    return cleaned

def create_article_hash(title: str, pub_date: str) -> str:
    """
    Generate a SHA-256 hash from title and publication date for deduplication.
    
    Args:
        title: Article title
        pub_date: Publication date (normalized string)
        
    Returns:
        SHA-256 hash string
    """
    if not title:
        title = ""
    if not pub_date:
        pub_date = ""
        
    # Use a separator that is unlikely to appear in title or date
    content = f"{title.strip()}|{pub_date.strip()}".encode('utf-8')
    return hashlib.sha256(content).hexdigest()


def validate_json_structure(data: Dict[str, Any], schema: Dict) -> bool:
    """
    Validate if a dictionary conforms to a simple schema (checks for required keys and basic types).
    
    Args:
        data: Dictionary to validate
        schema: Schema dictionary with required keys and expected types
        
    Returns:
        True if data conforms to schema, False otherwise
    """
    if not isinstance(data, dict):
        logger.warning("Validation failed: Data is not a dictionary")
        return False

    for key, expected_type in schema.items():
        if key not in data:
            logger.warning(f"Validation failed: Missing required key '{key}'")
            return False
        if not isinstance(data[key], expected_type):
             # Allow None for Optional fields, but check type if not None
            if expected_type is not type(None) and data[key] is not None and not isinstance(data[key], expected_type):
                logger.warning(f"Validation failed: Key '{key}' has wrong type. Expected {expected_type}, got {type(data[key])}")
                return False

    return True

# Define expected JSON schemas
ARTICLE_SCHEMA = {
    'title': str,
    'link': str,
    'published': str, # ISO format string
    'source': str,
    'snippet': str, # Cleaned and potentially truncated
    'id_hash': str, # SHA-256 hash based on title and published date
}

RSS_FEED_SCHEMA = {
    'fetched_at': str, # ISO format timestamp
    'query': str,
    'source_url': str,
    'articles': list # List of dictionaries conforming to ARTICLE_SCHEMA
}


def retry_with_backoff(func, max_retries: int, initial_delay: float, backoff_factor: float = 2.0):
    """
    Retry a function call with exponential backoff.
    
    Args:
        func: The function to call.
        max_retries: The maximum number of retries.
        initial_delay: The initial delay in seconds before the first retry.
        backoff_factor: The factor by which the delay increases each retry.
    
    Returns:
        The result of the function call if successful.
        
    Raises:
        Exception: If the function fails after max_retries.
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries:
                raise
            delay = initial_delay * (backoff_factor ** attempt) + random.uniform(0, initial_delay * 0.5) # Add jitter
            logger.warning(f"Attempt {attempt + 1} failed. Retrying in {delay:.2f}s: {e}")
            time.sleep(delay)


def validate_url(url: str) -> bool:
    """
    Validate if a string is a proper URL.
    
    Args:
        url: URL string to validate
    
    Returns:
        True if valid URL, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    try:
        parsed = urllib.parse.urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def extract_domain(url: str) -> str:
    """
    Extract domain name from a URL.
    
    Args:
        url: Full URL string
    
    Returns:
        Domain name or empty string if extraction fails
    """
    if not url:
        return ""
    
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""


def safe_filename(text: str, max_length: int = 50) -> str:
    """
    Convert text to a safe filename by removing/replacing invalid characters.
    
    Args:
        text: Text to convert
        max_length: Maximum filename length
    
    Returns:
        Safe filename string
    """
    if not text:
        return "unnamed"
    
    import re
    
    # Replace invalid filename characters with underscores
    safe = re.sub(r'[<>:"/\\|?*]', '_', text)
    
    # Replace spaces with underscores
    safe = safe.replace(' ', '_')
    
    # Remove multiple consecutive underscores
    safe = re.sub(r'_+', '_', safe)
    
    # Remove leading/trailing underscores
    safe = safe.strip('_')
    
    # Truncate if too long
    if len(safe) > max_length:
        safe = safe[:max_length].rstrip('_')
    
    # Ensure we have something
    if not safe:
        safe = "unnamed"
    
    return safe.lower()
