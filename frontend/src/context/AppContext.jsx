import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { useAuthenticator } from '@aws-amplify/ui-react';
import { fetchUserAttributes } from 'aws-amplify/auth';
import {
  generateVideo,
  checkStatus,
  getJobs,
  renameJob as apiRenameJob,
} from '../api/videoApi';

const AppContext = createContext(null);
export const useApp = () => useContext(AppContext);

const POLL_MS = 5000;
const ACTIVE_STATUSES = ['PENDING', 'RUNNING'];

export function AppProvider({ children }) {
  const { user, signOut } = useAuthenticator((c) => [c.user]);

  const [profile, setProfile] = useState({ name: '', email: '' });
  const [jobs, setJobs] = useState([]);
  const [view, setView] = useState('idle'); // idle | processing | done
  const [activeJobId, setActiveJobId] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [currentTitle, setCurrentTitle] = useState('');
  const [code, setCode] = useState('# Paste your code here\nprint("Hello World!")');

  // Load the signed-in user's name/email for the greeting + sidebar.
  useEffect(() => {
    fetchUserAttributes()
      .then((a) => setProfile({ name: a.name || a.email || '', email: a.email || '' }))
      .catch(() => {});
  }, [user]);

  const refreshJobs = useCallback(async () => {
    try {
      const data = await getJobs();
      setJobs(data.jobs || []);
      return data.jobs || [];
    } catch (e) {
      console.error('getJobs failed', e);
      return [];
    }
  }, []);

  // On load: fetch history and resume any job still in progress (refresh fix).
  useEffect(() => {
    (async () => {
      const list = await refreshJobs();
      const active = list.find((j) => ACTIVE_STATUSES.includes(j.status));
      if (active) {
        setActiveJobId(active.job_id);
        setCurrentTitle(active.title);
        setView('processing');
      }
    })();
  }, [refreshJobs]);

  // Poll the active job while processing.
  useEffect(() => {
    if (view !== 'processing' || !activeJobId) return;
    let cancelled = false;

    const tick = async () => {
      try {
        const data = await checkStatus(activeJobId);
        if (cancelled) return;
        if (data.status === 'COMPLETED' && data.video_url) {
          setVideoUrl(data.video_url);
          setCurrentTitle((t) => data.title || t);
          setView('done');
          refreshJobs();
        }
      } catch (e) {
        console.error('poll error', e);
      }
    };

    tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [view, activeJobId, refreshJobs]);

  const startGenerate = useCallback(async () => {
    setView('processing');
    setVideoUrl(null);
    try {
      const data = await generateVideo(code);
      setActiveJobId(data.job_id);
      setCurrentTitle(data.title || '');
      refreshJobs();
    } catch (e) {
      console.error('generate failed', e);
      setView('idle');
    }
  }, [code, refreshJobs]);

  // Open a job from the history sidebar.
  const openJob = useCallback(async (job) => {
    if (job.status === 'COMPLETED') {
      try {
        const data = await checkStatus(job.job_id); // fresh presigned URL
        setActiveJobId(job.job_id);
        setVideoUrl(data.video_url);
        setCurrentTitle(data.title || job.title);
        setView('done');
      } catch (e) {
        console.error('openJob failed', e);
      }
    } else if (ACTIVE_STATUSES.includes(job.status)) {
      setActiveJobId(job.job_id);
      setCurrentTitle(job.title);
      setView('processing');
    }
  }, []);

  const renameJob = useCallback(
    async (jobId, title) => {
      const clean = (title || '').trim();
      if (!clean) return;
      try {
        await apiRenameJob(jobId, clean);
        setJobs((prev) => prev.map((j) => (j.job_id === jobId ? { ...j, title: clean } : j)));
        setActiveJobId((cur) => {
          if (cur === jobId) setCurrentTitle(clean);
          return cur;
        });
      } catch (e) {
        console.error('rename failed', e);
      }
    },
    [],
  );

  const newVideo = useCallback(() => {
    setView('idle');
    setActiveJobId(null);
    setVideoUrl(null);
  }, []);

  const value = {
    profile,
    jobs,
    view,
    videoUrl,
    currentTitle,
    code,
    setCode,
    startGenerate,
    openJob,
    renameJob,
    newVideo,
    signOut,
    activeJobId,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
