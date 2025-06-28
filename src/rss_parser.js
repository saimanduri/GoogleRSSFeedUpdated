import Parser from 'rss-parser';
import { setupLogging } from './utils/logging_utils.js';

export class RSSParser {
    constructor() {
        this.parser = new Parser({
            customFields: {
                feed: ['language', 'copyright', 'managingEditor'],
                item: ['author', 'category', 'comments', 'enclosure', 'guid', 'source']
            }
        });
        this.logger = setupLogging();
    }

    async parse(rssData) {
        this.logger.info('Parsing RSS data...');
        
        try {
            const feed = await this.parser.parseString(rssData);
            
            const parsedData = {
                title: feed.title,
                description: feed.description,
                link: feed.link,
                language: feed.language,
                lastBuildDate: feed.lastBuildDate,
                items: feed.items.map(item => ({
                    title: item.title,
                    description: item.description || item.summary,
                    link: item.link,
                    pubDate: item.pubDate,
                    author: item.author || item.creator,
                    category: item.category,
                    guid: item.guid,
                    content: item.content || item.contentSnippet
                }))
            };

            this.logger.info(`Successfully parsed RSS feed with ${parsedData.items.length} items`);
            return parsedData;
        } catch (error) {
            this.logger.error('Failed to parse RSS data:', error.message);
            throw error;
        }
    }
}