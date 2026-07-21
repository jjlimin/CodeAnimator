import React from 'react';
import { AppProvider } from './context/AppContext';
import MainLayout from './layouts/MainLayout';
import GeneratorPage from './pages/GeneratorPage';
import './index.css';

function App() {
  return (
    <div className="App">
      <AppProvider>
        <MainLayout>
          <GeneratorPage />
        </MainLayout>
      </AppProvider>
    </div>
  );
}

export default App;
