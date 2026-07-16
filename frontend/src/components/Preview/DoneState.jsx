import React from 'react';
import ReactPlayer from 'react-player';
import Editor from '@monaco-editor/react';
import { Pencil, Download } from 'lucide-react';

const DoneState = ({ videoUrl, code, onEdit }) => (
  <div className="flex flex-col space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700 w-full">
    <div className="flex justify-between items-start">
      <div>
        <h2 className="text-5xl font-bold text-white mb-2">Video generated successfully!</h2>
        <p className="text-gray-400 text-xl">Title: My first video</p>
      </div>
      
      <div className="flex gap-6">
        <button onClick={onEdit} className="flex items-center gap-2 text-gray-300 hover:text-white transition-colors text-lg">
          <Pencil size={20} /> Edit code
        </button>
        <a href={videoUrl} download className="flex items-center gap-2 text-gray-300 hover:text-white transition-colors text-lg">
          <Download size={20} /> Download
        </a>
      </div>
    </div>
{/* 
    <div className="rounded-[2.5rem] overflow-hidden shadow-2xl border-8 border-[#2a2a2a] bg-black aspect-video relative group">
      <ReactPlayer muted key={videoUrl} url={videoUrl} controls width="100%" height="100%" playing />
    </div> */}

    <div className="rounded-[2.5rem] overflow-hidden shadow-2xl border-8 border-[#2a2a2a] bg-black aspect-video relative group">
      {/* בלי autoPlay/muted — כדי שהקריינות תישמע בלחיצת Play.
          בלי crossOrigin — לבאקט אין הגדרת CORS ומדיה לא צריכה אותה */}
      <video
        key={videoUrl}
        controls
        className="w-full h-full object-contain"
      >
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

export default DoneState;