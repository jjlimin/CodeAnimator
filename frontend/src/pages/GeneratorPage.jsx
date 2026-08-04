import React from 'react';
import { useApp } from '../context/AppContext';
import { filterForMascot } from '../mascotColors';
import ProcessingState from '../components/Preview/ProcessingState';
import DoneState from '../components/Preview/DoneState';
import CodeInputState from '../components/Preview/CodeInputState';
import CodeErrorChoice from '../components/Preview/CodeErrorChoice';
import GenFailed from '../components/Preview/GenFailed';

const GeneratorPage = () => {
  const { view, code, setCode, startGenerate, editVideo, cancelJob, videoUrl, currentTitle, renameJob, activeJobId, mascotColor } = useApp();

  return (
    <div className="flex flex-col h-full w-full">
      <header className="flex items-center justify-between mb-8 w-full">
        <div className="flex items-center gap-2">
          <img
            src="/logo.svg"
            alt="Logo"
            className="w-8 h-8 object-contain transition-[filter] duration-300"
            style={{ filter: filterForMascot(mascotColor) }}
          />
          <span className="text-xl font-bold tracking-tight text-white font-sans">CodeAnimator</span>
        </div>
      </header>

      <div className="flex-1 flex flex-col items-center justify-center w-full">
        <div className="w-full max-w-4xl">
          {view === 'idle' && (
            <CodeInputState code={code} setCode={setCode} onGenerate={startGenerate} />
          )}

          {view === 'code_error' && <CodeErrorChoice />}

          {view === 'gen_failed' && <GenFailed />}

          {view === 'processing' && <ProcessingState onCancel={() => cancelJob(activeJobId)} />}

          {view === 'done' && (
            <DoneState
              videoUrl={videoUrl}
              title={currentTitle}
              code={code}
              onRename={(t) => renameJob(activeJobId, t)}
              onEdit={editVideo}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default GeneratorPage;
