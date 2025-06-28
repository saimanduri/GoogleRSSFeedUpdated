import axios from 'axios';
import { setupLogging } from './utils/logging_utils.js';

export class RSSFetcher {
    constructor() {
        this.logger = setupLogging();
        this.timeout = 30000; // 30 seconds
    }

    async fetchFeed(url) {
        this.logger.info(`Fetching RSS feed from: ${url}`);
        
        try {
            const response = await axios.get(url, {
                timeout: this.timeout,
                headers: {
                    'User-Agent': 'RSS-Pipeline/1.0.0 (Node.js RSS Collector)',
                    'Accept': 'application/rss+xml, application/xml, text/xml'
                }
            });

            if (response.status !== 200) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            this.logger.info(`Successfully fetched RSS feed from: ${url}`);
            return response.data;
        } catch (error) {
            this.logger.error(`Failed to fetch RSS feed from ${url}:`, error.message);
            throw error;
        }
    }
}