import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Authenticator,
  ThemeProvider,
  defaultDarkModeOverride,
} from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import './amplify';
import './authTheme.css';
import './index.css';
import App from './App.jsx';

const theme = {
  name: 'codeanimator-dark',
  overrides: [defaultDarkModeOverride],
};

// Codima greeting shown above the sign-in form.
const components = {
  Header() {
    return (
      <>
        <div className="ca-aurora" aria-hidden="true">
          <span className="ca-blob ca-blob1"></span>
          <span className="ca-blob ca-blob2"></span>
        </div>
        <div className="codima-login-header">
          <div className="codima-brand-visual">
            <img src="/background.svg" alt="Codima" className="codima-mascot" />
          </div>
          <h1 className="codima-greeting">
            Hey, I'm <span className="codima-name">Codima</span>
          </h1>
          <p className="codima-sub">Sign in and let's animate some code.</p>
          <ul className="codima-perks" aria-hidden="true">
            <li>✦ Paste your code</li>
            <li>✦ Get a narrated animation</li>
          </ul>
        </div>
      </>
    );
  },
};

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider theme={theme} colorMode="dark">
      <Authenticator.Provider>
        <Authenticator socialProviders={['google']} components={components}>
          <App />
        </Authenticator>
      </Authenticator.Provider>
    </ThemeProvider>
  </StrictMode>,
);
