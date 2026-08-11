import React from 'react';
import { Search, Filter, X } from 'lucide-react';

export default function SearchFilter({ filters, onChange, onReset }) {
  const handleInputChange = (field, value) => {
    onChange({ ...filters, [field]: value, page: 1 });
  };

  const hasActiveFilters = Boolean(
    filters.search || filters.riskLevel || filters.origin || filters.processName
  );

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 mb-6 backdrop-blur-md shadow-lg">
      <div className="flex flex-wrap items-center gap-3">
        {/* Search input */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search command line / script text..."
            value={filters.search || ''}
            onChange={(e) => handleInputChange('search', e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
          />
        </div>

        {/* Risk Level Filter */}
        <div className="min-w-[140px]">
          <select
            value={filters.riskLevel || ''}
            onChange={(e) => handleInputChange('riskLevel', e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-cyan-500 cursor-pointer"
          >
            <option value="">All Risk Levels</option>
            <option value="high">High Risk Only</option>
            <option value="suspicious">Suspicious Only</option>
            <option value="info">Info Only</option>
            <option value="suspicious,high">Suspicious + High</option>
          </select>
        </div>

        {/* Origin Filter */}
        <div className="min-w-[150px]">
          <select
            value={filters.origin || ''}
            onChange={(e) => handleInputChange('origin', e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-cyan-500 cursor-pointer"
          >
            <option value="">All Origins</option>
            <option value="unknown">Unknown / Unexplained</option>
            <option value="registry_run">Registry Run</option>
            <option value="startup_folder">Startup Folder</option>
            <option value="scheduled_task">Scheduled Task</option>
            <option value="service">Windows Service</option>
            <option value="user_interactive">User Interactive</option>
          </select>
        </div>

        {/* Process Filter */}
        <div className="min-w-[140px]">
          <input
            type="text"
            placeholder="Filter process (e.g. cmd.exe)"
            value={filters.processName || ''}
            onChange={(e) => handleInputChange('processName', e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>

        {/* Clear Filters Button */}
        {hasActiveFilters && (
          <button
            onClick={onReset}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors border border-slate-700"
          >
            <X className="w-4 h-4 text-slate-400" />
            Reset
          </button>
        )}
      </div>
    </div>
  );
}
