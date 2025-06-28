import fs from 'fs-extra';
import path from 'path';

async function setupDirectories() {
    const directories = [
        'feeds',
        'logs',
        'Config',
        'src/utils',
        'tests'
    ];

    console.log('Setting up project directories...');

    for (const dir of directories) {
        try {
            await fs.ensureDir(dir);
            console.log(`✓ Created directory: ${dir}`);
        } catch (error) {
            console.error(`✗ Failed to create directory ${dir}:`, error.message);
        }
    }

    // Create gitkeep files for empty directories
    const gitkeepDirs = ['feeds', 'logs'];
    
    for (const dir of gitkeepDirs) {
        try {
            const gitkeepPath = path.join(dir, '.gitkeep');
            await fs.writeFile(gitkeepPath, '');
            console.log(`✓ Created .gitkeep in: ${dir}`);
        } catch (error) {
            console.error(`✗ Failed to create .gitkeep in ${dir}:`, error.message);
        }
    }

    console.log('Directory setup completed!');
}

setupDirectories().catch(console.error);