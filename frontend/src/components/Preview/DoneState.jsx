import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { Pencil, Download, Check } from 'lucide-react';

const DoneState = ({ videoUrl, title, code, onRename, onEdit }) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(title || '');
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    setDraft(title || '');
  }, [title]);

  const commit = () => {
    if (draft.trim() && draft.trim() !== title) onRename(draft.trim());
    setEditing(false);
  };

  // Fetch the video as a blob and save it directly (a plain <a download> is
  // ignored for cross-origin S3 URLs, which is why it used to open a new tab).
  const handleDownload = async () => {
    if (!videoUrl || downloading) return;
    setDownloading(true);
    try {
      const res = await fetch(videoUrl);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(title || 'codeanimator-video').replace(/[^\w\-]+/g, '_')}.mp4`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('download failed', e);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="flex flex-col space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700 w-full">
      <div className="flex justify-between items-start">
        <div className="min-w-0">
          <h2 className="text-5xl font-bold text-white mb-2">Video generated successfully!</h2>
          <div className="flex items-center gap-2 text-gray-400 text-xl">
            {editing ? (
              <>
                <input
                  autoFocus
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && commit()}
                  className="bg-[#1e1e1e] text-white rounded px-2 py-1 outline-none border border-purple-500/50 text-lg"
                />
                <button onClick={commit} className="text-green-400 hover:text-green-300">
                  <Check size={20} />
                </button>
              </>
            ) : (
              <>
                <span className="truncate">{title || 'Untitled'}</span>
                <button
                  onClick={() => setEditing(true)}
                  className="text-gray-500 hover:text-purple-400 transition shrink-0"
                  title="Rename"
                >
                  <Pencil size={18} />
                </button>
              </>
            )}
          </div>
        </div>

        <div className="flex gap-6 shrink-0">
          <button onClick={onEdit} className="flex items-center gap-2 text-gray-300 hover:text-white transition-colors text-lg">
            <Pencil size={20} /> New video
          </button>
          <button onClick={handleDownload} disabled={downloading} className="flex items-center gap-2 text-gray-300 hover:text-white transition-colors text-lg disabled:opacity-50">
            <Download size={20} /> {downloading ? 'Downloading...' : 'Download'}
          </button>
        </div>
      </div>

      <div className="rounded-[2.5rem] overflow-hidden shadow-2xl border-8 border-[#2a2a2a] bg-black aspect-video relative group">
        {/* No muted/autoPlay so the TTS narration is audible on Play */}
        <video key={videoUrl} controls className="w-full h-full object-contain">
          <source src={videoUrl} type="video/mp4" />
          Your browser does not support the video tag.
        </video>
      </div>

      <div className="rounded-2xl overflow-hidden border border-white/10 bg-[#1e1e1e] p-4 opacity-80 scale-95 origin-top">
        <Editor
          height="150px"
          defaultLanguage="python"
          theme="vs-dark"
          value={code}
          options={{ readOnly: true, fontSize: 12, minimap: { enabled: false } }}
        />
      </div>
    </div>
  );
};

export default DoneState;
