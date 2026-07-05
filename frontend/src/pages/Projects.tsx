import { FolderGit2 } from 'lucide-react';

export default function Projects() {
  return (
    <div className="space-y-6">
      <div className="border-b border-[#24304f] pb-4">
        <h2 className="text-3xl font-extrabold tracking-tight">Project Repositories</h2>
        <p className="text-slate-400 mt-1">Configure and target workspaces for agent actions.</p>
      </div>

      <div className="bg-brand-panel border border-[#24304f] rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-4 border-b border-[#24304f] pb-4">
          <FolderGit2 className="h-8 w-8 text-accent-primary" />
          <div>
            <h3 className="font-semibold text-lg">CodeForge Local Workspace</h3>
            <p className="text-sm text-slate-500 font-mono">./workspace</p>
          </div>
        </div>
        <p className="text-sm text-slate-400 leading-relaxed">
          The agent currently targets changes exclusively within the workspace subfolder to maintain security and scoping bounds. Future phases will support branch checkouts, remote repositories clones, and multiple workspace bindings.
        </p>
      </div>
    </div>
  );
}
