// src/layouts/MainLayout.jsx
import { useState } from 'react';
import { Menu } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import { useApp } from '../context/AppContext';
import { filterForMascot } from '../mascotColors';

const MainLayout = ({ children }) => {
  const { mascotColor } = useApp();
  // Sidebar is a static column on md+ screens; below that it becomes an
  // off-canvas drawer, closed by default, toggled from the mobile top bar.
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="flex h-screen bg-[#121212] text-white overflow-hidden">
      <Sidebar mobileOpen={mobileNavOpen} onCloseMobile={() => setMobileNavOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile-only top bar — the sidebar is off-canvas below md, so this
            hamburger is the only way to reach it (and the account/videos it holds). */}
        <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-white/5 shrink-0">
          <button
            onClick={() => setMobileNavOpen(true)}
            className="p-2 -ml-2 rounded-xl text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
            aria-label="Open menu"
          >
            <Menu size={22} />
          </button>
          <span className="font-semibold text-white">CodeAnimator</span>
        </div>

        <main className="flex-1 flex flex-col p-4 sm:p-8 lg:p-12 overflow-y-auto">
          {children}
        </main>
      </div>

      {/* Mascot — persistent across all views (idle / generating / done),
          tinted to the user's chosen Codima color. Smaller on narrow
          viewports so it doesn't crowd the content. */}
      <img
        src="/background.svg"
        alt="Mascot"
        className="fixed bottom-[-60px] right-[-40px] w-[220px] sm:bottom-[-90px] sm:right-[-50px] sm:w-[300px] lg:bottom-[-120px] lg:right-[-60px] lg:w-[400px] z-0 opacity-20 sm:opacity-30 pointer-events-none object-contain transition-[filter] duration-300"
        style={{ filter: filterForMascot(mascotColor) }}
      />
    </div>
  );
};

export default MainLayout;
