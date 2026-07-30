import React, { useState } from 'react';
import Editor from '@monaco-editor/react';
import { Copy, Check } from 'lucide-react';
import { useApp } from '../../context/AppContext';

// Requested explanation depth options, shown as a segmented control.
const COMPLEXITY_OPTIONS = [
  { id: 'high_level', label: 'High-level', hint: 'Short & big-picture' },
  { id: 'balanced', label: 'Balanced', hint: 'Recommended' },
  { id: 'detailed', label: 'Detailed', hint: 'Deep & thorough' },
];

const CodeInputState = ({ code, setCode, error, onGenerate }) => {
  const { profile, complexity, setComplexity } = useApp();
  const firstName = (profile.name || '').trim().split(' ')[0] || 'there';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 w-full flex flex-col h-full relative">
      {/* Top header: greeting + explanation-depth selector */}
      <div className="flex justify-between items-end mb-4 sm:mb-6 shrink-0 relative z-10">
        <div>
          <p className="text-gray-400 text-sm sm:text-lg font-medium">Hi {firstName}!</p>
          <h1 className="text-3xl sm:text-5xl font-bold mt-1 text-white tracking-tight">
            Paste your code here
          </h1>
        </div>
        
        <div className="flex flex-col items-end gap-2">
          {error && (
            <div className="bg-red-500/10 flex items-center px-3 py-1 sm:px-4 sm:py-1.5 rounded-md border border-red-500/30 shadow-inner">
              <span className="text-[10px] sm:text-xs text-red-400 font-medium select-none">
                Something went wrong — please try again
              </span>
            </div>
          )}

          {/* Explanation-depth selector (drives the generation prompt) */}
          <div className="flex flex-col items-end gap-1">
            <span className="text-[10px] sm:text-xs text-gray-500 font-medium uppercase tracking-wider">
              Explanation depth
            </span>
            <div className="flex bg-[#1e1e1e] rounded-xl border border-white/10 p-1">
              {COMPLEXITY_OPTIONS.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => setComplexity(opt.id)}
                  title={opt.hint}
                  className={`px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                    complexity === opt.id
                      ? 'bg-gradient-to-r from-[#8b5cf6] to-[#7c3aed] text-white shadow'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Code editor panel — z-10 so it sits above the mascot behind it */}
      <div className="relative rounded-2xl sm:rounded-3xl overflow-hidden border border-white/10 shadow-2xl bg-[#1e1e1e] p-1 flex-1 min-h-[350px] z-10">
        <button
          className={`absolute top-4 right-4 sm:top-6 sm:right-6 z-20 p-2 rounded-lg border backdrop-blur-sm transition-all ${
            copied
              ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400'
              : 'bg-[#2a2a2a]/80 hover:bg-[#3a3a3a] border-white/5 text-gray-400'
          }`}
          onClick={handleCopy}
        >
          {copied ? <Check size={18} /> : <Copy size={18} />}
        </button>

        <Editor
          height="calc(100vh - 320px)" 
          defaultLanguage="python"
          theme="vs-dark"
          value={code}
          onChange={(value) => setCode(value)}
          options={{
            fontSize: 14,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            padding: { top: 20, bottom: 100 },
            domReadOnly: false,
            automaticLayout: true,
          }}
        />

        <div className="absolute bottom-6 right-6 sm:bottom-8 sm:right-8 z-20">
          <button 
            onClick={onGenerate}
            className="bg-gradient-to-r from-[#EA6F22] to-[#d35f1c] hover:brightness-125 text-white px-8 py-3 sm:px-12 sm:py-4 rounded-xl sm:rounded-2xl font-bold text-base sm:text-xl transition-all shadow-[0_10px_50px_-10px_rgba(234,111,34,0.7)] active:scale-95"
          >
            Generate Video
          </button>
        </div>

        <div className="absolute bottom-0 left-0 right-0 h-24 sm:h-32 bg-gradient-to-t from-[#1e1e1e] to-transparent pointer-events-none z-10 opacity-70"></div>
      </div>
      {/* Mascot moved to MainLayout so it stays visible during generation. */}
    </div>
  );
};

export default CodeInputState;