import { Terminal, Cpu, FolderGit2, ShieldCheck } from 'lucide-react';

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div className="border-b border-[#24304f] pb-4">
        <h2 className="text-3xl font-extrabold tracking-tight">System Dashboard</h2>
        <p className="text-slate-400 mt-1">Status dashboard for CodeForge AI autonomous activities.</p>
      </div>

      {/* Grid status cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-brand-panel border border-[#24304f] p-6 rounded-xl space-y-3">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Active Task</h3>
            <Terminal className="h-5 w-5 text-accent-primary" />
          </div>
          <p className="text-2xl font-bold font-mono text-accent-primary">IDLE</p>
          <p className="text-xs text-slate-500">Ready to accept engineering task assignments.</p>
        </div>

        <div className="bg-brand-panel border border-[#24304f] p-6 rounded-xl space-y-3">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Agents Registered</h3>
            <Cpu className="h-5 w-5 text-accent-purple" />
          </div>
          <p className="text-2xl font-bold">4 Modules</p>
          <p className="text-xs text-slate-500">Planner, Coding, Reviewer, and Debugger agents.</p>
        </div>

        <div className="bg-brand-panel border border-[#24304f] p-6 rounded-xl space-y-3">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Managed Repos</h3>
            <FolderGit2 className="h-5 w-5 text-accent-green" />
          </div>
          <p className="text-2xl font-bold">1 Active</p>
          <p className="text-xs text-slate-500">Workspace scope resolves directory targets.</p>
        </div>
      </div>

      {/* Overview log container */}
      <div className="bg-brand-panel border border-[#24304f] rounded-xl p-6 space-y-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-accent-green" />
          Infrastructure Verification
        </h3>
        <div className="bg-brand-code border border-[#24304f] rounded-lg p-4 font-mono text-sm text-slate-400 space-y-2">
          <p className="text-accent-green">[OK] FastAPI server mounting routes...</p>
          <p className="text-accent-green">[OK] CORS security headers injected...</p>
          <p className="text-accent-green">[OK] Path traversal checker configured...</p>
          <p className="text-slate-500">// AI processing loop handles unexposed. Ready for Phase 2 integration.</p>
        </div>
      </div>
    </div>
  );
}
