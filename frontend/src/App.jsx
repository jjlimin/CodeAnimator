import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import MainLayout from './layouts/MainLayout';
import GeneratorPage from './pages/GeneratorPage';
import ExplorePage from './pages/ExplorePage';
import Onboarding from './components/Onboarding';
import './index.css';

function Shell() {
  const { profileLoaded, jobsLoaded, needsOnboarding, page } = useApp();

  // Avoid a flash of the wrong screen before the profile has loaded.
  if (!profileLoaded) return <div className="h-screen w-full bg-[#121212]" />;
  if (needsOnboarding) return <Onboarding />;
  // Avoid a flash of the empty "idle" screen before we know whether there's
  // a job to resume (e.g. still generating) — that check happens async.
  if (!jobsLoaded) return <div className="h-screen w-full bg-[#121212]" />;

  return (
    <MainLayout>
      {page === 'explore' ? <ExplorePage /> : <GeneratorPage />}
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
