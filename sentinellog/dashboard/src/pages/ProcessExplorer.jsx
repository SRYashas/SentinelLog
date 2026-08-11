import React, { useEffect, useState } from 'react';
import { fetchStatsSummary, fetchEvents } from '../api';
import EventRow from '../components/EventRow';
import { Cpu, RefreshCw, Terminal, GitFork, ArrowRight } from 'lucide-react';

export default function ProcessExplorer() {
  const [topProcesses, setTopProcesses] = useState([]);
  const [selectedProcess, setSelectedProcess] = useState('');
  const [processEvents, setProcessEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadSummary = async () => {
    try {
      setLoading(true);
      const data = await fetchStatsSummary();
      const processes = data.topProcesses || [];
      setTopProcesses(processes);
      if (processes.length > 0 && !selectedProcess) {
        setSelectedProcess(processes[0].processName);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadProcessEvents = async (procName) => {
    if (!procName) return;
    try {
      const data = await fetchEvents({ processName: procName, limit: 30 });
      setProcessEvents(data.events || []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  useEffect(() => {
    if (selectedProcess) {
      loadProcessEvents(selectedProcess);
    }
  }, [selectedProcess]);

  // Extract parent process relations for the process tree view
  const parentTree = processEvents.reduce((acc, evt) => {
    const parent = evt.parentProcessName || 'Unknown Parent';
    if (!acc[parent]) acc[parent] = [];
    acc[parent].push(evt);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight flex items-center gap-2">
            <Cpu className="w-6 h-6 text-cyan-400" />
            Process Explorer & Lineage
          </h1>
          <p className="text-sm text-slate-400">
            Group activity by executable name, inspect spawn frequency, and view parent-child process lineage trees
          </p>
        </div>

        <button
          onClick={loadSummary}
          className="flex items-center gap-2 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg text-xs font-medium text-slate-300 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Top Process List Selector */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl">
          <h3 className="text-base font-semibold text-slate-200 mb-3">Top Executables</h3>
          <p className="text-xs text-slate-500 mb-4">Click to inspect process lineage and execution history</p>

          <div className="space-y-2">
            {topProcesses.map((item) => {
              const isSelected = item.processName === selectedProcess;
              return (
                <button
                  key={item.processName}
                  onClick={() => setSelectedProcess(item.processName)}
                  className={`w-full flex items-center justify-between p-3 rounded-lg border text-left transition-all ${
                    isSelected
                      ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-300 shadow-md'
                      : 'bg-slate-950/60 border-slate-800/80 text-slate-300 hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Terminal className={`w-4 h-4 ${isSelected ? 'text-cyan-400' : 'text-slate-500'}`} />
                    <span className="font-mono text-xs font-medium">{item.processName}</span>
                  </div>
                  <span className="px-2 py-0.5 text-xs font-semibold bg-slate-800 text-slate-300 rounded border border-slate-700">
                    {item.count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Column: Lineage Tree & Events for Selected Process */}
        <div className="lg:col-span-2 space-y-6">
          {/* Parent-Child Lineage Summary Card */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl">
            <h3 className="text-base font-semibold text-slate-200 mb-1 flex items-center gap-2">
              <GitFork className="w-4 h-4 text-cyan-400" />
              Process Lineage Tree: <span className="font-mono text-cyan-300">{selectedProcess}</span>
            </h3>
            <p className="text-xs text-slate-500 mb-4">Spawning parent processes identified for {selectedProcess}</p>

            <div className="space-y-3">
              {Object.keys(parentTree).length > 0 ? (
                Object.entries(parentTree).map(([parentName, instances]) => (
                  <div key={parentName} className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 text-xs">
                    <div className="flex items-center justify-between text-slate-300 font-mono font-semibold mb-2">
                      <span className="flex items-center gap-1.5 text-slate-400">
                        Parent: <span className="text-amber-300">{parentName}</span>
                      </span>
                      <span className="text-slate-500 font-normal">
                        Spawned <span className="text-slate-200 font-bold">{instances.length}</span> times
                      </span>
                    </div>

                    <div className="pl-4 border-l-2 border-slate-800 space-y-1.5">
                      {instances.slice(0, 3).map((inst, i) => (
                        <div key={i} className="flex items-center gap-2 font-mono text-[11px] text-slate-400">
                          <ArrowRight className="w-3 h-3 text-cyan-500 shrink-0" />
                          <span className="text-slate-200 font-semibold">{inst.processName}</span>
                          <span className="text-slate-500 truncate max-w-xs">{inst.commandLine}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-500 italic py-4">No process lineage captured yet for this executable.</p>
              )}
            </div>
          </div>

          {/* Event History Table for Selected Process */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-xl">
            <h3 className="text-base font-semibold text-slate-200 mb-4">
              Execution Log: <span className="font-mono text-cyan-300">{selectedProcess}</span>
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
                  {processEvents.length > 0 ? (
                    processEvents.map((evt) => <EventRow key={evt._id} event={evt} />)
                  ) : (
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-slate-500 text-xs italic">
                        No events logged for {selectedProcess}.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
