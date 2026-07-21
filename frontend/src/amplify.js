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
          scopes: ['openid', 'email', 'profile'],
          redirectSignIn: [
            'http://localhost:5173/',
            'https://main.d13stb50mb84v8.amplifyapp.com/',
          ],
          redirectSignOut: [
            'http://localhost:5173/',
            'https://main.d13stb50mb84v8.amplifyapp.com/',
          ],
          responseType: 'code',
        },
      },
    },
  },
});
