import { Amplify } from 'aws-amplify';

// Public Cognito identifiers (safe to ship in client code).
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: 'us-east-1_CdEf0NcY1',
      userPoolClientId: '57jgajbnfmeuesfci2qq0umlea',
      loginWith: {
        email: true,
        oauth: {
          domain: 'codeanimator-auth-2026.auth.us-east-1.amazoncognito.com',
          // aws.cognito.signin.user.admin lets fetchUserAttributes/updateUserAttributes
          // work for OAuth (Google) sign-ins — without it the access token lacks the
          // scope and reading the user's name fails, wrongly forcing onboarding.
          scopes: ['openid', 'email', 'profile', 'aws.cognito.signin.user.admin'],
          redirectSignIn: [
            'http://localhost:5173/',
            'https://main.d13stb50mb84v8.amplifyapp.com/',
            'https://codeanimator.app/',
            'https://www.codeanimator.app/',
          ],
          redirectSignOut: [
            'http://localhost:5173/',
            'https://main.d13stb50mb84v8.amplifyapp.com/',
            'https://codeanimator.app/',
            'https://www.codeanimator.app/',
          ],
          responseType: 'code',
        },
      },
    },
  },
});
