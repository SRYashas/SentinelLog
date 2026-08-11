import React from 'react';
import { AlertTriangle, AlertOctagon, Info } from 'lucide-react';

export default function RiskBadge({ level, showIcon = true }) {
  switch (level) {
    case 'high':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-950/80 text-red-400 border border-red-800/50 shadow-sm shadow-red-950">
          {showIcon && <AlertOctagon className="w-3.5 h-3.5 text-red-400 shrink-0" />}
          High Risk
        </span>
      );
    case 'suspicious':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-300 border border-amber-800/50 shadow-sm shadow-amber-950">
          {showIcon && <AlertTriangle className="w-3.5 h-3.5 text-amber-300 shrink-0" />}
          Suspicious
        </span>
      );
    case 'info':
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800/80 text-slate-300 border border-slate-700/50">
          {showIcon && <Info className="w-3.5 h-3.5 text-slate-400 shrink-0" />}
          Info
        </span>
      );
  }
}
