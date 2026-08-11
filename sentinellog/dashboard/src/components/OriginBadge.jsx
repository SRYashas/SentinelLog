import React from 'react';
import { HelpCircle, Terminal, Cpu, Calendar, Folder, Key } from 'lucide-react';

export default function OriginBadge({ origin }) {
  if (!origin) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-950/70 text-rose-300 border border-rose-800/60 shadow-sm animate-pulse">
        <HelpCircle className="w-3.5 h-3.5" />
        Unknown Origin
      </span>
    );
  }

  const { resolved, source, detail } = origin;

  if (!resolved || source === 'unknown') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-950/70 text-rose-300 border border-rose-800/60 shadow-sm" title={detail || 'Unexplained popup / origin unresolved'}>
        <HelpCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
        Unknown Origin
      </span>
    );
  }

  switch (source) {
    case 'registry_run':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-950/70 text-purple-300 border border-purple-800/50" title={detail}>
          <Key className="w-3.5 h-3.5 text-purple-400 shrink-0" />
          Registry Run
        </span>
      );
    case 'startup_folder':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-950/70 text-blue-300 border border-blue-800/50" title={detail}>
          <Folder className="w-3.5 h-3.5 text-blue-400 shrink-0" />
          Startup Folder
        </span>
      );
    case 'scheduled_task':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950/70 text-emerald-300 border border-emerald-800/50" title={detail}>
          <Calendar className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          Scheduled Task
        </span>
      );
    case 'service':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-cyan-950/70 text-cyan-300 border border-cyan-800/50" title={detail}>
          <Cpu className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          Windows Service
        </span>
      );
    case 'user_interactive':
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800/80 text-slate-300 border border-slate-700/50" title={detail}>
          <Terminal className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          Interactive / Shell
        </span>
      );
  }
}
