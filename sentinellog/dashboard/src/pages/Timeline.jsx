import React, { useEffect, useState } from 'react';
import { fetchEvents } from '../api';
import EventRow from '../components/EventRow';
import SearchFilter from '../components/SearchFilter';
import { Activity, RefreshCw, ChevronLeft, ChevronRight, Pause, Play } from 'lucide-react';

export default function Timeline() {
  const [events, setEvents] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, limit: 50, total: 0, pages: 1 });
  const [filters, setFilters] = useState({});
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [loading, setLoading] = useState(true);

  const loadEvents = async (customFilters = filters, page = pagination.page) => {
    try {
      setLoading(true);
      const data = await fetchEvents({ ...customFilters, page });
      setEvents(data.events || []);
      setPagination(data.pagination || { page: 1, limit: 50, total: 0, pages: 1 });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents(filters, pagination.page);
  }, [filters, pagination.page]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      loadEvents(filters, pagination.page);
    }, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, filters, pagination.page]);

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  const handleResetFilters = () => {
    setFilters({});
    setPagination(prev => ({ ...prev, page: 1 }));
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight flex items-center gap-2">
            <Activity className="w-6 h-6 text-cyan-400" />
            Live Event Timeline
          </h1>
          <p className="text-sm text-slate-400">Reverse-chronological feed of all process creations and console activity</p>
        </div>

        <div className="flex items-center gap-3">
          {/* Auto refresh toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
              autoRefresh
                ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60'
                : 'bg-slate-900 text-slate-400 border-slate-800'
            }`}
          >
            {autoRefresh ? (
              <>
                <Pause className="w-3.5 h-3.5 text-emerald-400" />
                Live Polling On (5s)
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 text-slate-400" />
                Polling Paused
              </>
            )}
          </button>

          <button
            onClick={() => loadEvents()}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg text-xs font-medium text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Global Filter Toolbar */}
      <SearchFilter
        filters={filters}
        onChange={handleFilterChange}
        onReset={handleResetFilters}
      />

      {/* Events Table Container */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl">
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-950 text-slate-400 text-xs uppercase font-semibold border-b border-slate-800">
                <th className="py-3 px-3 w-8"></th>
                <th className="py-3 px-3">Time</th>
                <th className="py-3 px-3">Process</th>
                <th className="py-3 px-3">Command Line</th>
                <th className="py-3 px-3">Origin</th>
                <th className="py-3 px-3">Risk</th>
              </tr>
            </thead>
            <tbody>
              {events.length > 0 ? (
                events.map((evt) => <EventRow key={evt._id} event={evt} />)
              ) : (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-500 text-xs italic">
                    {loading ? 'Fetching matching event log records...' : 'No matching events found.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-800 text-xs text-slate-400">
          <div>
            Showing <span className="font-semibold text-slate-200">{events.length}</span> of{' '}
            <span className="font-semibold text-slate-200">{pagination.total}</span> events
          </div>

          <div className="flex items-center gap-2">
            <button
              disabled={pagination.page <= 1}
              onClick={() => setPagination(prev => ({ ...prev, page: prev.page - 1 }))}
              className="p-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <span>
              Page <span className="font-semibold text-slate-200">{pagination.page}</span> of{' '}
              <span className="font-semibold text-slate-200">{pagination.pages || 1}</span>
            </span>

            <button
              disabled={pagination.page >= pagination.pages}
              onClick={() => setPagination(prev => ({ ...prev, page: prev.page + 1 }))}
              className="p-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
