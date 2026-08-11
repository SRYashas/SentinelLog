/**
 * SentinelLog — Windows Service Uninstaller
 * ===========================================
 * Removes the SentinelLog Collector Windows service.
 *
 * Usage: Run as Administrator
 *   node uninstall-service.js
 */

const path = require('path');
const Service = require('node-windows').Service;

const svc = new Service({
  name: 'SentinelLog Collector',
  script: path.join(__dirname, 'index.js')
});

svc.on('uninstall', () => {
  console.log('[Service] SentinelLog Collector has been uninstalled.');
});

svc.on('error', (err) => {
  console.error('[Service] Error:', err);
});

console.log('Uninstalling SentinelLog Collector service...');
svc.uninstall();
