import React from 'react';
import { Search } from 'lucide-react';
import { useApp } from '../context/AppContext';
import ProcessingState from '../components/Preview/ProcessingState';
import DoneState from '../components/Preview/DoneState';
import CodeInputState from '../components/Preview/CodeInputState';

const GeneratorPage = () => {
  const { view, code, setCode, startGenerate, newVideo, videoUrl, currentTitle, renameJob, activeJobId } = useApp();

  return (
    <div className="flex flex-col h-full w-full">
      <header className="flex items-center justify-between mb-8 w-full">
        <div className="flex items-center gap-2">
          <img src="/logo.svg" alt="Logo" className="w-8 h-8 object-contain" />
          <span className="text-xl font-bold tracking-tight text-white font-sans">CodeAnimator</span>
        </div>
        <button className="text-gray-400 hover:text-white transition p-2">
          <Search size={20} />
        </button>
      </header>

      <div className="flex-1 flex flex-col items-center justify-center w-full">
        <div className="w-full max-w-4xl">
          {view === 'idle' && (
            <CodeInputState code={code} setCode={setCode} onGenerate={startGenerate} />
          )}

          {view === 'processing' && <ProcessingState onCancel={newVideo} />}

          {view === 'done' && (
            <DoneState
              videoUrl={videoUrl}
              title={currentTitle}
              code={code}
              onRename={(t) => renameJob(activeJobId, t)}
              onEdit={newVideo}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default GeneratorPage;
