import React, { useState, useEffect } from 'react';
import { XCircle } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { filterForMascot } from '../../mascotColors';
import Flashcard from './Flashcard';

// Small pools of flavor text per real pipeline stage — keeps the fun,
// rotating-message feel without ever claiming a stage we're not actually in
// (that mismatch was the "doesn't feel like real progress" complaint).
const STAGE_MESSAGES = {
  script: [
    'Writing the script...',
    'Teaching the robots to animate 🤖',
    'Sprinkling in a little magic ✨',
  ],
  rendering: [
    'Rendering your scenes 🎬',
    'Making the pixels dance...',
    'Bribing the GPU to hurry up...',
  ],
  finishing: [
    'Stitching the final cut 🎞️',
    'Almost there, hang tight!',
  ],
};

const STAGE_ORDER = ['script', 'rendering', 'finishing'];
const STAGE_LABELS = { script: 'Script', rendering: 'Rendering', finishing: 'Finishing' };

// Rough overall completion for the progress bar. Rendering is the biggest,
// most variable chunk, so it's the only one driven by a real fraction
// (scenes_done/scenes_total from the backend); script/finishing just get a
// fixed head-start/tail so the bar always shows visible motion.
const progressPercent = (stage, scenesDone, scenesTotal) => {
  if (stage === 'rendering') {
    const frac = scenesTotal > 0 ? scenesDone / scenesTotal : 0;
    return Math.round(20 + frac * 65);
  }
  if (stage === 'finishing') return 92;
  return 8; // script
};

