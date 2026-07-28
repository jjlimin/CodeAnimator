import { fetchAuthSession } from 'aws-amplify/auth';

const BASE_URL = import.meta.env.VITE_API_URL;

// Every request carries the Cognito ID token so the API Gateway JWT authorizer
// can identify the user (and so createJobLambda stamps the job with user_id).
async function authHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    if (token) headers.Authorization = `Bearer ${token}`;
  } catch {
    // not signed in — request will be rejected by the authorizer
  }
  return headers;
}

// POST /job — start a new animation job.
// `complexity` is the requested explanation depth ('high_level'|'balanced'|'detailed').
// `mode` is optional: 'explain_bug' to make a video explaining broken code.
// Returns { job_id, title, message } on success, OR { needs_choice, error } when
// the code does not compile and no mode was chosen yet.
export const generateVideo = async (code, complexity = 'balanced', mode = null) => {
  const payload = { user_code: code, complexity };
  if (mode) payload.mode = mode;
  const response = await fetch(`${BASE_URL}/job`, {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`API Error: ${response.status} - ${await response.text()}`);
  }
  return response.json();
};

// GET /job?job_id=... — poll status. Returns { status, title, video_url }.
export const checkStatus = async (jobId) => {
  const response = await fetch(`${BASE_URL}/job?job_id=${encodeURIComponent(jobId)}`, {
    headers: await authHeaders(),
  });
  if (!response.ok) throw new Error(`Status check failed: ${response.status}`);
  return response.json();
};

// GET /jobs — the signed-in user's jobs, newest first. Returns { jobs: [...] }.
export const getJobs = async () => {
  const response = await fetch(`${BASE_URL}/jobs`, { headers: await authHeaders() });
  if (!response.ok) throw new Error(`getJobs failed: ${response.status}`);
  return response.json();
};

// PATCH /job — rename a job. Returns { job_id, title }.
export const renameJob = async (jobId, title) => {
  const response = await fetch(`${BASE_URL}/job`, {
    method: 'PATCH',
    headers: await authHeaders(),
    body: JSON.stringify({ job_id: jobId, title }),
  });
  if (!response.ok) throw new Error(`rename failed: ${response.status}`);
  return response.json();
};

// DELETE /job?job_id=... — cancel an in-progress job (stops the render).
export const cancelJob = async (jobId) => {
  const response = await fetch(`${BASE_URL}/job?job_id=${encodeURIComponent(jobId)}`, {
    method: 'DELETE',
    headers: await authHeaders(),
  });
  if (!response.ok) throw new Error(`cancel failed: ${response.status}`);
  return response.json();
};
