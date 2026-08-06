import React, { useEffect, useState } from 'react';
import Editor from '@monaco-editor/react';
import { ArrowLeft, Check, Share2 } from 'lucide-react';
import { checkStatus, saveExploreVideo, shareJob } from '../../api/videoApi';
import { useApp } from '../../context/AppContext';

const ExploreVideoDetail = ({ jobId, onBack, onChanged }) => {
  const { jobs, refreshJobs } = useApp();
  const [data, setData] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [removing, setRemoving] = useState(false);
  // Own videos already live in `jobs` (the signed-in user's own history) —
  // no need for the backend to expose ownership on the public Explore feed.
  const isOwner = jobs.some((j) => j.job_id === jobId);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const d = await checkStatus(jobId);
        if (!cancelled) setData(d);
      } catch (e) {
        console.error('load explore video failed', e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  const handleSave = async () => {
    if (saving || saved) return;
    setSaving(true);
    try {
      await saveExploreVideo(jobId);
      setSaved(true);
      refreshJobs();
    } catch (e) {
      console.error('save failed', e);
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async () => {
    if (removing) return;
    setRemoving(true);
    try {
      await shareJob(jobId, false);
      onChanged?.();
      onBack();
    } catch (e) {
      console.error('remove from explore failed', e);
      setRemoving(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 animate-fade-slide-up">
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-gray-400 hover:text-white transition"
      >
        <ArrowLeft size={18} /> Back to Explore
      </button>

      {!data ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <>
          <div className="flex justify-between items-center gap-2">
            <h2 className="text-2xl sm:text-3xl font-bold text-white truncate min-w-0">
              {data.title || 'Untitled'}
            </h2>
            {isOwner ? (
              <button
                onClick={handleRemove}
                disabled={removing}
                className="flex items-center gap-2 text-red-400 hover:text-red-300 transition-colors text-lg shrink-0 disabled:opacity-50"
              >
                <Share2 size={20} /> {removing ? 'Removing...' : 'Remove from Explore'}
              </button>
            ) : (
              <button
                onClick={handleSave}
                disabled={saving || saved}
                className="flex items-center gap-2 text-gray-300 hover:text-white transition-colors text-lg shrink-0 disabled:opacity-50"
              >
                {saved ? (
                  <>
                    <Check size={20} className="text-green-400" /> Saved
                  </>
                ) : (
                  <>{saving ? 'Saving...' : 'Save to my videos'}</>
                )}
              </button>
            )}
          </div>

          <div className="rounded-[2.5rem] overflow-hidden shadow-2xl border-8 border-[#2a2a2a] bg-black aspect-video">
            <video key={data.video_url} controls className="w-full h-full object-contain">
              <source src={data.video_url} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          </div>

          <div className="rounded-2xl overflow-hidden border border-white/10 bg-[#1e1e1e] p-4">
            <Editor
              height="300px"
              defaultLanguage="python"
              theme="vs-dark"
              value={data.user_code}
              options={{ readOnly: true, fontSize: 13, minimap: { enabled: false } }}
            />
          </div>
        </>
      )}
    </div>
  );
};

export default ExploreVideoDetail;
