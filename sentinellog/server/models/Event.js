/**
 * SentinelLog — Event Model (Server)
 * =====================================
 * Mongoose model for the events collection.
 * Schema matches the collector's schema exactly — they share the same database.
 */

const mongoose = require('mongoose');

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
  eventRecordId: {
    type: String,
    default: ''
  }
}, {
  timestamps: false,
  collection: 'events'
});

// Compound indexes for dashboard queries
eventSchema.index({ timestamp: -1, riskLevel: 1 });
eventSchema.index({ 'origin.resolved': 1, timestamp: -1 });

module.exports = mongoose.model('Event', eventSchema);
