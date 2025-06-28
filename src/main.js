import { program } from 'commander';
import { RSSFetcher } from './rss_fetcher.js';
import { RSSParser } from './rss_parser.js';
import { StorageManager } from './storage_manager.js';
import { ConfigManager } from './config_manager.js';
import { Scheduler } from './scheduler.js';
import { setupLogging } from './utils/logging_utils.js';

class RSSPipeline {
    constructor() {
        this.configManager = new ConfigManager();
        this.fetcher = new RSSFetcher();
        this.parser = new RSSParser();
        this.storage = new StorageManager();
        this.scheduler = new Scheduler();
        this.logger = setupLogging();
    }

    async initialize() {
        try {
            await this.configManager.loadConfig();
            this.logger.info('RSS Pipeline initialized successfully');
        } catch (error) {
            this.logger.error('Failed to initialize RSS Pipeline:', error);
            throw error;
        }
    }

    async runOnce() {
        this.logger.info('Starting RSS collection run...');
        
        try {
            const feeds = await this.configManager.getFeeds();
            
            for (const feed of feeds) {
                this.logger.info(`Processing feed: ${feed.name}`);
                
                try {
                    const rssData = await this.fetcher.fetchFeed(feed.url);
                    const parsedData = await this.parser.parse(rssData);
                    await this.storage.saveArticles(parsedData, feed.name);
                    
                    this.logger.info(`Successfully processed ${parsedData.items.length} articles from ${feed.name}`);
                } catch (error) {
                    this.logger.error(`Failed to process feed ${feed.name}:`, error);
                }
            }
            
            this.logger.info('RSS collection run completed');
        } catch (error) {
            this.logger.error('RSS collection run failed:', error);
            throw error;
        }
    }

    async startScheduler() {
        this.logger.info('Starting RSS Pipeline scheduler...');
        
        try {
            await this.scheduler.start(async () => {
                await this.runOnce();
            });
        } catch (error) {
            this.logger.error('Failed to start scheduler:', error);
            throw error;
        }
    }
}

async function main() {
    program
        .name('rss-pipeline')
        .description('RSS Pipeline for collecting and processing news feeds')
        .version('1.0.0');

    program
        .option('--run-now', 'Run the pipeline once immediately')
        .option('--schedule', 'Start the scheduled pipeline');

    program.parse();

    const options = program.opts();
    const pipeline = new RSSPipeline();

    try {
        await pipeline.initialize();

        if (options.runNow) {
            await pipeline.runOnce();
        } else if (options.schedule) {
            await pipeline.startScheduler();
        } else {
            console.log('Please specify either --run-now or --schedule');
            program.help();
        }
    } catch (error) {
        console.error('Pipeline failed:', error);
        process.exit(1);
    }
}

if (import.meta.url === `file://${process.argv[1]}`) {
    main();
}