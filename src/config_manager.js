import fs from 'fs-extra';
import path from 'path';
import { setupLogging } from './utils/logging_utils.js';

export class ConfigManager {
    constructor() {
        this.logger = setupLogging();
        this.configDir = 'Config';
        this.settingsFile = path.join(this.configDir, 'settings.json');
        this.feedsFile = path.join(this.configDir, 'feeds.json');
        this.settings = {};
        this.feeds = [];
    }

    async loadConfig() {
        try {
            await fs.ensureDir(this.configDir);
            
            // Load settings
            if (await fs.pathExists(this.settingsFile)) {
                this.settings = await fs.readJson(this.settingsFile);
            } else {
                await this.createDefaultSettings();
            }

            // Load feeds
            if (await fs.pathExists(this.feedsFile)) {
                this.feeds = await fs.readJson(this.feedsFile);
            } else {
                await this.createDefaultFeeds();
            }

            this.logger.info('Configuration loaded successfully');
        } catch (error) {
            this.logger.error('Failed to load configuration:', error);
            throw error;
        }
    }

    async createDefaultSettings() {
        const defaultSettings = {
            schedule: {
                interval: "0 */6 * * *", // Every 6 hours
                timezone: "UTC"
            },
            storage: {
                maxFiles: 100,
                retentionDays: 30
            },
            fetcher: {
                timeout: 30,
                retries: 3,
                userAgent: "RSS-Pipeline/1.0.0"
            }
        };

        await fs.writeJson(this.settingsFile, defaultSettings, { spaces: 2 });
        this.settings = defaultSettings;
        this.logger.info('Created default settings file');
    }

    async createDefaultFeeds() {
        const defaultFeeds = [
            {
                name: "google-news-general",
                url: "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
                category: "general"
            },
            {
                name: "google-news-technology",
                url: "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZ4ZERBU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
                category: "technology"
            },
            {
                name: "google-news-business",
                url: "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
                category: "business"
            }
        ];

        await fs.writeJson(this.feedsFile, defaultFeeds, { spaces: 2 });
        this.feeds = defaultFeeds;
        this.logger.info('Created default feeds file');
    }

    async getFeeds() {
        return this.feeds;
    }

    async getSettings() {
        return this.settings;
    }

    async updateSettings(newSettings) {
        this.settings = { ...this.settings, ...newSettings };
        await fs.writeJson(this.settingsFile, this.settings, { spaces: 2 });
        this.logger.info('Settings updated');
    }

    async addFeed(feed) {
        this.feeds.push(feed);
        await fs.writeJson(this.feedsFile, this.feeds, { spaces: 2 });
        this.logger.info(`Added new feed: ${feed.name}`);
    }
}