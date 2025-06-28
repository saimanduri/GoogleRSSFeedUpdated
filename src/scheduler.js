import cron from 'node-cron';
import { setupLogging } from './utils/logging_utils.js';

export class Scheduler {
    constructor() {
        this.logger = setupLogging();
        this.task = null;
        this.isRunning = false;
    }

    async start(callback, schedule = '0 */6 * * *') {
        if (this.isRunning) {
            this.logger.warn('Scheduler is already running');
            return;
        }

        this.logger.info(`Starting scheduler with cron pattern: ${schedule}`);

        try {
            this.task = cron.schedule(schedule, async () => {
                this.logger.info('Scheduled task triggered');
                try {
                    await callback();
                } catch (error) {
                    this.logger.error('Scheduled task failed:', error);
                }
            }, {
                scheduled: false
            });

            this.task.start();
            this.isRunning = true;
            
            this.logger.info('Scheduler started successfully');
            
            // Keep the process running
            process.on('SIGINT', () => {
                this.stop();
                process.exit(0);
            });

            // Run initial collection
            this.logger.info('Running initial collection...');
            await callback();

        } catch (error) {
            this.logger.error('Failed to start scheduler:', error);
            throw error;
        }
    }

    stop() {
        if (this.task) {
            this.task.stop();
            this.isRunning = false;
            this.logger.info('Scheduler stopped');
        }
    }

    getStatus() {
        return {
            isRunning: this.isRunning,
            nextRun: this.task ? this.task.nextDate() : null
        };
    }
}