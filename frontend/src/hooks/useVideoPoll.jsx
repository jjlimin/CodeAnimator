import { useState, useEffect } from 'react';
import { checkStatus } from '../api/videoApi';

export const useVideoPoll = (projectId, isGenerating) => {
  const [status, setStatus] = useState('idle'); // idle, processing, done, error
  const [videoUrl, setVideoUrl] = useState(null);

  useEffect(() => {
    let interval;

    if (isGenerating && projectId) {
      setStatus('processing');
      
      interval = setInterval(async () => {
        try {
          const data = await checkStatus(projectId);
          if (data.Status === 'Done' || data.S3_VideoUrl) {
            console.log("Setting Video URL:", data.S3_VideoUrl);
            setVideoUrl(data.S3_VideoUrl);
            setStatus('Done');
            clearInterval(interval);
          }
        } catch (err) {
          console.error("Polling error:", err);
        }
      }, 15000); // 15 שניות
    }

    return () => clearInterval(interval);
  }, [isGenerating, projectId]);

  return { status, videoUrl, setStatus };
};