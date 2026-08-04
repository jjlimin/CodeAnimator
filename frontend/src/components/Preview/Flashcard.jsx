import React, { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { FLASHCARDS } from '../../flashcards';

const randomIndex = (excludeIdx) => {
  if (FLASHCARDS.length <= 1) return 0;
  let i = Math.floor(Math.random() * FLASHCARDS.length);
  while (i === excludeIdx) i = Math.floor(Math.random() * FLASHCARDS.length);
  return i;
};

const Flashcard = () => {
  const [idx, setIdx] = useState(() => randomIndex());
  const [flipped, setFlipped] = useState(false);
  const card = FLASHCARDS[idx];

  const next = (e) => {
    e.stopPropagation();
    setFlipped(false);
    setIdx((cur) => randomIndex(cur));
  };

  return (
    <div className="w-full flex flex-col items-center gap-3">
      <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">
        While you wait, test yourself
      </span>

      <div className="w-full max-w-md [perspective:1200px]">
        <div
          onClick={() => setFlipped((f) => !f)}
          className="relative h-36 w-full cursor-pointer transition-transform duration-500 [transform-style:preserve-3d]"
          style={{ transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)' }}
        >
          <div className="absolute inset-0 [backface-visibility:hidden] rounded-2xl bg-[#1e1e1e] border border-white/10 flex flex-col items-center justify-center gap-2 p-6 text-center">
            <p className="text-lg font-semibold text-white">{card.q}</p>
            <span className="text-xs text-gray-500">Tap to reveal</span>
          </div>
          <div
            className="absolute inset-0 [backface-visibility:hidden] rounded-2xl bg-gradient-to-br from-[#EA6F22] to-[#d35f1c] flex items-center justify-center p-6 text-center"
            style={{ transform: 'rotateY(180deg)' }}
          >
            <p className="text-base font-medium text-white">{card.a}</p>
          </div>
        </div>
      </div>

      <button
        onClick={next}
        className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-violet-400 transition"
      >
        Next question <ArrowRight size={14} />
      </button>
    </div>
  );
};

export default Flashcard;
