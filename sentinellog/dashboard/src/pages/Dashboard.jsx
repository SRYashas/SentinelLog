import React, { useEffect, useState } from 'react';
import { fetchStatsSummary, fetchEvents } from '../api';
import StatCard from '../components/StatCard';
import EventRow from '../components/EventRow';
import { Activity, ShieldAlert, HelpCircle, Terminal, RefreshCw, AlertOctagon } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [recentEvents, setRecentEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = async () => {
    try {
      setError(null);
      const [summaryData, eventsData] = await Promise.all([
        fetchStatsSummary(),
        fetchEvents({ limit: 10 })
      ]);
      setStats(summaryData);
      setRecentEvents(eventsData.events || []);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // 10s auto-refresh
    return () => clearInterval(interval);
  }, []);

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        <RefreshCw className="w-6 h-6 animate-spin text-cyan-400 mr-2" />
        Loading system activity metrics...
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="bg-red-950/50 border border-red-800 p-6 rounded-xl text-red-300">
        <h3 className="font-semibold text-lg flex items-center gap-2">
          <AlertOctagon className="w-5 h-5" />
          Failed to load summary stats
        </h3>
        <p className="text-sm mt-2">{error}</p>
        <p className="text-xs text-red-400 mt-1">Make sure MongoDB and the SentinelLog server are running on port 3000.</p>
        <button onClick={loadData} className="mt-4 px-4 py-2 bg-red-800 hover:bg-red-700 text-white rounded-lg text-sm">
          Retry
        </button>
      </div>
    );
  }

  const COLORS = ['#38bdf8', '#f59e0b', '#ef4444'];
  const pieData = stats ? [
    { name: 'Info', value: stats.riskCounts.info || 0 },
    { name: 'Suspicious', value: stats.riskCounts.suspicious || 0 },
    { name: 'High Risk', value: stats.riskCounts.high || 0 }
  ] : [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">System Activity Overview</h1>
          <p className="text-sm text-slate-400">Real-time local Windows process creation & PowerShell monitoring</p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg text-xs font-medium text-slate-300 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* Stat Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Events (24h)"
          value={stats?.recentTotal || 0}
          subtitle={`All time: ${stats?.totalEvents || 0}`}
          icon={Activity}
          color="cyan"
        />
        <StatCard
          title="Unknown / Unexplained"
          value={stats?.unresolvedCount || 0}
          subtitle="Trigger origin unresolved"
          icon={HelpCircle}
          color="rose"
        />
        <StatCard
          title="High Risk Events"
          value={stats?.riskCounts?.high || 0}
          subtitle="Severe rule triggers"
          icon={ShieldAlert}
          color="red"
        />
        <StatCard
          title="Suspicious Commands"
          value={stats?.riskCounts?.suspicious || 0}
          subtitle="Potentially anomalous"
          icon={Terminal}
          color="amber"
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Events per hour chart (2/3 width) */}
        <div className="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl">
          <h3 className="text-base font-semibold text-slate-200 mb-4 flex items-center justify-between">
            <span>Event Activity (Last 24 Hours)</span>
            <span className="text-xs font-normal text-slate-500">Hourly events frequency</span>
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={stats?.eventsPerHour || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#38bdf8" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="hour" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#f8fafc' }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Area type="monotone" dataKey="count" stroke="#38bdf8" strokeWidth={2} fillOpacity={1} fill="url(#colorCount)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Risk Level Distribution (1/3 width) */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-200 mb-2">Risk Breakdown</h3>
            <p className="text-xs text-slate-500 mb-4">Distribution across all captured events</p>
            <div className="h-44 w-full flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2 pt-4 border-t border-slate-800 text-center text-xs">
            <div>
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-cyan-400 mr-1"></span>
              <span className="text-slate-400">Info</span>
              <p className="font-semibold text-slate-200 mt-0.5">{stats?.riskCounts?.info || 0}</p>
            </div>
            <div>
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-amber-400 mr-1"></span>
              <span className="text-slate-400">Suspicious</span>
              <p className="font-semibold text-slate-200 mt-0.5">{stats?.riskCounts?.suspicious || 0}</p>
            </div>
            <div>
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500 mr-1"></span>
              <span className="text-slate-400">High</span>
              <p className="font-semibold text-slate-200 mt-0.5">{stats?.riskCounts?.high || 0}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Top Unknown Origin Processes & Recent Events Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Unknown Origin Processes */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl">
          <h3 className="text-base font-semibold text-slate-200 mb-1 flex items-center gap-2">
            <HelpCircle className="w-4 h-4 text-rose-400" />
            Top Unexplained Processes
          </h3>
          <p className="text-xs text-slate-500 mb-4">Processes with no resolved trigger origin</p>

          {stats?.topUnresolved?.length > 0 ? (
            <div className="space-y-3">
              {stats.topUnresolved.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between p-2.5 bg-slate-950/60 rounded-lg border border-slate-800">
                  <span className="font-mono text-xs text-rose-300">{item.processName}</span>
                  <span className="px-2 py-0.5 text-xs font-semibold bg-rose-950 text-rose-300 rounded border border-rose-800/50">
                    {item.count} occurrences
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-slate-500 italic py-8 text-center bg-slate-950/40 rounded-lg border border-slate-800/50">
              No unexplained process popups detected yet!
            </div>
          )}
        </div>

        {/* Live Recent Events Stream */}
        <div className="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl">
          <h3 className="text-base font-semibold text-slate-200 mb-4 flex items-center justify-between">
            <span>Latest Process & Command Log</span>
            <span className="text-xs font-normal text-slate-500">Auto-updates every 10s</span>
          </h3>

          <div className="overflow-x-auto rounded-lg border border-slate-800">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-950 text-slate-400 text-xs uppercase font-semibold border-b border-slate-800">
                  <th className="py-2.5 px-3 w-8"></th>
                  <th className="py-2.5 px-3">Time</th>
                  <th className="py-2.5 px-3">Process</th>
                  <th className="py-2.5 px-3">Command Line</th>
                  <th className="py-2.5 px-3">Origin</th>
                  <th className="py-2.5 px-3">Risk</th>
                </tr>
              </thead>
              <tbody>
                {recentEvents.length > 0 ? (
                  recentEvents.map((evt) => <EventRow key={evt._id} event={evt} />)
                ) : (
                  <tr>
                    <td colSpan={6} className="text-center py-8 text-slate-500 text-xs italic">
                      No events captured yet. Run Sysmon and PowerShell setup scripts to start monitoring.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
