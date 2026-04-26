import { USER_ID } from '../constants/auth';

const BASE_URL = 'https://agrl5kqhai.execute-api.us-east-1.amazonaws.com'; 

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
            // אם יש שגיאת CORS או שגיאת שרת, נתפוס אותה כאן
            const errorText = await response.text();
            throw new Error(`API Error: ${response.status} - ${errorText}`);
        }

        return await response.json();
    } 
    catch (error) {
        console.error("Fetch error:", error);
        throw error; // זריקת השגיאה כדי שה-UI ידע להציג מצב שגיאה
    }
};

export const checkStatus = async (projectId) => {
  // הלמדה שלך מוסיפה "PROJ#" בעצמה, לכן אנחנו חייבים לשלוח לה מזהה נקי.
  // אם ה-ID הוא "video#123", נשלח רק "video#123". 
  // אם הוא בטעות כבר "PROJ#video#123", ננקה אותו.
  const cleanId = projectId.startsWith('PROJ#') ? projectId.replace('PROJ#', '') : projectId;
  
  // חשוב: וודאי שהאותיות הקטנות/גדולות ב-URL תואמות למה שהלמדה מצפה לו ב-params.get()
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