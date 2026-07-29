// src/layouts/MainLayout.jsx
import Sidebar from '../components/Sidebar';
import { useApp } from '../context/AppContext';
import { filterForMascot } from '../mascotColors';

const MainLayout = ({ children }) => {
  const { mascotColor } = useApp();
  return (
    <div className="flex h-screen bg-[#121212] text-white overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col p-12 overflow-y-auto">
        {children}
      </main>

      {/* Mascot — persistent across all views (idle / generating / done),
          tinted to the user's chosen Codima color. */}
      <img
        src="/background.svg"
        alt="Mascot"
        className="fixed bottom-[-120px] right-[-60px] w-[400px] z-0 opacity-30 pointer-events-none object-contain transition-[filter] duration-300"
        style={{ filter: filterForMascot(mascotColor) }}
      />
    </div>
  );
};

export default MainLayout;
