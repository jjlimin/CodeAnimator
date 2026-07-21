import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import MainLayout from './layouts/MainLayout';
import GeneratorPage from './pages/GeneratorPage';
import Onboarding from './components/Onboarding';
import './index.css';

function Shell() {
  const { profileLoaded, needsOnboarding } = useApp();

  // Avoid a flash of the wrong screen before the profile has loaded.
  if (!profileLoaded) return <div className="h-screen w-full bg-[#121212]" />;
  if (needsOnboarding) return <Onboarding />;

  return (
    <MainLayout>
      <GeneratorPage />
    </MainLayout>
  );
}

function App() {
  return (
    <div className="App">
      <AppProvider>
        <Shell />
      </AppProvider>
    </div>
  );
}

export default App;
