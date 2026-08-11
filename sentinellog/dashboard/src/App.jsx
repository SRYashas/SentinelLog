import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Timeline from './pages/Timeline';
import Unresolved from './pages/Unresolved';
import Suspicious from './pages/Suspicious';
import ProcessExplorer from './pages/ProcessExplorer';
import EventDetail from './pages/EventDetail';

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-slate-950 text-slate-100 font-sans antialiased">
        {/* Left Sidebar */}
        <Sidebar />

        {/* Main Content Area */}
        <main className="flex-1 p-6 md:p-8 overflow-y-auto max-w-7xl">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/timeline" element={<Timeline />} />
            <Route path="/unresolved" element={<Unresolved />} />
            <Route path="/suspicious" element={<Suspicious />} />
            <Route path="/processes" element={<ProcessExplorer />} />
            <Route path="/events/:id" element={<EventDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
