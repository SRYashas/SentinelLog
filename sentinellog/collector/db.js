/**
 * SentinelLog — Database Connection & Models
 * ============================================
 * Mongoose connection to local MongoDB and schema definitions.
 * Database: sentinellog (mongodb://127.0.0.1:27017/sentinellog)
 *
 * Two collections:
 *   - events: Normalized process/script events with origin + risk enrichment
 *   - states: Tracks collector state (last-polled timestamps for gap resilience)
 */

const mongoose = require('mongoose');

// ── MongoDB Connection ─────────────────────────────────────────────────────

const { startLocalMongoIfNeeded } = require('./start-mongo');

const MONGO_URI = 'mongodb://127.0.0.1:27017/sentinellog';

async function connectDB() {
  try {
    await startLocalMongoIfNeeded();
    await mongoose.connect(MONGO_URI);
    console.log('[DB] Connected to MongoDB at', MONGO_URI);
  } catch (err) {
    console.error('[DB] Failed to connect to MongoDB:', err.message);
    console.error('[DB] Make sure MongoDB is running locally on port 27017.');
    process.exit(1);
  }
}

// ── Event Schema ───────────────────────────────────────────────────────────

const eventSchema = new mongoose.Schema({
  timestamp: {
    type: Date,
    required: true,
    index: true
  },
  eventType: {
    type: String,
    enum: ['process_create', 'script_block', 'module_log'],
    required: true,
    index: true
  },
  processName: {
    type: String,
    default: '',
    index: true
  },
  commandLine: {
    type: String,
    default: ''
  },
  pid: {
    type: Number,
    default: 0
  },
  parentProcessName: {
    type: String,
    default: ''
  },
  parentCommandLine: {
    type: String,
    default: ''
  },
  parentPid: {
    type: Number,
    default: 0
  },
  user: {
    type: String,
    default: ''
  },
  origin: {
    resolved: { type: Boolean, default: false },
    source: {
      type: String,
      enum: ['registry_run', 'startup_folder', 'scheduled_task', 'service', 'user_interactive', 'unknown'],
      default: 'unknown'
    },
    detail: { type: String, default: '' }
  },
  riskLevel: {
    type: String,
    enum: ['info', 'suspicious', 'high'],
    default: 'info',
    index: true
  },
  riskReasons: {
    type: [String],
    default: []
  },
  scriptBlockText: {
    type: String,
    default: ''
  },
  hash: {
    sha256: { type: String, default: '' }
  },
  // Raw event ID from Windows Event Log for reference
  eventRecordId: {
    type: String,
    default: ''
  }
}, {
  timestamps: false, // We use our own timestamp field
  collection: 'events'
});

// Compound index for common dashboard queries
eventSchema.index({ timestamp: -1, riskLevel: 1 });
eventSchema.index({ 'origin.resolved': 1, timestamp: -1 });

const Event = mongoose.model('Event', eventSchema);

// ── State Schema (for gap resilience) ──────────────────────────────────────
// Tracks the last-polled timestamp per event log channel so the collector
// can resume from where it left off after a restart.

const stateSchema = new mongoose.Schema({
  key: { type: String, required: true, unique: true },
  value: { type: String, required: true },
  updatedAt: { type: Date, default: Date.now }
}, {
  collection: 'state'
});

const State = mongoose.model('State', stateSchema);

/**
 * Get the last-polled timestamp for a given channel key.
 * Returns null if no state exists (first run).
 */
async function getLastTimestamp(channelKey) {
  const state = await State.findOne({ key: channelKey });
  return state ? state.value : null;
}

/**
 * Update the last-polled timestamp for a given channel key.
 */
async function setLastTimestamp(channelKey, isoTimestamp) {
  await State.findOneAndUpdate(
    { key: channelKey },
    { key: channelKey, value: isoTimestamp, updatedAt: new Date() },
    { upsert: true }
  );
}

module.exports = {
  connectDB,
  Event,
  State,
  getLastTimestamp,
  setLastTimestamp
};
