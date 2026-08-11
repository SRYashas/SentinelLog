import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchEventById } from '../api';
import RiskBadge from '../components/RiskBadge';
import OriginBadge from '../components/OriginBadge';
import { ArrowLeft, Terminal, ShieldAlert, Copy, Check, FileText, Cpu, User, Clock, Hash } from 'lucide-react';

export default function EventDetail() {
  const { id } = useParams();
  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    async function loadEvent() {
      try {
        setLoading(true);
        const data = await fetchEventById(id);
        setEvent(data);
      } catch (err) {
        console.error(err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadEvent();
  }, [id]);

  const copyCommandLine = () => {
    if (event?.commandLine) {
      navigator.clipboard.writeText(event.commandLine);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        Loading event inspection details...
      </div>
    );
  }

  if (error || !event) {
    return (
      <div className="bg-red-950/40 border border-red-800 p-6 rounded-xl text-red-300">
        <h3 className="font-semibold text-lg">Event Not Found</h3>
        <p className="text-sm mt-1">{error || 'Could not find the requested event log entry.'}</p>
        <Link to="/timeline" className="mt-4 inline-flex items-center gap-2 text-cyan-400 hover:underline text-sm font-medium">
          <ArrowLeft className="w-4 h-4" /> Back to Timeline
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Back button & title */}
      <div className="flex items-center justify-between">
        <Link
          to="/timeline"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg text-xs font-medium text-slate-300 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Timeline
        </Link>

        <div className="flex items-center gap-2">
          <OriginBadge origin={event.origin} />
          <RiskBadge level={event.riskLevel} />
        </div>
      </div>

      {/* Main Event Card Header */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
        <div className="flex items-start justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-slate-800 text-cyan-400 border border-slate-700">
              {event.eventType === 'script_block' ? <FileText className="w-6 h-6" /> : <Terminal className="w-6 h-6" />}
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100 font-mono">{event.processName || 'Unknown Process'}</h1>
              <p className="text-xs text-slate-400">Event Type: <span className="text-slate-200 uppercase font-semibold">{event.eventType}</span></p>
            </div>
          </div>
          <div className="text-right text-xs text-slate-400 font-mono">
            <div className="flex items-center gap-1 text-slate-300 justify-end">
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              {new Date(event.timestamp).toLocaleString()}
            </div>
            {event.pid > 0 && <div className="text-slate-500 mt-1">PID: {event.pid}</div>}
          </div>
        </div>

        {/* Full Command Line Box */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Full Command Line (Unredacted)
            </label>
            <button
              onClick={copyCommandLine}
              className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
          <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-slate-100 text-xs overflow-x-auto whitespace-pre-wrap break-all select-all shadow-inner">
            {event.commandLine || 'N/A'}
          </pre>
        </div>

        {/* Script Block Text if available */}
        {event.scriptBlockText && (
          <div>
            <label className="text-xs font-semibold text-cyan-400 uppercase tracking-wider block mb-1.5">
              PowerShell Script Block Content (Event ID 4104)
            </label>
            <pre className="bg-slate-950 p-4 rounded-xl border border-cyan-900/50 font-mono text-cyan-200 text-xs overflow-x-auto whitespace-pre-wrap max-h-96 overflow-y-auto shadow-inner">
              {event.scriptBlockText}
            </pre>
          </div>
        )}

        {/* Matched Risk Reasons */}
        {event.riskReasons && event.riskReasons.length > 0 && (
          <div className="bg-red-950/30 border border-red-800/60 p-4 rounded-xl">
            <h3 className="text-xs font-bold text-red-400 uppercase tracking-wider flex items-center gap-1.5 mb-2">
              <ShieldAlert className="w-4 h-4" />
              Risk Rules Matched ({event.riskReasons.length}):
            </h3>
            <ul className="list-disc list-inside space-y-1 text-xs text-red-200">
              {event.riskReasons.map((reason, idx) => (
                <li key={idx}>{reason}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Parent Process & System Context Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          {/* Parent Process Information */}
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2 text-xs">
            <h3 className="font-semibold text-slate-300 flex items-center gap-1.5 border-b border-slate-800 pb-2">
              <Cpu className="w-4 h-4 text-slate-400" />
              Parent Process Lineage
            </h3>
            <div>
              <span className="text-slate-500 block">Parent Executable:</span>
              <span className="font-mono text-slate-200 font-semibold">{event.parentProcessName || 'N/A'}</span>
              {event.parentPid > 0 && <span className="text-slate-500 font-mono ml-2">(PID: {event.parentPid})</span>}
            </div>
            {event.parentCommandLine && (
              <div>
                <span className="text-slate-500 block">Parent Command Line:</span>
                <p className="font-mono text-slate-300 break-all text-[11px] bg-slate-900 p-2 rounded border border-slate-800 mt-1">
                  {event.parentCommandLine}
                </p>
              </div>
            )}
          </div>

          {/* User Context & Execution Metadata */}
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2 text-xs">
            <h3 className="font-semibold text-slate-300 flex items-center gap-1.5 border-b border-slate-800 pb-2">
              <User className="w-4 h-4 text-slate-400" />
              User Context & Origin Detail
            </h3>
            <div>
              <span className="text-slate-500 block">User Account:</span>
              <span className="font-mono text-slate-200">{event.user || 'N/A'}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Origin Trigger Source:</span>
              <span className="font-mono text-cyan-300 font-semibold">{event.origin?.source || 'unknown'}</span>
              <p className="text-slate-400 mt-0.5">{event.origin?.detail || 'No trigger rule matched'}</p>
            </div>
            {event.hash?.sha256 && (
              <div className="pt-1">
                <span className="text-slate-500 flex items-center gap-1">
                  <Hash className="w-3 h-3" /> SHA256 Hash:
                </span>
                <span className="font-mono text-[10px] text-slate-400 break-all select-all">{event.hash.sha256}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
