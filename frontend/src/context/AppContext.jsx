import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { useAuthenticator } from '@aws-amplify/ui-react';
import { fetchUserAttributes, updateUserAttributes, fetchAuthSession } from 'aws-amplify/auth';
import {
  generateVideo,
  checkStatus,
  getJobs,
  renameJob as apiRenameJob,
  cancelJob as apiCancelJob,
  shareJob as apiShareJob,
} from '../api/videoApi';
import { DEFAULT_MASCOT_COLOR, isMascotColor } from '../mascotColors';

// Per-user localStorage key for the mascot color (source of truth; a copy is
// also best-effort mirrored to Cognito `zoneinfo` for cross-device sync).
const colorKey = (email) => `codima_mascot_color:${email || 'anon'}`;

const AppContext = createContext(null);
export const useApp = () => useContext(AppContext);

const POLL_MS = 5000;
const ACTIVE_STATUSES = ['PENDING', 'RUNNING'];

export function AppProvider({ children }) {
  const { user, signOut } = useAuthenticator((c) => [c.user]);

  const [profile, setProfile] = useState({ name: '', email: '' });
  const [profileLoaded, setProfileLoaded] = useState(false);
  const [mascotColor, setMascotColor] = useState(DEFAULT_MASCOT_COLOR);
  const [mascotColorChosen, setMascotColorChosen] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [jobsLoaded, setJobsLoaded] = useState(false);
  const [page, setPage] = useState('generate'); // generate | explore
  const [view, setView] = useState('idle'); // idle | processing | done | code_error
  const [isShared, setIsShared] = useState(false); // is the open (done) job on Explore
  const [codeError, setCodeError] = useState(''); // compile error when code is broken
  const [genPhase, setGenPhase] = useState('generating'); // checking | generating
  const [activeJobId, setActiveJobId] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [currentTitle, setCurrentTitle] = useState('');
  const [code, setCode] = useState('# Paste your code here\nprint("Hello World!")');
  const [complexity, setComplexity] = useState('balanced'); // high_level | balanced | detailed
  // Set by editVideo() to the job being replaced; the poll loop deletes it once
  // the new one completes, so an edit never leaves a duplicate in the history.
  const pendingDeleteJobIdRef = useRef(null);

  // Load the signed-in user's name/email for the greeting + sidebar.
  // Read from the ID token first — it carries `name`/`email` for BOTH email
  // and Google sign-ins, so a Google user with a name never wrongly lands on
  // onboarding. Fall back to GetUser to enrich if needed.
  // `name` still empty only for a brand-new email user -> that triggers onboarding.
  useEffect(() => {
    (async () => {
      let name = '';
      let email = '';
      let zoneinfo = ''; // repurposed to hold the mascot color (see saveMascotColor)
      try {
        const session = await fetchAuthSession();
        const claims = session.tokens?.idToken?.payload || {};
        name = claims.name || '';
        email = claims.email || '';
        zoneinfo = claims.zoneinfo || '';
      } catch { /* ignore */ }
      if (!name || !email || !zoneinfo) {
        try {
          const a = await fetchUserAttributes();
          name = name || a.name || '';
          email = email || a.email || '';
          zoneinfo = zoneinfo || a.zoneinfo || '';
        } catch { /* ignore */ }
      }
      setProfile({ name, email });

      // Resolve the mascot color: Cognito (zoneinfo) if valid, else localStorage.
      let stored = '';
      try { stored = localStorage.getItem(colorKey(email)) || ''; } catch { /* ignore */ }
      const resolved = isMascotColor(zoneinfo)
        ? zoneinfo
        : (isMascotColor(stored) ? stored : '');
      setMascotColor(resolved || DEFAULT_MASCOT_COLOR);
      setMascotColorChosen(!!resolved);
      setProfileLoaded(true);
    })();
  }, [user]);

  // Show onboarding until the user has both a name and a chosen mascot color.
  // (Google users arrive with a name, so this is what surfaces the color step.)
  const needsOnboarding = profileLoaded && (!profile.name || !mascotColorChosen);

  // Save the user's chosen name to Cognito (onboarding).
  const saveName = useCallback(async (name) => {
    const clean = (name || '').trim();
    if (!clean) return;
    await updateUserAttributes({ userAttributes: { name: clean } });
    setProfile((p) => ({ ...p, name: clean }));
  }, []);

  // Save the mascot color. localStorage is the reliable store; we also mirror it
  // to Cognito `zoneinfo` (an unused standard attribute) for cross-device sync —
  // best-effort, since the pool client may not permit writing it.
  const saveMascotColor = useCallback(async (color) => {
    if (!isMascotColor(color)) return;
    setMascotColor(color);
    setMascotColorChosen(true);
    try { localStorage.setItem(colorKey(profile.email), color); } catch { /* ignore */ }
    try {
      await updateUserAttributes({ userAttributes: { zoneinfo: color } });
    } catch { /* pool may block it; localStorage still holds the choice */ }
  }, [profile.email]);

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
  // jobsLoaded gates the app's first render (see App.jsx) so the user never
  // sees a flash of the empty "idle" screen before this resolves and jumps
  // them into the job they were actually in.
  useEffect(() => {
    (async () => {
      const list = await refreshJobs();
      const active = list.find((j) => ACTIVE_STATUSES.includes(j.status));
      if (active) {
        setActiveJobId(active.job_id);
        setCurrentTitle(active.title);
        setGenPhase('generating'); // resuming a real job — skip the checking phase
        setView('processing');
      }
      setJobsLoaded(true);
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
        // The AI-generated title lands mid-processing (from the first OpenAI
        // call), replacing createJobLambda's placeholder date/time title —
        // reflect it as soon as it shows up, not just once the job is done.
        if (data.title) {
          setCurrentTitle((t) => (data.title !== t ? data.title : t));
        }
        // Restores the code that actually produced this job, covering the
        // "still processing" job resumed after a page refresh — the editor
        // buffer otherwise still holds whatever was last typed, not this job's.
        if (data.user_code) setCode(data.user_code);
        if (data.status === 'COMPLETED' && data.video_url) {
          setVideoUrl(data.video_url);
          setIsShared(!!data.is_shared);
          setView('done');
          // This completion replaces an edited video -> remove the old row
          // now that the new one has taken its place (never both at once).
          const oldId = pendingDeleteJobIdRef.current;
          if (oldId) {
            pendingDeleteJobIdRef.current = null;
            apiCancelJob(oldId).catch((e) => console.error('cleanup of edited job failed', e)).finally(refreshJobs);
          }
        } else if (data.status === 'FAILED') {
          // The render failed (state machine Catch marked it FAILED).
          setView('gen_failed');
        }
        refreshJobs();
      } catch (e) {
        console.error('poll error', e);
        // 404 = the job was removed (failed + cleaned) -> treat as failure.
        if (!cancelled && String(e.message).includes('404')) {
          setView('gen_failed');
        }
      }
    };

    tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [view, activeJobId, refreshJobs]);

  // mode = null (normal) | 'explain_bug' (make a video explaining broken code)
  const runGenerate = useCallback(async (mode = null) => {
    // Phase 1: validating the code (server compiles it) — show "Checking...".
    setGenPhase('checking');
    setView('processing');
    setVideoUrl(null);
    try {
      const data = await generateVideo(code, complexity, mode);
      // Broken code and no choice made yet -> show the choice screen.
      if (data.needs_choice) {
        setCodeError(data.error || 'Your code has an error.');
        setView('code_error');
        return;
      }
      // Phase 2: a real job started -> switch to the fun generating messages.
      setActiveJobId(data.job_id);
      setCurrentTitle(data.title || '');
      setGenPhase('generating');
      refreshJobs();
    } catch (e) {
      console.error('generate failed', e);
      pendingDeleteJobIdRef.current = null; // the edit attempt failed -> keep the original job
      setView('idle');
    }
  }, [code, complexity, refreshJobs]);

  const startGenerate = useCallback(() => runGenerate(null), [runGenerate]);
  const generateExplainBug = useCallback(() => runGenerate('explain_bug'), [runGenerate]);
  const backToEdit = useCallback(() => {
    setCodeError('');
    setView('idle');
  }, []);

  // Open a job from the history sidebar.
  const openJob = useCallback(async (job) => {
    setPage('generate'); // history lives in the generator flow, not Explore
    if (job.status === 'COMPLETED') {
      try {
        const data = await checkStatus(job.job_id); // fresh presigned URL
        setActiveJobId(job.job_id);
        setVideoUrl(data.video_url);
        setIsShared(!!data.is_shared);
        setCurrentTitle(data.title || job.title);
        // Older jobs (created before this was stored) have no user_code —
        // leave the editor buffer alone rather than blanking it out.
        if (data.user_code) setCode(data.user_code);
        setView('done');
      } catch (e) {
        console.error('openJob failed', e);
      }
    } else if (ACTIVE_STATUSES.includes(job.status)) {
      setActiveJobId(job.job_id);
      setCurrentTitle(job.title);
      setGenPhase('generating');
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

  // Adds or removes the currently open (done) job from Explore.
  const shareVideo = useCallback(async (share) => {
    if (!activeJobId) return;
    try {
      await apiShareJob(activeJobId, share, profile.name);
      setIsShared(share);
    } catch (e) {
      console.error('share failed', e);
    }
  }, [activeJobId, profile.name]);

  const newVideo = useCallback(() => {
    pendingDeleteJobIdRef.current = null;
    setPage('generate');
    setView('idle');
    setActiveJobId(null);
    setVideoUrl(null);
    setIsShared(false);
  }, []);

  // Re-render the finished video from a DoneState edit: back to the code
  // screen with the same code, but remembers the finished job so the poll
  // loop can delete it once the new one completes -> no duplicate history row.
  const editVideo = useCallback(() => {
    pendingDeleteJobIdRef.current = activeJobId;
    setView('idle');
    setActiveJobId(null);
    setVideoUrl(null);
    setIsShared(false);
  }, [activeJobId]);

  // Cancel actually stops the running job (Step Function + render), then resets.
  const cancelJob = useCallback(async (jobId) => {
    const id = jobId || activeJobId;
    pendingDeleteJobIdRef.current = null; // aborting -> keep whatever job was being replaced, if any
    setView('idle');
    setActiveJobId(null);
    setVideoUrl(null);
    setIsShared(false);
    if (!id) return;
    try {
      await apiCancelJob(id);
    } catch (e) {
      console.error('cancel failed', e);
    } finally {
      refreshJobs();
    }
  }, [activeJobId, refreshJobs]);

  // Delete a job from the history list. Same DELETE /job endpoint as cancel —
  // the backend stops the render if it's still active, or removes the S3
  // media + row if it's a finished video. Unlike cancelJob (which targets
  // "the job currently open"), this removes an arbitrary row from the list
  // and only resets the view if that job happened to be the open one.
  const deleteJob = useCallback(async (jobId) => {
    setJobs((prev) => prev.filter((j) => j.job_id !== jobId));
    setActiveJobId((cur) => {
      if (cur !== jobId) return cur;
      setView('idle');
      setVideoUrl(null);
      return null;
    });
    try {
      await apiCancelJob(jobId);
    } catch (e) {
      console.error('delete failed', e);
    } finally {
      refreshJobs();
    }
  }, [refreshJobs]);

  const value = {
    profile,
    profileLoaded,
    jobsLoaded,
    needsOnboarding,
    saveName,
    mascotColor,
    mascotColorChosen,
    saveMascotColor,
    jobs,
    refreshJobs,
    page,
    setPage,
    view,
    genPhase,
    isShared,
    shareVideo,
    videoUrl,
    currentTitle,
    code,
    setCode,
    complexity,
    setComplexity,
    codeError,
    startGenerate,
    generateExplainBug,
    backToEdit,
    openJob,
    renameJob,
    cancelJob,
    deleteJob,
    newVideo,
    editVideo,
    signOut,
    activeJobId,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
