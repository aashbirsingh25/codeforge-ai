import { Database } from 'lucide-react';

export default function Memory() {
  return (
    <div className="space-y-6">
      <div className="border-b border-[#24304f] pb-4">
        <h2 className="text-3xl font-extrabold tracking-tight">Agent Memory Manager</h2>
        <p className="text-slate-400 mt-1">Configure vector nodes and prompt context retrieval systems.</p>
      </div>

      <div className="bg-brand-panel border border-[#24304f] rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-3">
          <Database className="h-6 w-6 text-accent-purple" />
          <h3 className="font-semibold text-lg">Vector Store & Short Term Context</h3>
        </div>
        <p className="text-sm text-slate-400 leading-relaxed">
          Memory nodes hold index markers pointing to previous debugging routines, code files templates, and developer execution summaries. Semantic embeddings search triggers will be mounted in Phase 3.
        </p>
        <div className="bg-brand-code border border-[#24304f] p-4 rounded-lg font-mono text-xs text-slate-500">
          // Memory structures await semantic indexing configurations...
        </div>
      </div>
    </div>
  );
}
