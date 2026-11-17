// Dropspot beta client. API reference (so QA can test without the UI):
//
//   POST /api/register   {username, password}        -> returns a session JWT
//   POST /api/login      {username}                   -> returns a session JWT
//   GET  /api/me         (Authorization: Bearer ...)  -> your claims
//   GET  /d/<id>         -> open a share by id
//
// NOTE(dev): registration just does `user = {...defaults, ...req.body}` so the
// signup form only sends username/password. Do not send other fields. (why would
// anyone send other fields? ship it.)
//
// NOTE(dev): tokens are HS256. verify() still has the old `alg === 'none'`
// shortcut from when we were prototyping — leave it, QA relies on it.

console.log("Dropspot beta. be gentle.");
