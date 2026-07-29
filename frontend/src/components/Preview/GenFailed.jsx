import React from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';
import { useApp } from '../../context/AppContext';

// Shown when a video's generation/render failed (the state machine marked the
// job FAILED). Lets the user go back and try again.
const GenFailed = () => {
  const { newVideo } = useApp();

  return (
    <div className="flex flex-col items-center text-center gap-6 w-full max-w-xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="text-red-400">
        <AlertTriangle size={48} />
      </div>

      <div>
        <h2 className="text-4xl font-bold text-white mb-2">Video generation failed</h2>
        <p className="text-gray-400 text-lg">
          Something went wrong while creating your video. Please try again.
        </p>
      </div>

      <button
        onClick={newVideo}
        className="flex items-center justify-center gap-2 bg-gradient-to-r from-[#6d28d9] to-[#4f46e5] hover:brightness-125 text-white px-8 py-4 rounded-2xl font-bold text-lg transition-all shadow-[0_10px_50px_-10px_rgba(109,40,217,0.7)] active:scale-95"
      >
        <RotateCcw size={20} /> Try again
      </button>
    </div>
  );
};

export default GenFailed;
