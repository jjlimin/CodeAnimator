import React, { useState } from 'react';
import { 
  UserCircle, 
  Menu, 
  PlusCircle, 
  Compass, 
  Settings, 
  ShoppingBag, 
  Folder 
} from 'lucide-react';

const Sidebar = () => {
  const [isOpen, setIsOpen] = useState(true);

  // הורדנו את ה-loading מהאובייקט הראשון
  const lastVideos = [
    { id: 1, title: 'fruits and friends' },
    { id: 2, title: 'Simple code' },
    { id: 3, title: 'x = "Guy"' },
    { id: 4, title: 'Very simple code' },
    { id: 5, title: 'x = "Guy?"' },
    { id: 6, title: 'Loop in a loop' },
    { id: 7, title: 'Difficult code' },
  ];

  const navItems = [
    { icon: <PlusCircle size={20} />, label: 'New Video' },
    { icon: <Compass size={20} />, label: 'Explore' },
    { icon: <Settings size={20} />, label: 'Setting' },
    { icon: <ShoppingBag size={20} />, label: 'Store' },
  ];

  return (
    <aside 
      className={`${
        isOpen ? 'w-64' : 'w-20'
      } bg-[#1a1a1a] h-full flex flex-col border-r border-white/5 text-gray-300 transition-all duration-300 ease-in-out`}
    >
      
      {/* פרופיל משתמש והמבורגר */}
      <div className={`p-4 flex items-center ${isOpen ? 'justify-between' : 'justify-center'} mb-6`}>
        {isOpen && (
          <div className="flex items-center gap-3 animate-in fade-in duration-300">
            <div className="text-purple-400">
              <UserCircle size={32} />
            </div>
            <span className="font-semibold text-white truncate">Yogev Shani</span>
          </div>
        )}
        <button 
          onClick={() => setIsOpen(!isOpen)} 
          className="hover:bg-white/10 p-2 rounded-xl transition-colors text-gray-400 hover:text-white"
        >
          <Menu size={20} />
        </button>
      </div>

      {/* ניווט ראשי */}
      <nav className="px-2 space-y-1 mb-10">
        {navItems.map((item, idx) => (
          <button 
            key={idx}
            className={`w-full flex items-center ${isOpen ? 'justify-start px-4' : 'justify-center'} py-3 hover:bg-white/5 rounded-xl transition-all group`}
            title={!isOpen ? item.label : ""}
          >
            <span className={`${isOpen ? 'mr-3' : ''} text-gray-400 group-hover:text-purple-400 transition-colors`}>
              {item.icon}
            </span>
            {isOpen && (
              <span className="text-sm font-medium animate-in slide-in-from-left-2 duration-300">
                {item.label}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* רשימת סרטונים אחרונים - עכשיו נקייה מספינרים */}
      <div className={`px-4 flex-1 overflow-y-auto scrollbar-hide ${!isOpen && 'hidden'}`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">
            Last Videos
          </h3>
          <Folder size={18} className="text-gray-500" />
        </div>

        <div className="space-y-1">
          {lastVideos.map((video) => (
            <div 
              key={video.id}
              className="flex items-center justify-between px-2 py-2 hover:bg-white/5 rounded-lg cursor-pointer group transition"
            >
              <span className="text-sm truncate pr-2 text-gray-400 group-hover:text-white">
                {video.title}
              </span>
              {/* הסרנו את הלוגיקה של ה-Loader2 שהייתה כאן */}
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;