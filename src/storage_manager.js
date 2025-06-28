import fs from 'fs-extra';
import path from 'path';
import { format } from 'date-fns';
import { setupLogging } from './utils/logging_utils.js';

export class StorageManager {
    constructor() {
        this.logger = setupLogging();
        this.feedsDir = 'feeds';
        this.ensureDirectories();
    }

    async ensureDirectories() {
        try {
            await fs.ensureDir(this.feedsDir);
            await fs.ensureDir('logs');
        } catch (error) {
            this.logger.error('Failed to create directories:', error);
        }
    }

    async saveArticles(feedData, feedName) {
        const timestamp = format(new Date(), 'yyyy-MM-dd_HH-mm-ss');
        const filename = `${feedName}_${timestamp}.json`;
        const filepath = path.join(this.feedsDir, filename);

        try {
            const dataToSave = {
                metadata: {
                    feedName,
                    collectedAt: new Date().toISOString(),
                    title: feedData.title,
                    description: feedData.description,
                    link: feedData.link,
                    itemCount: feedData.items.length
                },
                articles: feedData.items
            };

            await fs.writeJson(filepath, dataToSave, { spaces: 2 });
            this.logger.info(`Saved ${feedData.items.length} articles to ${filepath}`);
            
            return filepath;
        } catch (error) {
            this.logger.error(`Failed to save articles to ${filepath}:`, error);
            throw error;
        }
    }

    async loadArticles(filepath) {
        try {
            const data = await fs.readJson(filepath);
            this.logger.info(`Loaded articles from ${filepath}`);
            return data;
        } catch (error) {
            this.logger.error(`Failed to load articles from ${filepath}:`, error);
            throw error;
        }
    }

    async listSavedFeeds() {
        try {
            const files = await fs.readdir(this.feedsDir);
            return files.filter(file => file.endsWith('.json'));
        } catch (error) {
            this.logger.error('Failed to list saved feeds:', error);
            return [];
        }
    }
}