// Tiny local endpoint for recording real sessions from demo/collect.html.
// Usage: node tools/collect-server.mjs   -> writes data/sessions-real/<label>-<ts>.json
import http from 'node:http';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
const dir = join(import.meta.dirname, '..', 'data', 'sessions-real');
mkdirSync(dir, { recursive: true });
const cors = { 'access-control-allow-origin': '*', 'access-control-allow-headers': 'content-type', 'access-control-allow-methods': 'POST,OPTIONS' };
http.createServer((req, res) => {
  if (req.method === 'OPTIONS') { res.writeHead(204, cors); return res.end(); }
  if (req.method !== 'POST' || req.url !== '/session') { res.writeHead(404, cors); return res.end(); }
  let body = '';
  req.on('data', (c) => { body += c; if (body.length > 20e6) req.destroy(); });
  req.on('end', () => {
    try {
      const s = JSON.parse(body);
      if (!Array.isArray(s.events)) throw new Error('no events');
      const label = s.label === 'bot' ? 'bot' : 'human';
      const f = join(dir, `${label}-${Date.now()}.json`);
      writeFileSync(f, JSON.stringify(s));
      console.log('saved', f, s.events.length, 'events');
      res.writeHead(200, cors); res.end('ok');
    } catch (e) { res.writeHead(400, cors); res.end(String(e)); }
  });
}).listen(8787, () => console.log('collect server on http://localhost:8787/session ->', dir));
