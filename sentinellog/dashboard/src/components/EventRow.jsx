import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, ChevronRight, Terminal, ShieldAlert, FileText, ArrowRight } from 'lucide-react';
import RiskBadge from './RiskBadge';
import OriginBadge from './OriginBadge';

export default function EventRow({ event }) {
  const [expanded, setExpanded] = useState(false);

  const formattedTime = new Date(event.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
  const formattedDate = new Date(event.timestamp).toLocaleDateString([], {
    month: 'short',
    day: 'numeric'
  });

  return (
    <>
      <tr
        onClick={() => setExpanded(!expanded)}
        className={`border-b border-slate-800/80 transition-colors cursor-pointer text-sm ${
          expanded ? 'bg-slate-800/40' : 'hover:bg-slate-900/60'
        } ${event.riskLevel === 'high' ? 'bg-red-950/10' : ''}`}
      >
        {/* Expand toggle icon */}
        <td className="py-3 px-3 w-8 text-slate-500 text-center">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </td>

        {/* Timestamp */}
        <td className="py-3 px-3 whitespace-nowrap text-slate-400 font-mono text-xs">
          <div>{formattedTime}</div>
          <div className="text-[10px] text-slate-500">{formattedDate}</div>
        </td>

        {/* Process Name */}
        <td className="py-3 px-3 whitespace-nowrap font-medium text-slate-200">
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-slate-800 text-slate-400 border border-slate-700/50">
              {event.eventType === 'script_block' ? (
                <FileText className="w-3.5 h-3.5 text-cyan-400" />
              ) : (
                <Terminal className="w-3.5 h-3.5 text-slate-300" />
              )}
            </span>
            <span className="font-mono text-xs text-cyan-300">{event.processName || 'N/A'}</span>
            {event.pid > 0 && (
              <span className="text-[10px] text-slate-500 font-mono">PID:{event.pid}</span>
            )}
          </div>
        </td>

        {/* Command Line (Truncated preview) */}
        <td className="py-3 px-3 max-w-md truncate font-mono text-xs text-slate-300">
          {event.eventType === 'script_block' ? (
            <span className="text-slate-400 italic">
              {event.scriptBlockText ? event.scriptBlockText.substring(0, 100) : '[Script block]'}
            </span>
          ) : (
            event.commandLine || <span className="text-slate-600 italic">No command line</span>
          )}
        </td>

        {/* Origin Badge */}
        <td className="py-3 px-3 whitespace-nowrap">
          <OriginBadge origin={event.origin} />
        </td>

        {/* Risk Badge */}
        <td className="py-3 px-3 whitespace-nowrap">
          <RiskBadge level={event.riskLevel} />
        </td>
      </tr>

      {/* Expanded Details Row */}
      {expanded && (
        <tr className="bg-slate-950/90 border-b border-slate-800/80">
          <td colSpan={6} className="p-4 pl-12 text-xs">
            <div className="space-y-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
              {/* Command line full view */}
              <div>
                <span className="font-semibold text-slate-400 block mb-1">Full Command Line:</span>
                <pre className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-slate-200 text-xs overflow-x-auto whitespace-pre-wrap break-all select-all">
                  {event.commandLine || 'N/A'}
                </pre>
              </div>

              {/* Script Block Text if present */}
              {event.scriptBlockText && (
                <div>
                  <span className="font-semibold text-cyan-400 block mb-1">PowerShell Script Block Content:</span>
                  <pre className="bg-slate-950 p-3 rounded-lg border border-cyan-900/40 font-mono text-cyan-200 text-xs overflow-x-auto whitespace-pre-wrap max-h-48 overflow-y-auto">
                    {event.scriptBlockText}
                  </pre>
                </div>
              )}

              {/* Parent Process lineage */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                <div>
                  <span className="font-semibold text-slate-400 block">Parent Process:</span>
                  <p className="font-mono text-slate-300">{event.parentProcessName || 'N/A'} (PID: {event.parentPid || 'N/A'})</p>
                  {event.parentCommandLine && (
                    <p className="font-mono text-slate-500 truncate text-[11px] mt-0.5" title={event.parentCommandLine}>
                      {event.parentCommandLine}
                    </p>
                  )}
                </div>
                <div>
                  <span className="font-semibold text-slate-400 block">User Context:</span>
                  <p className="font-mono text-slate-300">{event.user || 'N/A'}</p>
                </div>
              </div>

              {/* Risk reasons list */}
              {event.riskReasons && event.riskReasons.length > 0 && (
                <div className="pt-2 border-t border-slate-800">
                  <span className="font-semibold text-red-400 flex items-center gap-1.5 mb-1">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    Risk Reasons Matched:
                  </span>
                  <ul className="list-disc list-inside space-y-0.5 text-slate-300">
                    {event.riskReasons.map((reason, idx) => (
                      <li key={idx} className="text-red-300/90">{reason}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Origin detail */}
              {event.origin && event.origin.detail && (
                <div className="pt-2 border-t border-slate-800 text-slate-400">
                  <span className="font-semibold text-slate-300">Origin Resolution Detail: </span>
                  <span>{event.origin.detail}</span>
                </div>
              )}

              {/* Link to detail page */}
              <div className="pt-2 flex justify-end">
                <Link
                  to={`/events/${event._id}`}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-lg text-xs transition-colors"
                >
                  View Full Event Inspection
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
