import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Authenticator,
  ThemeProvider,
  defaultDarkModeOverride,
} from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import './amplify';
import './index.css';
import App from './App.jsx';

const theme = {
  name: 'codeanimator-dark',
  overrides: [defaultDarkModeOverride],
};

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider theme={theme} colorMode="dark">
      <Authenticator.Provider>
        {/* Name is collected in the onboarding step, not at sign-up. */}
        <Authenticator socialProviders={['google']}>
          <App />
        </Authenticator>
      </Authenticator.Provider>
    </ThemeProvider>
  </StrictMode>,
);
