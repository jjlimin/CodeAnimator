import React, { useState, useEffect } from 'react';
import { XCircle } from 'lucide-react';

const MESSAGES = [
  'Generating narration...',
  'Working hard on your video...',
  'Teaching the robots to animate 🤖',
  'Wait just a little more — AI is hard!',
  'Rendering frame by frame 🎞️',
  'Bribing the GPU to hurry up...',
  'Turning your code into cinema 🎬',
  'Sprinkling in a little magic ✨',
  'Making the pixels dance...',
  'Almost there, hang tight!',
];

const ProcessingState = ({ onCancel }) => {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setIdx((i) => (i + 1) % MESSAGES.length), 3000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex flex-col items-center space-y-8 animate-in fade-in zoom-in duration-500 w-full">
      <style>{`@keyframes ca-float{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}`}</style>

      <div className="text-left w-full mb-4">
        <h2 className="text-5xl font-bold text-white mb-2">Generating your video...</h2>
        {/* Outer element floats gently; inner span slides in on every message change */}
        <p className="text-gray-400 text-xl italic" style={{ animation: 'ca-float 3s ease-in-out infinite' }}>
          <span key={idx} className="inline-block animate-in fade-in slide-in-from-bottom-2 duration-500">
            {MESSAGES[idx]}
          </span>
        </p>
      </div>

      <div className="relative w-full aspect-video bg-gradient-to-br from-[#2d1b4e] to-[#121212] rounded-[2.5rem] flex flex-col items-center justify-center border border-white/10 shadow-[0_0_80px_-20px_rgba(139,92,246,0.5)]">
        <img src="/loading.svg" alt="loading" className="w-32 h-32 mb-4 animate-pulse" />
        <p className="text-2xl font-medium text-white tracking-wide">
          <span key={idx} className="inline-block animate-in fade-in slide-in-from-bottom-2 duration-500">
            {MESSAGES[idx]}
          </span>
        </p>
      </div>

      <div className="w-full bg-[#1e1e1e]/50 p-6 rounded-2xl border border-white/5 flex justify-between items-center opacity-60">
        <div className="space-y-2">
          <div className="h-2 w-48 bg-gray-700 rounded"></div>
          <div className="h-2 w-64 bg-gray-800 rounded"></div>
        </div>
        <button
          onClick={onCancel}
          className="bg-[#ef4444] hover:bg-red-600 text-white px-6 py-2 rounded-xl font-bold flex items-center gap-2 transition"
        >
          <XCircle size={20} /> Cancel
        </button>
      </div>
    </div>
  );
};

export default ProcessingState;
