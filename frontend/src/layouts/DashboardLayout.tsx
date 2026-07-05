import { Link, Outlet, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  FolderGit2, 
  Cpu, 
  Database, 
  Settings as SettingsIcon,
  Hammer
} from 'lucide-react';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/projects', label: 'Projects', icon: FolderGit2 },
  { path: '/agents', label: 'Agents', icon: Cpu },
  { path: '/memory', label: 'Memory', icon: Database },
  { path: '/settings', label: 'Settings', icon: SettingsIcon },
];

export default function DashboardLayout() {
  const location = useLocation();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-brand-bg text-[#f8fafc]">
      {/* Sidebar navigation */}
      <aside className="w-72 bg-brand-panel border-r border-[#24304f] flex flex-col shrink-0">
        <div className="p-6 border-b border-[#24304f] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Hammer className="h-6 w-6 text-accent-primary" />
            <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
              CodeForge AI
            </h1>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive 
                    ? 'bg-gradient-to-r from-[#00f2fe]/10 to-[#4facfe]/10 text-accent-primary border-l-2 border-accent-primary' 
                    : 'text-slate-400 hover:bg-white/5 hover:text-[#f8fafc]'
                }`}
              >
                <Icon className={`h-5 w-5 ${isActive ? 'text-accent-primary' : 'text-slate-400'}`} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-[#24304f]">
          <div className="flex items-center gap-3 bg-brand-card/50 p-3 rounded-lg border border-[#24304f] text-xs">
            <span className="h-2 w-2 rounded-full bg-accent-green shadow-[0_0_8px_#10b981]" />
            <span className="text-slate-400 font-medium">Core Service Status: Ready</span>
          </div>
        </div>
      </aside>

      {/* Main content frame */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header navbar */}
        <header className="h-16 border-b border-[#24304f] bg-brand-panel flex items-center justify-between px-8">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-slate-400">Environment:</span>
            <span className="text-xs bg-brand-card px-2.5 py-1 rounded-md border border-[#24304f] font-mono text-accent-primary">
              production-foundation-refactor
            </span>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="text-xs text-right">
              <p className="text-slate-300 font-medium">Flagship Autonomous Agent Platform</p>
              <p className="text-slate-500 font-mono text-[10px]">v2.0.0-dev</p>
            </div>
          </div>
        </header>

        {/* Dynamic Route View Page */}
        <main className="flex-1 overflow-y-auto p-8 bg-brand-bg">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
