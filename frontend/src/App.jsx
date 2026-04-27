import React from 'react';
import MainLayout from './layouts/MainLayout';
import GeneratorPage from './pages/GeneratorPage';

// אם אתם משתמשים ב-Tailwind, ודאו שהקובץ index.css מיובא כאן או ב-main.jsx
import './index.css';

function App() {
  return (
    <div className="App">
      {/* ה-MainLayout מכיל את ה-Sidebar ואת העיצוב הכללי */}
      <MainLayout>
        {/* דף המחולל מטפל בלוגיקה של הקוד, הטעינה והצגת הוידאו */}
        <GeneratorPage />
      </MainLayout>
    </div>
  );
}

export default App;