import React from 'react';
import Editor from '@monaco-editor/react';
import { Copy } from 'lucide-react';
import { useApp } from '../../context/AppContext';

const CodeInputState = ({ code, setCode, error, onGenerate }) => {
  const { profile } = useApp();
  const firstName = (profile.name || '').trim().split(' ')[0] || 'there';
  return (
    /* הסרנו את ה-group מהדיב הראשי והעברנו אותו למיכל העורך אם צריך */
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 w-full flex flex-col h-full relative">
      
      {/* כותרות עליונות */}
      <div className="flex justify-between items-end mb-4 sm:mb-6 shrink-0 relative z-10">
        <div>
          <p className="text-gray-400 text-sm sm:text-lg font-medium">Hi {firstName}!</p>
          <h1 className="text-3xl sm:text-5xl font-bold mt-1 text-white tracking-tight">
            Paste your code here
          </h1>
        </div>
        
        {error && (
          <div className="flex flex-col items-end gap-1">
            <div className="bg-red-500/10 flex items-center px-3 py-1 sm:px-4 sm:py-1.5 rounded-md border border-red-500/30 shadow-inner">
              <span className="text-[10px] sm:text-xs text-red-400 font-medium select-none">
                Something went wrong — please try again
              </span>
            </div>
          </div>
        )}
      </div>

      {/* מיכל העורך - כאן הוספנו z-10 כדי שיהיה מעל התמונה */}
      <div className="relative rounded-2xl sm:rounded-3xl overflow-hidden border border-white/10 shadow-2xl bg-[#1e1e1e] p-1 flex-1 min-h-[350px] z-10">
        <button 
          className="absolute top-4 right-4 sm:top-6 sm:right-6 z-20 p-2 bg-[#2a2a2a]/80 hover:bg-[#3a3a3a] rounded-lg text-gray-400 border border-white/5 backdrop-blur-sm transition-all"
          onClick={() => navigator.clipboard.writeText(code)}
        >
          <Copy size={18} />
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
            className="bg-gradient-to-r from-[#6d28d9] to-[#4f46e5] hover:brightness-125 text-white px-8 py-3 sm:px-12 sm:py-4 rounded-xl sm:rounded-2xl font-bold text-base sm:text-xl transition-all shadow-[0_10px_50px_-10px_rgba(109,40,217,0.7)] active:scale-95"
          >
            Generate Video
          </button>
        </div>

        <div className="absolute bottom-0 left-0 right-0 h-24 sm:h-32 bg-gradient-to-t from-[#1e1e1e] to-transparent pointer-events-none z-10 opacity-70"></div>
      </div>

      {/* --- התמונה החדשה: ממוקמת מחוץ למיכל ה-overflow --- */}
      <div 
        className="fixed bottom-[-60px] right-[-60px] z-0 opacity-30 pointer-events-none"
        style={{
          width: '400px', 
          right: '-60px', // הזזה ימינה
          bottom: '-120px', // כאן תשחק עם המספר כדי להוריד/להעלות
        }}
      >
        <img 
          src="/background.svg" 
          alt="Floating decoration" 
          className="w-full h-full object-contain"
        />
      </div>
    </div>
  );
};

export default CodeInputState;