// Three dots + connecting lines showing which real pipeline stage we're in.
const StageTracker = ({ stage }) => {
  const currentIdx = STAGE_ORDER.indexOf(stage);
  return (
    <div className="w-full max-w-md flex items-center justify-between mb-3 px-2">
      {STAGE_ORDER.map((s, i) => (
        <React.Fragment key={s}>
          {i > 0 && (
            <div className={`flex-1 h-0.5 mx-1 ${i <= currentIdx ? 'bg-violet-500' : 'bg-white/10'}`} />
          )}
          <div className="flex flex-col items-center gap-1.5">
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                i < currentIdx
                  ? 'bg-violet-500 text-white'
                  : i === currentIdx
                    ? 'bg-violet-500 text-white animate-pulse'
                    : 'bg-white/10 border border-white/20 text-gray-400'
              }`}
            >
              {i < currentIdx ? '✓' : i + 1}
            </div>
            <span className={`text-[11px] ${i === currentIdx ? 'text-white font-medium' : 'text-gray-500'}`}>
              {STAGE_LABELS[s]}
            </span>
          </div>
        </React.Fragment>
      ))}
    </div>
  );
};

const ProcessingState = ({ onCancel }) => {
  const { genPhase, mascotColor, stage, scenesDone, scenesTotal } = useApp();
  const checking = genPhase === 'checking';
  const [idx, setIdx] = useState(0);
  const [showGame, setShowGame] = useState(false);

  // Jump to the top of the new stage's message pool whenever the stage advances.
  useEffect(() => setIdx(0), [stage]);

  // Rotate the fun messages only while actually generating.
  useEffect(() => {
    if (checking) return;
    const pool = STAGE_MESSAGES[stage] || STAGE_MESSAGES.script;
    const t = setInterval(() => setIdx((i) => (i + 1) % pool.length), 8000);
    return () => clearInterval(t);
  }, [checking, stage]);

  const pool = STAGE_MESSAGES[stage] || STAGE_MESSAGES.script;
  const message = checking ? 'Making sure it compiles ✅' : pool[idx % pool.length];
  const progress = progressPercent(stage, scenesDone, scenesTotal);
  const sceneLabel =
    stage === 'rendering' && scenesTotal > 0
      ? `Scene ${Math.min(scenesDone + 1, scenesTotal)} of ${scenesTotal} rendered`
      : '';

  return (
    <div className="flex flex-col items-center space-y-8 w-full">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 w-full mb-4 animate-fade-slide-up">
        {checking ? (
          <h2 className="text-3xl sm:text-5xl font-bold text-white mb-2">Checking your code...</h2>
        ) : (
          <p className="text-lg sm:text-xl font-medium text-white/80 tracking-wide">
            <span key={message} className="inline-block animate-fade-slide-up">
              {message}
            </span>
          </p>
        )}

        <button
          onClick={onCancel}
          className="self-start sm:self-auto bg-[#ef4444] hover:bg-red-600 text-white px-6 py-2 rounded-xl font-bold flex items-center gap-2 transition shrink-0"
        >
          <XCircle size={20} /> Cancel
        </button>
      </div>

      <div
        className={`relative w-full ${checking ? 'aspect-video' : 'min-h-[22rem] sm:min-h-[26rem] py-8'} bg-gradient-to-br from-[#2d1b4e] to-[#121212] rounded-[2.5rem] flex flex-col items-center justify-center border border-white/10 shadow-[0_0_80px_-20px_rgba(139,92,246,0.5)] animate-fade-slide-up [animation-delay:120ms] px-6`}
      >
        {checking ? (
          <>
            <img
              src="/loading.svg"
              alt="loading"
              className="w-32 h-32 mb-4 animate-pulse transition-[filter] duration-300"
              style={{ filter: filterForMascot(mascotColor) }}
            />
            <p className="text-2xl font-medium text-white tracking-wide">
              <span key={message} className="inline-block animate-fade-slide-up">
                {message}
              </span>
            </p>
          </>
        ) : showGame ? (
          <div className="flex flex-col items-center w-full">
            <button
              onClick={() => setShowGame(false)}
              className="self-start flex items-center gap-1 text-xs text-gray-400 hover:text-violet-400 transition mb-4"
            >
              ← Back to progress
            </button>
            <Flashcard />
            <div className="w-full max-w-md h-1 bg-white/10 rounded-full overflow-hidden mt-6">
              <div
                className="h-full bg-violet-500/70 rounded-full transition-[width] duration-700"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-[11px] text-gray-500 mt-1.5">
              {STAGE_LABELS[stage]}
              {sceneLabel ? ` · scene ${Math.min(scenesDone + 1, scenesTotal)} of ${scenesTotal}` : ''}
            </span>
          </div>
        ) : (
          <>
            <img
              src="/loading.svg"
              alt="loading"
              className="w-28 h-28 mb-4 animate-pulse transition-[filter] duration-300"
              style={{ filter: filterForMascot(mascotColor) }}
            />
            <p className="text-2xl font-medium text-white tracking-wide mb-1">
              <span key={message} className="inline-block animate-fade-slide-up">
                {message}
              </span>
            </p>
            {/* Reserved height so the layout doesn't jump between stages that have a scene count and those that don't. */}
            <p className="text-sm text-gray-400 mb-6 h-5">{sceneLabel || ' '}</p>

            <StageTracker stage={stage} />

            <div className="w-full max-w-md h-2 bg-white/10 rounded-full overflow-hidden mb-6">
              <div
                className="h-full bg-gradient-to-r from-violet-500 to-purple-400 rounded-full transition-[width] duration-700 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>

            <button
              onClick={() => setShowGame(true)}
              className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-violet-400 transition"
            >
              🎲 Bored? Test yourself while you wait <span>→</span>
            </button>
          </>
        )}
      </div>

      <div className="w-full bg-[#1e1e1e]/50 p-6 rounded-2xl border border-white/5 opacity-60 space-y-2 animate-fade-slide-up [animation-delay:240ms]">
        <div className="h-2 w-48 bg-gray-700 rounded"></div>
        <div className="h-2 w-64 bg-gray-800 rounded"></div>
      </div>
    </div>
  );
};

export default ProcessingState;
