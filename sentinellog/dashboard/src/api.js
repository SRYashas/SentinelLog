/**
 * SentinelLog API Client
 * Centralized fetch functions connecting to local Express backend at http://127.0.0.1:3000/api
 */

const API_BASE = '/api';

/**
 * Fetch paginated event listing
 */
export async function fetchEvents(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, val);
    }
  });

  const res = await fetch(`${API_BASE}/events?${query.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch events: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Fetch single event details by ID
 */
export async function fetchEventById(id) {
  const res = await fetch(`${API_BASE}/events/${id}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch event detail: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Fetch events with unresolved/unknown origin
 */
export async function fetchUnresolvedOrigins(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, val);
    }
  });

  const res = await fetch(`${API_BASE}/origins/unresolved?${query.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch unresolved origins: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Fetch summary statistics for the dashboard
 */
export async function fetchStatsSummary() {
  const res = await fetch(`${API_BASE}/stats/summary`);
  if (!res.ok) {
    throw new Error(`Failed to fetch stats summary: ${res.statusText}`);
  }
  return res.json();
}
