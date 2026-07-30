import React, { useState } from 'react';
import { Sparkles, ArrowRight, Check } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { MASCOT_COLORS, filterForMascot, DEFAULT_MASCOT_COLOR } from '../mascotColors';

const Onboarding = () => {
  const { profile, saveName, saveMascotColor, signOut } = useApp();

  // Google users already have a name, so they start straight at the color step.
  const needsName = !profile.name;
  const [step, setStep] = useState(needsName ? 'name' : 'color');
  const [name, setName] = useState('');
  const [color, setColor] = useState(DEFAULT_MASCOT_COLOR);
  const [saving, setSaving] = useState(false);

  const submitName = (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setStep('color');
  };

  const finish = async () => {
    if (saving) return;
    setSaving(true);
    try {
      if (needsName && name.trim()) await saveName(name.trim());
      await saveMascotColor(color);
    } catch (err) {
      console.error('onboarding save failed', err);
      setSaving(false);
    }
  };

  return (
    <div className="flex h-screen w-full items-center justify-center bg-[#121212] text-white p-6">
      {step === 'name' ? (
        <form
          onSubmit={submitName}
          className="w-full max-w-md flex flex-col items-center text-center gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500"
        >
          <div className="text-violet-400">
            <Sparkles size={48} />
          </div>
          <div>
            <h1 className="text-4xl font-bold mb-2">Welcome to CodeAnimator!</h1>
            <p className="text-gray-400 text-lg">First, what should we call you?</p>
          </div>

          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            className="w-full bg-[#1e1e1e] border border-white/10 focus:border-violet-500/60 outline-none rounded-2xl px-5 py-4 text-lg text-center transition-all"
          />

          <button
            type="submit"
            disabled={!name.trim()}
            className="w-full bg-gradient-to-r from-[#EA6F22] to-[#d35f1c] hover:brightness-125 disabled:opacity-40 disabled:cursor-not-allowed text-white px-8 py-4 rounded-2xl font-bold text-lg transition-all shadow-[0_10px_50px_-10px_rgba(234,111,34,0.7)] active:scale-95 flex items-center justify-center gap-2"
          >
            Continue <ArrowRight size={20} />
          </button>

          <button type="button" onClick={signOut} className="text-gray-500 hover:text-gray-300 text-sm transition">
            Sign out
          </button>
        </form>
      ) : (
        <div className="w-full max-w-md flex flex-col items-center text-center gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="relative">
            <div
              className="absolute inset-[-18%] rounded-full blur-2xl -z-10"
              style={{ background: 'radial-gradient(circle, rgba(124,58,237,0.45), transparent 62%)' }}
            />
            <img
              src="/background.svg"
              alt="Codima"
              className="w-40 h-40 object-contain transition-[filter] duration-300"
              style={{ filter: filterForMascot(color) }}
            />
          </div>

          <div>
            <h1 className="text-3xl font-bold mb-2">
              {needsName && name.trim() ? `Nice to meet you, ${name.trim()}!` : 'Pick your Codima'}
            </h1>
            <p className="text-gray-400 text-lg">Choose a color — you can change it anytime.</p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3">
            {MASCOT_COLORS.map((c) => {
              const active = c.key === color;
              return (
                <button
                  key={c.key}
                  type="button"
                  onClick={() => setColor(c.key)}
                  aria-label={c.label}
                  title={c.label}
                  className={`relative w-11 h-11 rounded-full transition-all active:scale-90 ${
                    active ? 'ring-2 ring-white ring-offset-2 ring-offset-[#121212] scale-110' : 'hover:scale-105 opacity-85 hover:opacity-100'
                  }`}
                  style={{ backgroundColor: c.swatch }}
                >
                  {active && (
                    <Check size={18} strokeWidth={3} className="absolute inset-0 m-auto text-white drop-shadow" />
                  )}
                </button>
              );
            })}
          </div>

          <button
            type="button"
            onClick={finish}
            disabled={saving}
            className="w-full bg-gradient-to-r from-[#EA6F22] to-[#d35f1c] hover:brightness-125 disabled:opacity-40 disabled:cursor-not-allowed text-white px-8 py-4 rounded-2xl font-bold text-lg transition-all shadow-[0_10px_50px_-10px_rgba(234,111,34,0.7)] active:scale-95 flex items-center justify-center gap-2"
          >
            {saving ? 'Setting up...' : (<>Let's animate some code <ArrowRight size={20} /></>)}
          </button>

          <button type="button" onClick={signOut} className="text-gray-500 hover:text-gray-300 text-sm transition">
            Sign out
          </button>
        </div>
      )}
    </div>
  );
};

export default Onboarding;
