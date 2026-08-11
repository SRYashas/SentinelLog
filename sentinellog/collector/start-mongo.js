/**
 * SentinelLog — Local MongoDB Standalone Helper
 * ================================================
 * Checks if a MongoDB server is already listening on mongodb://127.0.0.1:27017.
 * If not, it uses MongoMemoryServer to spin up an in-memory/standalone local MongoDB
 * instance on port 27017 so SentinelLog works out-of-the-box!
 */

const net = require('net');
const { MongoMemoryServer } = require('mongodb-memory-server');

function isPortOpen(port, host = '127.0.0.1') {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(1000);
    socket.on('connect', () => {
      socket.destroy();
      resolve(true); // Port is in use / Mongo is listening
    });
    socket.on('timeout', () => {
      socket.destroy();
      resolve(false);
    });
    socket.on('error', () => {
      socket.destroy();
      resolve(false);
    });
    socket.connect(port, host);
  });
}

async function startLocalMongoIfNeeded() {
  const isOpen = await isPortOpen(27017);
  if (isOpen) {
    console.log('[MongoHelper] Existing MongoDB detected on 127.0.0.1:27017.');
    return null;
  }

  console.log('[MongoHelper] No local MongoDB found on port 27017.');
  console.log('[MongoHelper] Launching embedded local MongoDB server on 127.0.0.1:27017...');

  const mongoServer = await MongoMemoryServer.create({
    instance: {
      port: 27017,
      ip: '127.0.0.1',
      dbName: 'sentinellog'
    }
  });

  console.log('[MongoHelper] Embedded MongoDB server running at mongodb://127.0.0.1:27017/sentinellog');
  return mongoServer;
}

if (require.main === module) {
  startLocalMongoIfNeeded().then(() => {
    console.log('[MongoHelper] MongoDB environment ready.');
  }).catch(err => {
    console.error('[MongoHelper] Failed to start local Mongo:', err);
    process.exit(1);
  });
}

module.exports = { startLocalMongoIfNeeded };
