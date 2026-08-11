/**
 * SentinelLog — Express API Server
 * ===================================
 * Main entry point for the backend API.
 *
 * - Binds to 127.0.0.1 ONLY (never 0.0.0.0) — localhost access only
 * - Connects to local MongoDB at mongodb://127.0.0.1:27017/sentinellog
 * - Serves the React dashboard as static files from ../dashboard/dist
 * - Mounts API routes under /api/*
 * - Structured for future auth middleware insertion
 *
 * No external network calls. No CDN dependencies. Fully offline.
 */

const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const path = require('path');

// ── Configuration ──────────────────────────────────────────────────────────

const HOST = '127.0.0.1';  // NEVER change to 0.0.0.0
const PORT = process.env.PORT || 3000;
const MONGO_URI = 'mongodb://127.0.0.1:27017/sentinellog';
const DASHBOARD_DIR = path.join(__dirname, '..', 'dashboard', 'dist');

// ── Express App Setup ──────────────────────────────────────────────────────

const app = express();

// Middleware
app.use(express.json());

// Content-Security-Policy header to satisfy Electron security standards
app.use((req, res, next) => {
  res.setHeader(
    'Content-Security-Policy',
    "default-src 'self' 'unsafe-inline' 'unsafe-eval' http://127.0.0.1:3000 http://localhost:3000; img-src 'self' data:; font-src 'self' data:;"
  );
  next();
});

// CORS — only allow localhost origins (for development with separate dev server)
app.use(cors({
  origin: [
    'http://127.0.0.1:3000',
    'http://localhost:3000',
    'http://127.0.0.1:5173',  // Vite dev server
    'http://localhost:5173'
  ],
  methods: ['GET'],
  credentials: false
}));

// ── Future Auth Middleware Hook ─────────────────────────────────────────────
// To add authentication later, uncomment and implement:
// const authMiddleware = require('./middleware/auth');
// app.use('/api', authMiddleware);

// ── API Routes ─────────────────────────────────────────────────────────────

const eventsRouter = require('./routes/events');
const statsRouter = require('./routes/stats');

app.use('/api', eventsRouter);
app.use('/api/stats', statsRouter);

// ── Health Check ───────────────────────────────────────────────────────────

app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    uptime: process.uptime(),
    mongo: mongoose.connection.readyState === 1 ? 'connected' : 'disconnected',
    timestamp: new Date().toISOString()
  });
});

// ── Serve React Dashboard (Static Files) ───────────────────────────────────

app.use(express.static(DASHBOARD_DIR));

// SPA fallback: serve index.html for any non-API route
// This enables React Router's client-side routing
app.get('*', (req, res) => {
  if (req.path.startsWith('/api')) {
    return res.status(404).json({ error: 'API endpoint not found' });
  }
  res.sendFile(path.join(DASHBOARD_DIR, 'index.html'));
});

// ── Start Server ───────────────────────────────────────────────────────────

async function start() {
  console.log('+--------------------------------------------+');
  console.log('|  SentinelLog API Server                    |');
  console.log('|  Offline Windows Process & Console Monitor |');
  console.log('+--------------------------------------------+');
  console.log('');

  // Connect to MongoDB
  try {
    const { startLocalMongoIfNeeded } = require('../collector/start-mongo');
    await startLocalMongoIfNeeded();
    await mongoose.connect(MONGO_URI);
    console.log(`[Server] Connected to MongoDB at ${MONGO_URI}`);
  } catch (err) {
    console.error('[Server] Failed to connect to MongoDB:', err.message);
    console.error('[Server] Make sure MongoDB is running locally on port 27017.');
    process.exit(1);
  }

  // Start listening — LOCALHOST ONLY
  app.listen(PORT, HOST, () => {
    console.log(`[Server] API listening on http://${HOST}:${PORT}`);
    console.log(`[Server] Dashboard: http://${HOST}:${PORT}`);
    console.log(`[Server] API base:  http://${HOST}:${PORT}/api`);
    console.log('');
    console.log('[Server] Endpoints:');
    console.log('  GET /api/events              — Paginated event listing');
    console.log('  GET /api/events/:id          — Event detail');
    console.log('  GET /api/origins/unresolved   — Unresolved origin events');
    console.log('  GET /api/stats/summary       — Dashboard statistics');
    console.log('  GET /api/health              — Health check');
    console.log('');
  });
}

start().catch(err => {
  console.error('[Server] Fatal error:', err);
  process.exit(1);
});
