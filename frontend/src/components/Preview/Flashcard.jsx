import React, { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { FLASHCARDS } from '../../flashcards';
import { useApp } from '../../context/AppContext';
import { gradientForMascot } from '../../mascotColors';

const randomIndex = (excludeIdx) => {
  if (FLASHCARDS.length <= 1) return 0;
  let i = Math.floor(Math.random() * FLASHCARDS.length);
  while (i === excludeIdx) i = Math.floor(Math.random() * FLASHCARDS.length);
  return i;
};

const Flashcard = () => {
  const { mascotColor } = useApp();
  const { from, to } = gradientForMascot(mascotColor);
  const [idx, setIdx] = useState(() => randomIndex());
  const [flipped, setFlipped] = useState(false);
  const card = FLASHCARDS[idx];

  const next = (e) => {
    e.stopPropagation();
    setFlipped(false);
    setIdx((cur) => randomIndex(cur));
  };

  return (
    <div className="w-full h-full flex flex-col items-center justify-center gap-4">
      <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">
        While you wait, test yourself
      </span>

      <div className="w-full max-w-lg [perspective:1200px]">
        <div
          onClick={() => setFlipped((f) => !f)}
          className="relative h-56 sm:h-64 w-full cursor-pointer transition-transform duration-500 [transform-style:preserve-3d]"
          style={{ transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)' }}
        >
          <div className="absolute inset-0 [backface-visibility:hidden] rounded-2xl bg-[#1e1e1e] border border-white/10 flex flex-col items-center justify-center gap-3 p-8 text-center">
            <p className="text-xl sm:text-2xl font-semibold text-white">{card.q}</p>
            <span className="text-xs text-gray-500">Tap to reveal</span>
          </div>
          <div
            className="absolute inset-0 [backface-visibility:hidden] rounded-2xl flex items-center justify-center p-8 text-center"
            style={{
              backgroundImage: `linear-gradient(to bottom right, ${from}, ${to})`,
              transform: 'rotateY(180deg)',
            }}
          >
            <p className="text-lg sm:text-xl font-medium text-white">{card.a}</p>
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
