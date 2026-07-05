import { Cpu } from 'lucide-react';

const subAgents = [
  { id: 'planner', name: 'Planner Agent', desc: 'Deconstructs user queries and specifications into detailed checklists and execution trajectories.', color: 'text-accent-primary' },
  { id: 'coding', name: 'Coding Agent', desc: 'Generates scripts, edits files, structures imports, and refactors logic recursively.', color: 'text-accent-green' },
  { id: 'reviewer', name: 'Reviewer Agent', desc: 'Examines code files for syntax correctness, import compliance, and architectural design patterns.', color: 'text-accent-purple' },
  { id: 'debugger', name: 'Debugger Agent', desc: 'Monitors console errors and test suite failures to construct logical corrections iteratively.', color: 'text-accent-red' },
];

export default function Agents() {
  return (
    <div className="space-y-6">
      <div className="border-b border-[#24304f] pb-4">
        <h2 className="text-3xl font-extrabold tracking-tight">Autonomous Agent Registry</h2>
        <p className="text-slate-400 mt-1">Multi-agent orchestrator modules available for execution plans.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {subAgents.map((agent) => (
          <div key={agent.id} className="bg-brand-panel border border-[#24304f] p-6 rounded-xl space-y-3">
            <div className="flex items-center gap-3">
              <Cpu className={`h-6 w-6 ${agent.color}`} />
              <h3 className="font-semibold text-lg">{agent.name}</h3>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed">{agent.desc}</p>
            <div className="pt-2">
              <span className="text-[10px] bg-brand-card text-slate-400 px-2 py-1 rounded border border-[#24304f] uppercase tracking-wider font-mono">
                Subroutine Configured
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
