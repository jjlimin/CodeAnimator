import { useState, useEffect } from 'react';
import { checkStatus } from '../api/videoApi';

const POLL_INTERVAL_MS = 10000;   // 10 שניות
const MAX_POLL_MS = 15 * 60 * 1000; // אחרי 15 דקות בלי תוצאה — שגיאה

export const useVideoPoll = (jobId, isGenerating) => {
  const [status, setStatus] = useState('idle'); // idle, processing, Done, error
  const [videoUrl, setVideoUrl] = useState(null);

  useEffect(() => {
    let interval;

    if (isGenerating && jobId) {
      setStatus('processing');
      const startedAt = Date.now();

      interval = setInterval(async () => {
        try {
          const data = await checkStatus(jobId);
          if (data.status === 'COMPLETED' && data.video_url) {
            console.log("Setting Video URL:", data.video_url);
            setVideoUrl(data.video_url);
            setStatus('Done');
            clearInterval(interval);
          } else if (Date.now() - startedAt > MAX_POLL_MS) {
            console.error("Polling timed out for job", jobId);
            setStatus('error');
            clearInterval(interval);
          }
        } catch (err) {
          console.error("Polling error:", err);
        }
      }, POLL_INTERVAL_MS);
    }

    return () => clearInterval(interval);
  }, [isGenerating, jobId]);

  return { status, videoUrl, setStatus };
};
