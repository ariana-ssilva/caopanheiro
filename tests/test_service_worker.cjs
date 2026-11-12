const cases = [];
function test(name, run) { cases.push({name, run}); }
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

class Response {
  constructor(body) { this.body=body; this.ok=true; this.redirected=false; this.type='basic'; }
  async text() { return this.body; }
  clone() { return new Response(this.body); }
  static error() { return new Response('network error'); }
}
class Request {
  constructor(url, options) { this.url=url; Object.assign(this, options); }
}

function worker(network) {
  const listeners = {};
  const writes = [];
  const deleted = [];
  const cache = {
    match: async () => new Response('offline notice'),
    put: async key => { writes.push(key); },
    addAll: async requests => {
      assert(requests.every(request => !request.url.includes('/uploads/')));
    }
  };
  vm.runInNewContext(fs.readFileSync('app/static/service-worker.js', 'utf8'), {
    self: { location: {origin: 'https://example.com'}, addEventListener: (type, fn) => {listeners[type] = fn;}, clients: {claim: async () => {}}, skipWaiting: async () => {} },
    caches: { open: async () => cache, keys: async () => ['caopanheiro-pwa-v0', 'caopanheiro-pwa-v1', 'another-app'], delete: async key => {deleted.push(key);} },
    fetch: network, URL, Response, Request
  });
  function request(path, mode='navigate', method='GET') {
    let response;
    listeners.fetch({request: {url: new URL(path, 'https://example.com').href, mode, method}, respondWith: value => { response=value; }});
    return response;
  }
  return {request, writes, deleted, listeners};
}

test('private navigations use network and never write HTML to cache', async () => {
  const app = worker(async () => new Response('private profile'));
  assert.equal(await (await app.request('/profile')).text(), 'private profile');
  assert.deepEqual(app.writes, []);
});
test('offline navigations return a generic notice without storing the page', async () => {
  const app = worker(async () => {throw new Error('offline');});
  assert.equal(await (await app.request('/admin')).text(), 'offline notice');
  assert.deepEqual(app.writes, []);
});
test('POSTs, photos, external services and unlisted URLs are never intercepted', () => {
  const app = worker(async () => new Response('unused'));
  assert.equal(app.request('/donations', 'navigate', 'POST'), undefined);
  assert.equal(app.request('/static/uploads/profile.png', 'cors'), undefined);
  assert.equal(app.request('https://project.supabase.co/image.png', 'cors'), undefined);
  assert.equal(app.request('/my-adoptions', 'cors'), undefined);
  assert.equal(app.request('/static/style.css?private=1', 'cors'), undefined);
});
test('only allowlisted public assets are written to cache', async () => {
  const app = worker(async () => new Response('public css'));
  assert.equal(await (await app.request('/static/style.css', 'cors')).text(), 'public css');
  assert.deepEqual(app.writes, ['/static/style.css']);
});
test('activation only removes outdated caches owned by this application', async () => {
  const app = worker(async () => new Response('unused'));
  let pending;
  app.listeners.activate({waitUntil: promise => {pending=promise;}});
  await pending;
  assert.deepEqual(app.deleted, ['caopanheiro-pwa-v0']);
});

(async () => {
  for (const item of cases) {
    await item.run();
    process.stdout.write(`OK: ${item.name}\n`);
  }
  process.stdout.write(`${cases.length} service worker checks passed.\n`);
})().catch(error => { console.error(error); process.exitCode = 1; });
