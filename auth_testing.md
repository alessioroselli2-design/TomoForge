# Auth Testing Playbook (Emergent Google Auth + JWT)

TomeForge supports TWO auth methods:
1. Email/Password (JWT) — register/login return a `token`. Send as `Authorization: Bearer <token>`.
2. Emergent Google OAuth — sets httpOnly `session_token` cookie; token also stored in localStorage `tf_token`.

Unified backend auth dependency `get_current_user` accepts either:
- cookie `session_token`, OR `Authorization: Bearer <token>`
- validates first against db.user_sessions (Google), then as JWT (email/password).

## Simulate a Google session (for browser tests)
mongosh --eval "
use('test_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({ user_id: userId, email: 'test.user.'+Date.now()+'@example.com', name: 'Test User', picture: null, auth_provider:'google', created_at: new Date() });
db.user_sessions.insertOne({ user_id: userId, session_token: sessionToken, expires_at: new Date(Date.now()+7*24*60*60*1000).toISOString(), created_at: new Date().toISOString() });
print('Session token: ' + sessionToken);
"

Set cookie AND localStorage in browser:
await page.context.add_cookies([{ "name":"session_token","value":TOKEN,"domain":DOMAIN,"path":"/","httpOnly":true,"secure":true,"sameSite":"None" }])
await page.add_init_script(f"localStorage.setItem('tf_token','{TOKEN}')")

## Email/password test account
Email: mago@grimorio.it  Password: arcano123
