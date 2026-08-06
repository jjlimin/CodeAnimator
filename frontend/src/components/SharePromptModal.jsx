import React from 'react';
import { Share2 } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { gradientForMascot } from '../mascotColors';

const SharePromptModal = () => {
  const { showSharePrompt, shareVideo, currentTitle, mascotColor } = useApp();
  if (!showSharePrompt) return null;
  const { from, to } = gradientForMascot(mascotColor);

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-slide-up">
      <div className="bg-[#1e1e1e] border border-white/10 rounded-2xl p-8 max-w-md w-full text-center shadow-2xl">
        <div
          className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4"
          style={{ backgroundColor: `${to}26` }}
        >
          <Share2 size={26} style={{ color: to }} />
        </div>
        <h3 className="text-2xl font-bold text-white mb-2">Share to Explore?</h3>
        <p className="text-gray-400 text-sm mb-6">
          Let other users see &ldquo;{currentTitle || 'this video'}&rdquo; and its code on the Explore page.
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={() => shareVideo(false)}
            className="px-6 py-2.5 rounded-xl font-bold text-gray-300 hover:text-white hover:bg-white/5 transition"
          >
            Not now
          </button>
          <button
            onClick={() => shareVideo(true)}
            style={{ backgroundImage: `linear-gradient(to right, ${from}, ${to})` }}
            className="px-6 py-2.5 rounded-xl font-bold text-white hover:brightness-110 transition"
          >
            Share
          </button>
        </div>
      </div>
    </div>
  );
};

export default SharePromptModal;
