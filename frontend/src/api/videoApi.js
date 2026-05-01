import { USER_ID } from '../constants/auth';

const BASE_URL = import.meta.env.VITE_API_URL;

export const generateVideo = async (projectId, code) => {
    try {
        const response = await fetch(`${BASE_URL}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                UserID: USER_ID,
                ProjectID: projectId,
                code: code
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

export const checkStatus = async (projectId) => {
  const cleanId = projectId.startsWith('PROJ#') ? projectId.replace('PROJ#', '') : projectId;
  const url = `${BASE_URL}/status?userId=${encodeURIComponent(USER_ID)}&projectId=${encodeURIComponent(cleanId)}`;
  
  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
  });
  
  if (!response.ok) {
    throw new Error(`Status check failed: ${response.status}`);
  }
  return response.json();
};