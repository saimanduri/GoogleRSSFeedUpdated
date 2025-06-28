"""
RSS Parser module for processing RSS feeds.
Extracts essential information from feed XML into structured format.
"""
import logging
import feedparser
from typing import Dict, List, Any, Optional
from src.utils.helpers import normalize_date, clean_text, create_article_hash
import datetime # Keep for _get_iso_timestamp for now

logger = logging.getLogger(__name__)

class RSSParser:
    """
    Parses RSS feeds and extracts relevant information.
    """
    
    def __init__(self):
        """Initialize the RSS parser."""
        logger.debug("RSSParser initialized")
    
    def parse_rss(self, rss_content: str, query: str) -> Dict[str, Any]:
        """
        Parse RSS content into structured format.
        
        Args:
            rss_content: Raw RSS XML content
            query: Original query keyword used for this feed
            
        Returns:
            Dictionary with feed metadata and articles
        """
        logger.info(f"Parsing RSS feed for query: {query}")
        
        # Parse the feed
        feed = feedparser.parse(rss_content)
        
        if not feed or not feed.entries:
            logger.warning(f"No entries found in feed for query: {query}")
            return {
                "fetched_at": self._get_iso_timestamp(),
                "query": query,
                "source_url": "",
                "articles": []
            }
        
        # Extract feed URL
        source_url = feed.feed.get('link', '')
        
        # Extract articles
        articles = []
        for entry in feed.entries:
            try:
                article = self._extract_article_data(entry)
                if article and self._is_valid_article(article):
                    articles.append(article)
            except Exception as e:
                logger.exception(f"Error extracting article data: {e}")
        
        # Return structured data
        result = {
            "fetched_at": self._get_iso_timestamp(),
            "query": query,
            "source_url": source_url,
            "articles": articles
        }
        
        logger.info(f"Extracted {len(articles)} valid articles from feed")
        return result
    
    def _extract_article_data(self, entry) -> Dict[str, str]:
        """
        Extract relevant data from a feed entry.
        
        Args:
            entry: Feed entry from feedparser
            
        Returns:
            Dictionary with article data
        """
        # Extract and clean title
        title = entry.get('title', '').strip()
        
        # Extract link
        link = entry.get('link', '').strip()
        
        # Extract publication date
        published = ''
        if hasattr(entry, 'published'):
            published = entry.published
        elif hasattr(entry, 'pubDate'):
            published = entry.pubDate
        elif hasattr(entry, 'updated'):
            published = entry.updated
        
        # Extract source
        source = ''
        if hasattr(entry, 'source'):
            if hasattr(entry.source, 'title'):
                source = entry.source.title
            elif isinstance(entry.source, str):
                source = entry.source
        
        # Try to extract source from tags if not found
        if not source and hasattr(entry, 'tags'):
            for tag in entry.tags:
                if hasattr(tag, 'term') and 'source' in tag.term.lower():
                    source = tag.term
                    break
        
        # Extract description/snippet
        snippet = ''
        if hasattr(entry, 'summary'):
            snippet = entry.summary
        elif hasattr(entry, 'description'):
            snippet = entry.description
        elif hasattr(entry, 'content'):
            if isinstance(entry.content, list) and entry.content:
                snippet = entry.content[0].get('value', '')
            else:
                snippet = str(entry.content)
        
        # Clean and truncate snippet
        snippet = clean_text(snippet, max_length=300)
        
        # Generate hash ID using title and published date
        id_hash = ''
        id_hash = create_article_hash(title, published)
        
        # Normalize date
        published = normalize_date(published)
        
        # Return structured article data
        return {
            "title": title,
            "link": link,
            "published": published,
            "source": source,
            "snippet": snippet,
            "id_hash": id_hash # id_hash is always generated now
        }
    
    def _is_valid_article(self, article: Dict[str, str]) -> bool:
        """
        Validate if an article contains minimum required information.
        
        Args:
            article: Article dictionary
            
        Returns:
            True if article is valid, False otherwise
        """
        # Must have title
        if not article.get('title', '').strip():
            return False
        
        # Must have either link or id_hash for deduplication
        if not article.get('link', '').strip() and not article.get('id_hash', '').strip():
            return False
        
        # Title should be reasonable length (not just a few characters)
        title = article.get('title', '').strip()
        if len(title) < 10:
            logger.debug(f"Skipping article with short title: {title}")
            return False
        
        return True
    
    def _get_iso_timestamp(self) -> str:
        """
        Get current timestamp in ISO format.
        
        Returns:
            ISO formatted timestamp
        """
        return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
