// src/layouts/MainLayout.jsx
import Sidebar from '../components/Sidebar';

const MainLayout = ({ children }) => {
  return (
    <div className="flex h-screen bg-[#121212] text-white overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col p-12 overflow-y-auto">
        {children}
      </main>

      {/* Mascot — persistent across all views (idle / generating / done) */}
      <img
        src="/background.svg"
        alt="Mascot"
        className="fixed bottom-[-120px] right-[-60px] w-[400px] z-0 opacity-30 pointer-events-none object-contain"
      />
    </div>
  );
};

export default MainLayout;
