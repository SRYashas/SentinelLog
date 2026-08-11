/**
 * SentinelLog — Stats API Routes
 * =================================
 * Dashboard statistics and aggregation endpoints.
 *
 * GET /api/stats/summary — Counts by risk level, top processes,
 *                          events-per-hour for last 24h, unresolved count.
 */

const express = require('express');
const router = express.Router();
const Event = require('../models/Event');

// ── GET /api/stats/summary ─────────────────────────────────────────────────
// Returns a comprehensive summary for the dashboard home page:
//   - riskCounts: { info, suspicious, high }
//   - topProcesses: top 10 process names by frequency
//   - eventsPerHour: event counts per hour for the last 24 hours
//   - unresolvedCount: total events with unresolved origin
//   - totalEvents: total event count

router.get('/summary', async (req, res) => {
  try {
    const now = new Date();
    const twentyFourHoursAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);

    // Run all aggregations in parallel for performance
    const [
      riskCounts,
      topProcesses,
      eventsPerHour,
      unresolvedCount,
      totalEvents,
      recentTotal
    ] = await Promise.all([
      // ── Risk level breakdown ──────────────────────────────────────────
      Event.aggregate([
        {
          $group: {
            _id: '$riskLevel',
            count: { $sum: 1 }
          }
        }
      ]),

      // ── Top 10 processes by frequency ─────────────────────────────────
      Event.aggregate([
        {
          $match: { eventType: 'process_create' }
        },
        {
          $group: {
            _id: '$processName',
            count: { $sum: 1 }
          }
        },
        { $sort: { count: -1 } },
        { $limit: 10 },
        {
          $project: {
            _id: 0,
            processName: '$_id',
            count: 1
          }
        }
      ]),

      // ── Events per hour (last 24h) ───────────────────────────────────
      Event.aggregate([
        {
          $match: {
            timestamp: { $gte: twentyFourHoursAgo }
          }
        },
        {
          $group: {
            _id: {
              year: { $year: '$timestamp' },
              month: { $month: '$timestamp' },
              day: { $dayOfMonth: '$timestamp' },
              hour: { $hour: '$timestamp' }
            },
            count: { $sum: 1 }
          }
        },
        { $sort: { '_id.year': 1, '_id.month': 1, '_id.day': 1, '_id.hour': 1 } }
      ]),

      // ── Unresolved origin count ──────────────────────────────────────
      Event.countDocuments({ 'origin.resolved': false }),

      // ── Total events ─────────────────────────────────────────────────
      Event.countDocuments({}),

      // ── Recent total (last 24h) ──────────────────────────────────────
      Event.countDocuments({ timestamp: { $gte: twentyFourHoursAgo } })
    ]);

    // Format risk counts into an object
    const riskCountMap = { info: 0, suspicious: 0, high: 0 };
    for (const item of riskCounts) {
      if (item._id in riskCountMap) {
        riskCountMap[item._id] = item.count;
      }
    }

    // Format events-per-hour into a time series
    // Fill in missing hours with 0 counts
    const hourlyData = [];
    for (let i = 23; i >= 0; i--) {
      const hourDate = new Date(now.getTime() - i * 60 * 60 * 1000);
      const year = hourDate.getUTCFullYear();
      const month = hourDate.getUTCMonth() + 1;
      const day = hourDate.getUTCDate();
      const hour = hourDate.getUTCHours();

      const match = eventsPerHour.find(e =>
        e._id.year === year &&
        e._id.month === month &&
        e._id.day === day &&
        e._id.hour === hour
      );

      hourlyData.push({
        hour: `${String(hour).padStart(2, '0')}:00`,
        timestamp: hourDate.toISOString(),
        count: match ? match.count : 0
      });
    }

    // Top 5 unresolved-origin processes
    let topUnresolved = [];
    if (unresolvedCount > 0) {
      topUnresolved = await Event.aggregate([
        { $match: { 'origin.resolved': false, eventType: 'process_create' } },
        { $group: { _id: '$processName', count: { $sum: 1 } } },
        { $sort: { count: -1 } },
        { $limit: 5 },
        { $project: { _id: 0, processName: '$_id', count: 1 } }
      ]);
    }

    res.json({
      riskCounts: riskCountMap,
      topProcesses,
      eventsPerHour: hourlyData,
      unresolvedCount,
      topUnresolved,
      totalEvents,
      recentTotal
    });
  } catch (err) {
    console.error('[API] GET /stats/summary error:', err.message);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;
