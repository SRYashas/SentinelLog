import React, { useEffect, useState } from 'react';
import { fetchEvents } from '../api';
import EventRow from '../components/EventRow';
import { ShieldAlert, RefreshCw, ChevronLeft, ChevronRight, Filter } from 'lucide-react';

export default function Suspicious() {
  const [events, setEvents] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, limit: 50, total: 0, pages: 1 });
  const [riskFilter, setRiskFilter] = useState('suspicious,high');
  const [loading, setLoading] = useState(true);

  const loadData = async (page = pagination.page, level = riskFilter) => {
    try {
      setLoading(true);
      const data = await fetchEvents({ riskLevel: level, page });
      setEvents(data.events || []);
      setPagination(data.pagination || { page: 1, limit: 50, total: 0, pages: 1 });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(pagination.page, riskFilter);
  }, [pagination.page, riskFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-amber-400" />
            Suspicious & High Risk Activity
          </h1>
          <p className="text-sm text-slate-400">
            Commands and scripts matching risk rules engine patterns (encoded commands, LOLBin abuse, web cradles, evasion)
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Quick Risk Selector */}
          <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 p-1 rounded-lg">
            <button
              onClick={() => setRiskFilter('suspicious,high')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                riskFilter === 'suspicious,high'
                  ? 'bg-slate-800 text-slate-100 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All Anomalies
            </button>
            <button
              onClick={() => setRiskFilter('high')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                riskFilter === 'high'
                  ? 'bg-red-950 text-red-300 border border-red-800/60 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              High Risk Only
            </button>
            <button
              onClick={() => setRiskFilter('suspicious')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                riskFilter === 'suspicious'
                  ? 'bg-amber-950 text-amber-300 border border-amber-800/60 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Suspicious Only
            </button>
          </div>

          <button
            onClick={() => loadData()}
            className="flex items-center gap-2 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg text-xs font-medium text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
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
                <th className="py-3 px-3">Risk Level</th>
              </tr>
            </thead>
            <tbody>
              {events.length > 0 ? (
                events.map((evt) => <EventRow key={evt._id} event={evt} />)
              ) : (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-500 text-xs italic">
                    {loading ? 'Evaluating rules engine matches...' : 'No suspicious or high-risk activity detected.'}
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
            <span className="font-semibold text-slate-200">{pagination.total}</span> flagged events
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
