import fs from 'fs-extra';
import path from 'path';

class Logger {
    constructor() {
        this.logsDir = 'logs';
        this.ensureLogsDir();
    }

    async ensureLogsDir() {
        try {
            await fs.ensureDir(this.logsDir);
        } catch (error) {
            console.error('Failed to create logs directory:', error);
        }
    }

    formatMessage(level, message, error = null) {
        const timestamp = new Date().toISOString();
        let logMessage = `[${timestamp}] ${level.toUpperCase()}: ${message}`;
        
        if (error) {
            logMessage += `\nError: ${error.message}`;
            if (error.stack) {
                logMessage += `\nStack: ${error.stack}`;
            }
        }
        
        return logMessage;
    }

    async writeToFile(message) {
        try {
            const logFile = path.join(this.logsDir, `rss-pipeline-${new Date().toISOString().split('T')[0]}.log`);
            await fs.appendFile(logFile, message + '\n');
        } catch (error) {
            console.error('Failed to write to log file:', error);
        }
    }

    info(message) {
        const logMessage = this.formatMessage('info', message);
        console.log(logMessage);
        this.writeToFile(logMessage);
    }

    error(message, error = null) {
        const logMessage = this.formatMessage('error', message, error);
        console.error(logMessage);
        this.writeToFile(logMessage);
    }

    warn(message) {
        const logMessage = this.formatMessage('warn', message);
        console.warn(logMessage);
        this.writeToFile(logMessage);
    }

    debug(message) {
        const logMessage = this.formatMessage('debug', message);
        console.debug(logMessage);
        this.writeToFile(logMessage);
    }
}

let loggerInstance = null;

export function setupLogging() {
    if (!loggerInstance) {
        loggerInstance = new Logger();
    }
    return loggerInstance;
}