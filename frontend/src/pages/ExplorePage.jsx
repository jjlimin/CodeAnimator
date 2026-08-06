import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { filterForMascot } from '../mascotColors';
import { listExplore } from '../api/videoApi';
import ExploreVideoDetail from '../components/Explore/ExploreVideoDetail';
import ExploreThumbnail from '../components/Explore/ExploreThumbnail';

const ExplorePage = () => {
  const { mascotColor } = useApp();
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const [query, setQuery] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listExplore();
      setVideos(data.videos || []);
    } catch (e) {
      console.error('listExplore failed', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filteredVideos = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return videos;
    return videos.filter(
      (v) => (v.title || '').toLowerCase().includes(q) || (v.owner_name || '').toLowerCase().includes(q),
    );
  }, [videos, query]);

  return (
    <div className="flex flex-col h-full w-full">
      <header className="flex items-center justify-between mb-8 w-full">
        <div className="flex items-center gap-2">
          <img
            src="/logo.svg"
            alt="Logo"
            className="w-8 h-8 object-contain transition-[filter] duration-300"
            style={{ filter: filterForMascot(mascotColor) }}
          />
          <span className="text-xl font-bold tracking-tight text-white font-sans">CodeAnimator</span>
        </div>
      </header>

      <div className="flex-1 w-full max-w-7xl mx-auto">
        {selectedId ? (
          <ExploreVideoDetail
            jobId={selectedId}
            onBack={() => setSelectedId(null)}
            onChanged={load}
          />
        ) : (
          <>
            <div className="flex items-center justify-between gap-4 mb-6 flex-wrap">
              <h1 className="text-3xl font-bold text-white">Explore</h1>
              <div className="relative w-full max-w-xs">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search by title or creator"
                  className="w-full bg-[#1e1e1e] border border-white/10 rounded-xl pl-9 pr-3 py-2 text-sm text-white placeholder:text-gray-500 outline-none focus:border-violet-500/50 transition"
                />
              </div>
            </div>

            {loading ? (
              <p className="text-gray-500">Loading...</p>
            ) : videos.length === 0 ? (
              <p className="text-gray-500">No shared videos yet — be the first to share one!</p>
            ) : filteredVideos.length === 0 ? (
              <p className="text-gray-500">No videos match &ldquo;{query}&rdquo;.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-8">
                {filteredVideos.map((v) => (
                  <button
                    key={v.job_id}
                    onClick={() => setSelectedId(v.job_id)}
                    className="text-left group"
                  >
                    <div className="aspect-video rounded-xl overflow-hidden bg-black border border-white/10 mb-2 transition-transform group-hover:scale-[1.02]">
                      <ExploreThumbnail src={v.video_url} />
                    </div>
                    <p className="text-white font-medium truncate group-hover:text-violet-400 transition">
                      {v.title || 'Untitled'}
                    </p>
                    <p className="text-gray-500 text-sm truncate">{v.owner_name || 'Someone'}</p>
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ExplorePage;
