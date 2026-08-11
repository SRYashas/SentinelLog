/**
 * SentinelLog — Events API Routes
 * ==================================
 * Endpoints for querying and filtering logged events.
 *
 * GET /api/events       — Paginated event list with filtering
 * GET /api/events/:id   — Single event detail
 * GET /api/origins/unresolved — Events with unknown/unresolved origins
 */

const express = require('express');
const router = express.Router();
const Event = require('../models/Event');

// ── GET /api/events ────────────────────────────────────────────────────────
// Paginated event listing with query parameter filtering.
//
// Query params:
//   from        — ISO date, events after this time
//   to          — ISO date, events before this time
//   processName — filter by exact process name
//   eventType   — filter by event type (process_create, script_block, module_log)
//   riskLevel   — filter by risk level (info, suspicious, high)
//   origin      — filter by origin source type
//   search      — regex search on commandLine field
//   page        — page number (default: 1)
//   limit       — items per page (default: 50, max: 200)

router.get('/events', async (req, res) => {
  try {
    const {
      from, to, processName, eventType,
      riskLevel, origin, search,
      page = 1, limit = 50
    } = req.query;

    // Build query filter
    const filter = {};

    // Date range filter
    if (from || to) {
      filter.timestamp = {};
      if (from) filter.timestamp.$gte = new Date(from);
      if (to) filter.timestamp.$lte = new Date(to);
    }

    // Exact match filters
    if (processName) filter.processName = processName.toLowerCase();
    if (eventType) filter.eventType = eventType;
    if (riskLevel) {
      // Support comma-separated values: "suspicious,high"
      const levels = riskLevel.split(',').map(l => l.trim());
      if (levels.length === 1) {
        filter.riskLevel = levels[0];
      } else {
        filter.riskLevel = { $in: levels };
      }
    }
    if (origin) filter['origin.source'] = origin;

    // Full-text search on commandLine (regex, case-insensitive)
    if (search) {
      filter.commandLine = { $regex: escapeRegex(search), $options: 'i' };
    }

    // Pagination
    const pageNum = Math.max(1, parseInt(page, 10) || 1);
    const pageSize = Math.min(200, Math.max(1, parseInt(limit, 10) || 50));
    const skip = (pageNum - 1) * pageSize;

    // Execute query
    const [events, total] = await Promise.all([
      Event.find(filter)
        .sort({ timestamp: -1 })
        .skip(skip)
        .limit(pageSize)
        .lean(),
      Event.countDocuments(filter)
    ]);

    res.json({
      events,
      pagination: {
        page: pageNum,
        limit: pageSize,
        total,
        pages: Math.ceil(total / pageSize)
      }
    });
  } catch (err) {
    console.error('[API] GET /events error:', err.message);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ── GET /api/events/:id ────────────────────────────────────────────────────
// Full event detail including command line, parent chain, script block text.

router.get('/events/:id', async (req, res) => {
  try {
    const event = await Event.findById(req.params.id).lean();
    if (!event) {
      return res.status(404).json({ error: 'Event not found' });
    }
    res.json(event);
  } catch (err) {
    // Handle invalid ObjectId format
    if (err.name === 'CastError') {
      return res.status(400).json({ error: 'Invalid event ID format' });
    }
    console.error('[API] GET /events/:id error:', err.message);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ── GET /api/origins/unresolved ────────────────────────────────────────────
// Dedicated endpoint for events with unresolved origins — the highest-interest
// items ("what just popped up and why don't I know what it was").

router.get('/origins/unresolved', async (req, res) => {
  try {
    const { page = 1, limit = 50, from, to } = req.query;

    const filter = { 'origin.resolved': false };

    if (from || to) {
      filter.timestamp = {};
      if (from) filter.timestamp.$gte = new Date(from);
      if (to) filter.timestamp.$lte = new Date(to);
    }

    const pageNum = Math.max(1, parseInt(page, 10) || 1);
    const pageSize = Math.min(200, Math.max(1, parseInt(limit, 10) || 50));
    const skip = (pageNum - 1) * pageSize;

    const [events, total] = await Promise.all([
      Event.find(filter)
        .sort({ timestamp: -1 })
        .skip(skip)
        .limit(pageSize)
        .lean(),
      Event.countDocuments(filter)
    ]);

    res.json({
      events,
      pagination: {
        page: pageNum,
        limit: pageSize,
        total,
        pages: Math.ceil(total / pageSize)
      }
    });
  } catch (err) {
    console.error('[API] GET /origins/unresolved error:', err.message);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ── Helper ─────────────────────────────────────────────────────────────────

/**
 * Escape special regex characters in a search string.
 */
function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

module.exports = router;
