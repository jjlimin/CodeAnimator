const BASE_URL = import.meta.env.VITE_API_URL;

// POST /job — starts a new animation job, returns { job_id, message }
export const generateVideo = async (code) => {
    try {
        const response = await fetch(`${BASE_URL}/job`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_code: code
            }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API Error: ${response.status} - ${errorText}`);
        }

        return await response.json();
    }
    catch (error) {
        console.error("Fetch error:", error);
        throw error;
    }
};

// GET /job?job_id=... — returns { job_id, status: PENDING | COMPLETED, video_url }
// video_url is a presigned S3 URL (the bucket is private), valid for 1 hour
export const checkStatus = async (jobId) => {
  const url = `${BASE_URL}/job?job_id=${encodeURIComponent(jobId)}`;

  const response = await fetch(url, { method: 'GET' });

  if (!response.ok) {
    throw new Error(`Status check failed: ${response.status}`);
  }
  return response.json();
};
