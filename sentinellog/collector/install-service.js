/**
 * SentinelLog — Windows Service Installer
 * =========================================
 * Uses node-windows to install the collector as a native Windows service
 * named "SentinelLog Collector". The service will:
 *   - Start automatically on system boot
 *   - Restart automatically on failure
 *   - Run under the LocalSystem account
 *
 * Usage: Run as Administrator
 *   node install-service.js
 *
 * After installation, manage via:
 *   services.msc → "SentinelLog Collector"
 *   sc start SentinelLogCollector
 *   sc stop SentinelLogCollector
 */

const path = require('path');
const Service = require('node-windows').Service;

const svc = new Service({
  name: 'SentinelLog Collector',
  description: 'SentinelLog — Offline Windows Process & Console Activity Monitor. Collects Sysmon and PowerShell events, enriches with origin resolution and risk detection, stores in local MongoDB.',
  script: path.join(__dirname, 'index.js'),
  nodeOptions: [],
  // Restart on failure: wait 1 minute, then try again
  wait: 1,
  grow: 0.5,
  maxRestarts: 10
});

svc.on('install', () => {
  console.log('[Service] SentinelLog Collector installed successfully.');
  console.log('[Service] Starting service...');
  svc.start();
});

svc.on('start', () => {
  console.log('[Service] SentinelLog Collector is now running.');
  console.log('[Service] Manage via: services.msc → "SentinelLog Collector"');
});

svc.on('alreadyinstalled', () => {
  console.log('[Service] SentinelLog Collector is already installed.');
  console.log('[Service] To reinstall, run: node uninstall-service.js first.');
});

svc.on('error', (err) => {
  console.error('[Service] Error:', err);
});

console.log('Installing SentinelLog Collector as a Windows service...');
console.log('Script:', path.join(__dirname, 'index.js'));
console.log('');
svc.install();
