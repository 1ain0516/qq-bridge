import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

const PORT = 3002;
const DATA_DIR = '/app/data';
const EVENTS_FILE = path.join(DATA_DIR, 'events.jsonl');

if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

const server = http.createServer((req, res) => {
  if (req.method === 'POST' && req.url === '/event') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        JSON.parse(body);
        fs.appendFileSync(EVENTS_FILE, body + '\n');
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ code: 0, message: 'ok' }));
      } catch (e) {
        res.writeHead(400);
        res.end(JSON.stringify({ code: -1, message: e.message }));
      }
    });
  } else {
    res.writeHead(405);
    res.end();
  }
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[Relay] Listening on http://127.0.0.1:${PORT}`);
});
