// Bench server: serves bench/site and stores each session's events (last POST wins) in bench/data/raw/<tool>/<sid>.json.
// The tool name is the sid prefix before the first '__'.
import http from 'node:http';
import { mkdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join, extname } from 'node:path';
const here = import.meta.dirname, site = join(here, 'site'), raw = join(here, 'data', 'raw');
const port = +(process.env.BENCH_PORT || 18790);
const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' };
http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  if (req.method === 'POST' && url.pathname === '/save') {
    let body = '';
    req.on('data', (c) => { body += c; if (body.length > 50e6) req.destroy(); });
    req.on('end', () => {
      try {
        const s = JSON.parse(body); const sid = String(s.sid).replace(/[^\w.-]/g, '_');
        const tool = sid.split('__')[0]; mkdirSync(join(raw, tool), { recursive: true });
        writeFileSync(join(raw, tool, sid + '.json'), JSON.stringify(s)); res.writeHead(200); res.end('ok');
      } catch (e) { res.writeHead(400); res.end(String(e)); }
    });
    return;
  }
  const f = join(site, url.pathname === '/' ? 'index.html' : url.pathname.replace(/\.\./g, ''));
  if (!f.startsWith(site) || !existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': types[extname(f)] || 'application/octet-stream', 'cache-control': 'no-store' }); res.end(readFileSync(f));
}).listen(port, '127.0.0.1', () => console.log(`bench server http://127.0.0.1:${port}/`));
