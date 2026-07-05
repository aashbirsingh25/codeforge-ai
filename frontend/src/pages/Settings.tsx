import { useState } from 'react';
import { Settings as SettingsIcon } from 'lucide-react';

export default function Settings() {
  const [provider, setProvider] = useState('gemini');
  const [model, setModel] = useState('gemini-1.5-pro');
  const [apiKey, setApiKey] = useState('');

  return (
    <div className="space-y-6">
      <div className="border-b border-[#24304f] pb-4">
        <h2 className="text-3xl font-extrabold tracking-tight">System Settings</h2>
        <p className="text-slate-400 mt-1">Manage global system settings and model credentials.</p>
      </div>

      <div className="bg-brand-panel border border-[#24304f] p-6 rounded-xl max-w-2xl space-y-6">
        <div className="flex items-center gap-3 border-b border-[#24304f] pb-4">
          <SettingsIcon className="h-6 w-6 text-accent-primary" />
          <h3 className="font-semibold text-lg">Model & Provider Configuration</h3>
        </div>

        <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300 block">LLM Provider</label>
            <select 
              value={provider} 
              onChange={(e) => setProvider(e.target.value)}
              className="w-full bg-brand-bg border border-[#24304f] rounded-lg p-2.5 text-slate-100 font-sans text-sm outline-none focus:border-accent-primary"
            >
              <option value="gemini">Gemini (Google)</option>
              <option value="openai">OpenAI</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300 block">Model Name</label>
            <input 
              type="text" 
              value={model} 
              onChange={(e) => setModel(e.target.value)}
              className="w-full bg-brand-bg border border-[#24304f] rounded-lg p-2.5 text-slate-100 font-mono text-sm outline-none focus:border-accent-primary"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300 block">API Key</label>
            <input 
              type="password" 
              value={apiKey} 
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter provider API Key"
              className="w-full bg-brand-bg border border-[#24304f] rounded-lg p-2.5 text-slate-100 font-mono text-sm outline-none focus:border-accent-primary"
            />
          </div>

          <button 
            type="submit" 
            className="bg-gradient-to-r from-accent-primary to-accent-secondary text-brand-bg font-semibold px-5 py-2.5 rounded-lg text-sm transition-transform duration-200 active:scale-95 hover:shadow-[0_0_15px_rgba(0,242,254,0.3)]"
          >
            Save Configurations
          </button>
        </form>
      </div>
    </div>
  );
}
