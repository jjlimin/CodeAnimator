import React from 'react';
import { AlertTriangle, Film, Pencil } from 'lucide-react';
import { useApp } from '../../context/AppContext';

// Shown when the submitted code does not compile. The user chooses between
// getting an explanatory video about the broken code, or going back to edit it.
const CodeErrorChoice = () => {
  const { codeError, generateExplainBug, backToEdit } = useApp();

  return (
    <div className="flex flex-col items-center text-center gap-6 w-full max-w-2xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="text-amber-400">
        <AlertTriangle size={48} />
      </div>

      <div>
        <h2 className="text-4xl font-bold text-white mb-2">Your code has an issue</h2>
        <p className="text-gray-400 text-lg">It doesn't compile, so we can't run it as-is.</p>
      </div>

      <div className="w-full bg-[#1e1e1e] border border-red-500/30 rounded-2xl px-5 py-4 text-left">
        <span className="text-[11px] uppercase tracking-wider text-red-400/80 font-semibold">Error</span>
        <p className="text-red-300 font-mono text-sm mt-1 break-words">{codeError}</p>
      </div>

      <p className="text-gray-400">What would you like to do?</p>

      <div className="flex flex-col sm:flex-row gap-4 w-full">
        <button
          onClick={generateExplainBug}
          className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-[#EA6F22] to-[#d35f1c] hover:brightness-125 text-white px-6 py-4 rounded-2xl font-bold text-lg transition-all shadow-[0_10px_50px_-10px_rgba(234,111,34,0.7)] active:scale-95"
        >
          <Film size={20} /> Explain what's wrong (video)
        </button>
        <button
          onClick={backToEdit}
          className="flex-1 flex items-center justify-center gap-2 bg-[#2a2a2a] hover:bg-[#3a3a3a] text-gray-200 px-6 py-4 rounded-2xl font-bold text-lg transition-all border border-white/10 active:scale-95"
        >
          <Pencil size={20} /> Back to editing
        </button>
      </div>
    </div>
  );
};

export default CodeErrorChoice;
