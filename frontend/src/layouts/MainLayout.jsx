// src/layouts/MainLayout.jsx
import Sidebar from '../components/Sidebar';

const MainLayout = ({ children }) => {
  return (
    <div className="flex h-screen bg-[#121212] text-white overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col p-12 overflow-y-auto">
        {children}
      </main>
    </div>
  );
};

export default MainLayout;