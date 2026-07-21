import React, { useState } from 'react';
import { Sparkles, ArrowRight } from 'lucide-react';
import { useApp } from '../context/AppContext';

const Onboarding = () => {
  const { saveName, signOut } = useApp();
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!name.trim() || saving) return;
    setSaving(true);
    try {
      await saveName(name.trim());
    } catch (err) {
      console.error('saveName failed', err);
      setSaving(false);
    }
  };

  return (
    <div className="flex h-screen w-full items-center justify-center bg-[#121212] text-white p-6">
      <form
        onSubmit={submit}
        className="w-full max-w-md flex flex-col items-center text-center gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500"
      >
        <div className="text-purple-400">
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
          className="w-full bg-[#1e1e1e] border border-white/10 focus:border-purple-500/60 outline-none rounded-2xl px-5 py-4 text-lg text-center transition-all"
        />

        <button
          type="submit"
          disabled={!name.trim() || saving}
          className="w-full bg-gradient-to-r from-[#6d28d9] to-[#4f46e5] hover:brightness-125 disabled:opacity-40 disabled:cursor-not-allowed text-white px-8 py-4 rounded-2xl font-bold text-lg transition-all shadow-[0_10px_50px_-10px_rgba(109,40,217,0.7)] active:scale-95 flex items-center justify-center gap-2"
        >
          {saving ? 'Setting up...' : (<>Continue <ArrowRight size={20} /></>)}
        </button>

        <button type="button" onClick={signOut} className="text-gray-500 hover:text-gray-300 text-sm transition">
          Sign out
        </button>
      </form>
    </div>
  );
};

export default Onboarding;
