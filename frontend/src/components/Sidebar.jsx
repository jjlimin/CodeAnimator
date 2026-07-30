import React, { useState } from 'react';
import {
  UserCircle,
  Menu,
  PlusCircle,
  LogOut,
  Folder,
  Pencil,
  Check,
  Trash2,
  X,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { MASCOT_COLORS } from '../mascotColors';

const StatusDot = ({ status }) => {
  const color =
    status === 'COMPLETED' ? 'bg-green-500'
      : status === 'FAILED' ? 'bg-red-500'
        : 'bg-yellow-500 animate-pulse';
  return <span className={`w-2 h-2 rounded-full shrink-0 ${color}`} />;
};

const Sidebar = () => {
  const { profile, jobs, openJob, renameJob, deleteJob, newVideo, signOut, mascotColor, saveMascotColor } = useApp();
  const [isOpen, setIsOpen] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState('');
  const [deletingId, setDeletingId] = useState(null);

  const startEdit = (job, e) => {
    e.stopPropagation();
    setEditingId(job.job_id);
    setDraft(job.title || '');
  };

  const commitEdit = (jobId) => {
    if (draft.trim()) renameJob(jobId, draft.trim());
    setEditingId(null);
  };

  const displayName = profile.name || profile.email || 'My account';

  return (
    <aside
      className={`${isOpen ? 'w-64' : 'w-20'} bg-[#1a1a1a] h-full flex flex-col border-r border-white/5 text-gray-300 transition-all duration-300 ease-in-out`}
    >
      <div className={`p-4 flex items-center ${isOpen ? 'justify-between' : 'justify-center'} mb-6`}>
        {isOpen && (
          <div className="flex items-center gap-3 animate-in fade-in duration-300 min-w-0">
            <div className="text-violet-400 shrink-0">
              <UserCircle size={32} />
            </div>
            <span className="font-semibold text-white truncate" title={profile.email}>
              {displayName}
            </span>
          </div>
        )}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="hover:bg-white/10 p-2 rounded-xl transition-colors text-gray-400 hover:text-white"
        >
          <Menu size={20} />
        </button>
      </div>

      <nav className="px-2 space-y-1 mb-8">
        <button
          onClick={newVideo}
          className={`w-full flex items-center ${isOpen ? 'justify-start px-4' : 'justify-center'} py-3 hover:bg-white/5 rounded-xl transition-all group`}
          title={!isOpen ? 'New Video' : ''}
        >
          <span className={`${isOpen ? 'mr-3' : ''} text-gray-400 group-hover:text-violet-400 transition-colors`}>
            <PlusCircle size={20} />
          </span>
          {isOpen && <span className="text-sm font-medium">New Video</span>}
        </button>
      </nav>

      <div className={`px-4 flex-1 overflow-y-auto scrollbar-hide ${!isOpen && 'hidden'}`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Your Videos</h3>
          <Folder size={18} className="text-gray-500" />
        </div>

        <div className="space-y-1">
          {jobs.length === 0 && (
            <p className="text-xs text-gray-600 px-2 py-2">No videos yet — generate your first one!</p>
          )}
          {jobs.map((job) => (
            <div
              key={job.job_id}
              onClick={() => editingId !== job.job_id && openJob(job)}
              className="flex items-center gap-2 px-2 py-2 hover:bg-white/5 rounded-lg cursor-pointer group transition"
            >
              <StatusDot status={job.status} />
              {editingId === job.job_id ? (
                <>
                  <input
                    autoFocus
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    onKeyDown={(e) => e.key === 'Enter' && commitEdit(job.job_id)}
                    className="flex-1 min-w-0 bg-[#2a2a2a] text-sm text-white rounded px-2 py-1 outline-none border border-violet-500/50"
                  />
                  <button onClick={(e) => { e.stopPropagation(); commitEdit(job.job_id); }} className="text-green-400 hover:text-green-300 shrink-0">
                    <Check size={16} />
                  </button>
                </>
              ) : deletingId === job.job_id ? (
                <>
                  <span className="text-sm truncate flex-1 text-red-400">Delete this video?</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteJob(job.job_id); setDeletingId(null); }}
                    className="text-red-400 hover:text-red-300 shrink-0"
                    title="Confirm delete"
                  >
                    <Check size={16} />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setDeletingId(null); }}
                    className="text-gray-500 hover:text-gray-300 shrink-0"
                    title="Cancel"
                  >
                    <X size={16} />
                  </button>
                </>
              ) : (
                <>
                  <span className="text-sm truncate flex-1 text-gray-400 group-hover:text-white">
                    {job.title || 'Untitled'}
                  </span>
                  <button
                    onClick={(e) => startEdit(job, e)}
                    className="text-gray-600 hover:text-violet-400 opacity-0 group-hover:opacity-100 transition shrink-0"
                    title="Rename"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setDeletingId(job.job_id); }}
                    className="text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition shrink-0"
                    title="Delete"
                  >
                    <Trash2 size={14} />
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      {isOpen && (
        <div className="px-4 pt-3 pb-1 border-t border-white/5">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Codima color</h3>
          <div className="flex items-center gap-2">
            {MASCOT_COLORS.map((c) => {
              const active = c.key === mascotColor;
              return (
                <button
                  key={c.key}
                  onClick={() => saveMascotColor(c.key)}
                  aria-label={c.label}
                  title={c.label}
                  className={`w-6 h-6 rounded-full transition-all active:scale-90 ${
                    active ? 'ring-2 ring-white ring-offset-2 ring-offset-[#1a1a1a] scale-110' : 'hover:scale-110 opacity-80 hover:opacity-100'
                  }`}
                  style={{ backgroundColor: c.swatch }}
                />
              );
            })}
          </div>
        </div>
      )}

      <div className="p-2 border-t border-white/5">
        <button
          onClick={signOut}
          className={`w-full flex items-center ${isOpen ? 'justify-start px-4' : 'justify-center'} py-3 hover:bg-white/5 rounded-xl transition-all group text-gray-400 hover:text-white`}
          title={!isOpen ? 'Sign out' : ''}
        >
          <span className={isOpen ? 'mr-3' : ''}><LogOut size={20} /></span>
          {isOpen && <span className="text-sm font-medium">Sign out</span>}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
