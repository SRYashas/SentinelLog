import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Activity, HelpCircle, ShieldAlert, Cpu, ShieldCheck, WifiOff } from 'lucide-react';

export default function Sidebar() {
  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/timeline', label: 'Live Timeline', icon: Activity },
    { to: '/unresolved', label: 'Unknown Origins', icon: HelpCircle, badge: 'Key Flag' },
    { to: '/suspicious', label: 'Suspicious Activity', icon: ShieldAlert },
    { to: '/processes', label: 'Process Explorer', icon: Cpu }
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col h-screen sticky top-0 shrink-0 select-none">
      {/* Header */}
      <div className="p-5 border-b border-slate-800 flex items-center gap-3">
        <div className="p-2 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 shadow-lg shadow-cyan-900/30 text-white">
          <ShieldCheck className="w-6 h-6" />
        </div>
        <div>
          <h1 className="font-bold text-slate-100 text-lg tracking-tight leading-none">SentinelLog</h1>
          <span className="text-[10px] text-cyan-400 font-semibold tracking-wider uppercase">Process Monitor</span>
        </div>
      </div>

      {/* Nav Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        <div className="px-3 py-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
          Monitoring
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`
              }
            >
              <div className="flex items-center gap-3">
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-rose-950/80 text-rose-300 border border-rose-800/50 rounded">
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer Offline Notice */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/50">
        <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-900/90 p-2.5 rounded-lg border border-slate-800">
          <WifiOff className="w-4 h-4 text-emerald-400 shrink-0" />
          <div>
            <p className="font-semibold text-slate-300 leading-none mb-0.5">Localhost Only</p>
            <p className="text-[10px] text-slate-500 leading-tight">Zero Network Calls • 100% Offline</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
