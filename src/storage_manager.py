"""
Storage Manager module for handling JSON file storage and deduplication.
"""
import json
import logging
import os, sys
import hashlib  # Use hashlib for SHA-256
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set
from src.utils.logging_utils import log_deduplication_results

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Manages storage and deduplication of RSS feed data in JSON files.
    """
    
    def __init__(self, base_dir: str = 'feeds'):
        """
        Initialize the storage manager.
        
        Args:
            base_dir: Base directory for storing feeds
        """
        self.base_dir = base_dir
        self.feeds_dir = os.path.join(base_dir, 'feeds') if base_dir != 'feeds' else base_dir
        
        # Ensure directory exists
        try:
            os.makedirs(self.feeds_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create feeds directory {self.feeds_dir}: {e}")
        
        logger.debug(f"StorageManager initialized with feeds directory: {self.feeds_dir}")
    
    def _get_daily_file_path(self, date: datetime) -> str:
        """
        Get the file path for a specific date.
        
        Args:
            date: Date object
            
        Returns:
            Full file path for the date
        """
        date_str = date.strftime('%Y-%m-%d')
        return os.path.join(self.feeds_dir, f"{date_str}.json")
    
    def _load_existing_data(self, date: datetime) -> Dict[str, Any]:
        """
        Load existing feed data for a specific date.
        Returns a dictionary representing the day's data, keyed by article link or id_hash.
        
        Args: 
            date: Date to load data for
            
        Returns:
            List of existing feed data or empty list if file doesn't exist
        """
        file_path = self._get_daily_file_path(date)
        
        if not os.path.exists(file_path):
            logger.debug(f"No existing data file found: {file_path}")
            return {} # Return an empty dictionary for daily storage
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if not isinstance(data, dict): # Expecting a dictionary for daily storage
                logger.warning(f"Invalid data format in {file_path}, expected dict. Returning empty dict.")
                return {}
                
            logger.debug(f"Loaded {len(data)} existing feed entries from {file_path}")
 return data
            
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in {file_path}. Returning empty list.")
            return []
            
        except Exception as e:
            logger.error(f"Error loading data from {file_path}: {e}")
            return []
    
    def _save_data(self, data: Dict[str, Any], date: datetime) -> None:
        """
        Save feed data to file for a specific date.
        
        Args:
            data: List of feed data to save
            date: Date for the data
        """
        file_path = self._get_daily_file_path(date)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(list(data.values()), f, indent=2, ensure_ascii=False) # Save list of articles

            logger.debug(f"Saved {len(data)} unique articles to {file_path}")

        except Exception as e:
            logger.error(f"Error saving data to {file_path}: {e}")
            raise

    def _append_jsonl(self, articles: List[Dict[str, Any]], date: datetime) -> None:
        """Append articles to the daily JSONL file."""
        file_path = self._get_daily_file_path(date).replace(".json", ".jsonl")
            
        try:
            with open(file_path, "a", encoding="utf-8") as jf: # Use "a" for append mode
                for article in articles:
                    json.dump(article, jf, ensure_ascii=False)
                    jf.write("\n")
        except Exception as e:
            logger.error(f"Error saving data to {file_path}: {e}")
            raise

    def _is_duplicate(self, article: Dict[str, Any], existing_links: Set[str], existing_hashes: Set[str]) -> bool:
        """
        Check if an article is a duplicate based on link or content hash.

        Args:
            article: Article to check
            existing_links: Set of existing article links
            existing_hashes: Set of existing article hashes

        Returns:
            True if article is a duplicate, False otherwise
        """
        article_link = article.get('link', '').strip()

        # Primary check: compare links if exists
        if article_link and article_link in existing_links:
            return True

        # Fallback check: compare title+published hash
        article_hash = self._get_article_hash(article)
        if article_hash and article_hash in existing_hashes:
            return True

        return False

    def _get_article_hash(self, article: Dict[str, Any]) -> str:
        """
        Generate a SHA-256 hash for an article based on its unique identifier (link or title+published).

        Args:
            article: Article dictionary

        Returns:
            SHA-256 hash string
        """
        title = article.get('title', '').strip()
        published = article.get('published', '').strip()
        link = article.get('link', '').strip()

        # Use link if available, otherwise use title and published date
        unique_id = link if link else f"{title}|{published}"

        if not unique_id:
            return "" # Cannot generate hash if no unique identifier

        return hashlib.sha256(unique_id.encode('utf-8')).hexdigest()

    def store_feed_data(self, feed_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Store feed data with deduplication.

        Args:
            feed_data: Feed data dictionary containing articles and metadata

        Returns:
            Dictionary with statistics about the storage operation
        """
        today = datetime.now()

        # Load existing data for today and prepare sets for efficient lookup
        # existing_data is a dictionary where keys are article identifiers (link or hash)
        # and values are the full article dictionaries.
        existing_data_dict = self._load_existing_data(today)

        # Create sets for quick duplicate checking
        existing_links = {article.get('link', '').strip() for article in existing_data_dict.values() if article.get('link')}
        existing_hashes = {self._get_article_hash(article) for article in existing_data_dict.values() if not article.get('link')}

        # Process articles from the current feed_data
        incoming_articles = feed_data.get('articles', [])
        new_articles_list = [] # List of newly added articles from this feed_data
        total_processed = len(incoming_articles)
        duplicates_found = 0

        for article in incoming_articles:
            article_id = article.get('link', '').strip() or self._get_article_hash(article)

            if not article_id:
                logger.warning(f"Article missing link and title+published, skipping: {article.get('title', 'N/A')}")
                duplicates_found += 1 # Count as effectively not added
                continue

            # Check if this article already exists in the day's collection
            if article_id in existing_data_dict:
                 duplicates_found += 1
                 continue

            # Check for duplicates using the sets if the primary ID (link or hash) wasn't found
            # This handles cases where an article might have a link in the existing data but
            # the incoming article lacks one (or vice versa), or where the hash needs checking.
            if self._is_duplicate(article, existing_links, existing_hashes):
                 duplicates_found += 1
                 continue

            # If not a duplicate, add to the list of new articles and the main dictionary
            new_articles_list.append(article)
            existing_data_dict[article_id] = article
            # Update sets for subsequent checks within the same incoming batch (minor optimization)
            article_link = article.get('link', '').strip()
            if article_link:
                 existing_links.add(article_link)
            else:
                 existing_hashes.add(self._get_article_hash(article))

        # If any new articles were found from this feed_data, save the entire day's data
        # and append to the JSONL file.
        new_articles_count = len(new_articles_list)
        if new_articles:
            # Save updated data
            self._save_data(existing_data_dict, today)

            # Append new articles to the daily JSONL file
            self._append_jsonl(new_articles_list, today)
        
        # Return statistics
        stats = {
            'new_articles': len(new_articles),
            'duplicates_found': duplicates_found,
            'total_articles': len(articles)
        }

        # Log deduplication results using utility function
        log_deduplication_results(logger, stats['total_articles'], stats['new_articles'], stats['duplicates_found'])
        
        logger.info(f"Stored feed data: {stats}")
        return stats
    
    def get_daily_stats(self, date: datetime) -> Dict[str, Any]:
        """
        Get statistics for a specific date.
        
        Args:
            date: Date to get statistics for
            
        Returns:
            Dictionary with daily statistics
        """
        # Load data into the dictionary format
        data_dict = self._load_existing_data(date)
        total_articles = len(data_dict) # Count unique articles stored
        
        return {
            'date': date.strftime('%Y-%m-%d'),
 'total_articles': total_articles
        }
    
    def list_available_dates(self) -> List[str]:
        """
        List all available dates with stored data.
        
        Returns:
            List of date strings in YYYY-MM-DD format
        """
        dates = []
        
        if not os.path.exists(self.feeds_dir):
            return []

        for filename in os.listdir(self.feeds_dir):
            if filename.endswith('.json'):
                date_str = filename[:-5]  # Remove '.json'
                try:
                    datetime.strptime(date_str, '%Y-%m-%d')
                    dates.append(date_str)
                except ValueError:
                        # Skip invalid date formats
                        continue
                        
        except OSError as e:
            logger.error(f"Error listing files in {self.feeds_dir}: {e}")
        
        return sorted(dates)
    
    def cleanup_old_files(self, days_to_keep: int = 30) -> int:
        """
        Remove files older than specified number of days.
        
        Args:
            days_to_keep: Number of days to keep files for
            
        Returns:
            Number of files removed
        """
        if not os.path.exists(self.feeds_dir):
            logger.warning(f"Feeds directory not found for cleanup: {self.feeds_dir}")
            return 0

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        removed_count = 0
        
        try:
            for filename in os.listdir(self.feeds_dir):
                # Only process date-based files
                if not (filename.endswith('.json') or filename.endswith('.jsonl')):
                    continue

                date_str = filename.split('.')[0] # Extract date part before extension

                try:
                    file_date = datetime.strptime(date_str, '%Y-%m-%d')

                    if file_date < cutoff_date:
                        file_path = os.path.join(self.feeds_dir, filename)
                        os.remove(file_path)
                        removed_count += 1
                        logger.debug(f"Removed old file: {filename}")

                except ValueError:
                    # Ignore files that don't match the YYYY-MM-DD format
                    continue
                        
        except OSError as e:
            logger.error(f"Error accessing directory {self.feeds_dir}: {e}")
        
        logger.info(f"Cleanup completed: removed {removed_count} old files")
        return removed_count