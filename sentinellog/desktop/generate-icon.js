/**
 * SentinelLog Tray Icon Generator
 * Generates a native 16x16 PNG tray icon for Electron.
 */

const fs = require('fs');
const path = require('path');

// 16x16 solid cyan security shield icon PNG base64
const base64Png = 'iVBORw0KGgoAAAANSU5EUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAA7SURBVDhPY2AYBaNgFCxYsIBfQEBgAD0xYfT///8ZqGJgAKpmgAOmqRupAZiG0dUDAwPUAgYGBhQFAADqZBAxP3X4HAAAAABJRU5ErkJggg==';

const iconBuffer = Buffer.from(base64Png, 'base64');
const outputPath = path.join(__dirname, 'tray-icon.png');

fs.writeFileSync(outputPath, iconBuffer);
console.log('Generated tray icon at:', outputPath);
