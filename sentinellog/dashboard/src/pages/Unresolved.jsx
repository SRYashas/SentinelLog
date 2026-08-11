import React, { useEffect, useState } from 'react';
import { fetchUnresolvedOrigins } from '../api';
import EventRow from '../components/EventRow';
import { HelpCircle, RefreshCw, ChevronLeft, ChevronRight, AlertCircle } from 'lucide-react';

export default function Unresolved() {
  const [events, setEvents] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, limit: 50, total: 0, pages: 1 });
  const [loading, setLoading] = useState(true);

  const loadData = async (page = pagination.page) => {
    try {
      setLoading(true);
      const data = await fetchUnresolvedOrigins({ page });
      setEvents(data.events || []);
      setPagination(data.pagination || { page: 1, limit: 50, total: 0, pages: 1 });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(pagination.page);
  }, [pagination.page]);

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight flex items-center gap-2">
            <HelpCircle className="w-6 h-6 text-rose-400" />
            Unknown / Unexplained Origins
          </h1>
          <p className="text-sm text-slate-400">
            Process creation events where registry, startup folders, scheduled tasks, and service checks could not explain the trigger.
          </p>
        </div>

        <button
          onClick={() => loadData()}
          className="flex items-center gap-2 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg text-xs font-medium text-slate-300 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Explanatory callout alert */}
      <div className="bg-rose-950/40 border border-rose-800/60 p-4 rounded-xl text-rose-200 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <p className="font-semibold text-sm text-rose-300">Why these popups matter:</p>
          <p>
            When a console or process opens on Windows without a matching Registry Run key, Startup folder item, Scheduled Task, or Service definition, it indicates a background trigger or unexpected spawn mechanism. These are the primary targets to audit for unexplained popup windows.
          </p>
        </div>
      </div>

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
                    {loading ? 'Analyzing system log origins...' : 'No unexplained process creation events found!'}
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
            <span className="font-semibold text-slate-200">{pagination.total}</span> unexplained events
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
