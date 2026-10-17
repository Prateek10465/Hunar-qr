// Loads the web demo from a live backend and drives it. Requires python deps installed (see backend/requirements.txt).
const fs = require('fs'), os = require('os'), path = require('path');
const { spawn } = require('child_process');
const { JSDOM, VirtualConsole } = require('jsdom');
const qrgen = require('qrcode-generator'), jsQR = require('jsqr');

const PORT = +process.env.PORT || 8765, BASE = `http://127.0.0.1:${PORT}`;
const ROOT = path.join(__dirname, '..');
const venvPy = process.platform === 'win32' ? path.join(ROOT, '.venv', 'Scripts', 'python.exe') : path.join(ROOT, '.venv', 'bin', 'python');
const PY = process.env.PYTHON || (fs.existsSync(venvPy) ? venvPy : 'python3');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failed = 0;
const ok = (c, m) => { if (!c) failed++; console.log((c ? 'PASS ' : 'FAIL ') + m); };

async function startServer() {
  const data = fs.mkdtempSync(path.join(os.tmpdir(), 'hunar-e2e-'));
  const proc = spawn(PY, ['-m', 'uvicorn', 'app.main:create_app', '--factory', '--host', '127.0.0.1', '--port', String(PORT), '--log-level', 'warning'], {
    cwd: path.join(ROOT, 'backend'),
    env: { ...process.env, DATA_DIR: data, WEB_DIR: path.join(ROOT, 'web'), PUBLIC_BASE_URL: BASE, HASH_SECRET: 'e2e-secret' },
  });
  let log = '';
  proc.stderr.on('data', (b) => (log += b)); proc.stdout.on('data', (b) => (log += b));
  for (let i = 0; i < 100; i++) {
    try { if ((await fetch(BASE + '/healthz')).ok) return { proc, log: () => log }; } catch (e) {}
    await sleep(200);
  }
  proc.kill(); throw new Error('server did not start:\n' + log);
}

(async () => {
  const srv = await startServer();
  const errs = [];
  try {
    const vc = new VirtualConsole();
    vc.on('jsdomError', (e) => { if (!/Could not parse CSS|Not implemented/.test(e.message)) errs.push('jsdomError: ' + ((e.detail && e.detail.stack) || e.message)); });
    const dom = await JSDOM.fromURL(BASE + '/', {
      runScripts: 'dangerously', pretendToBeVisual: true, virtualConsole: vc,
      beforeParse(w) {
        Object.defineProperty(w, 'crypto', { value: require('crypto').webcrypto, configurable: true });
        w.TextEncoder = TextEncoder; w.qrcode = qrgen; w.jsQR = jsQR;
        w.fetch = (u, o) => fetch(new URL(u, BASE), o);
        w.FormData = FormData; w.Blob = Blob; w.File = File; w.AbortController = AbortController;
        w.matchMedia = (q) => ({ matches: /reduced-motion/.test(q), addEventListener() {}, removeEventListener() {} });
        w.scrollTo = () => {}; w.Element.prototype.scrollIntoView = function () {};
        w.addEventListener('error', (e) => errs.push('window error: ' + e.message));
        w.addEventListener('unhandledrejection', (e) => errs.push('unhandled rejection: ' + ((e.reason && e.reason.stack) || e.reason)));
      },
    });
    const w = dom.window, d = w.document;
    const ev = (el, t) => el.dispatchEvent(new w.Event(t, { bubbles: true, cancelable: true }));
    const idle = async (max = 20000) => { const t = Date.now(); await sleep(60); while (w.eval('S.running') && Date.now() - t < max) await sleep(40); await sleep(80); };
    const stats = async () => (await fetch(BASE + '/api/stats')).json();
    const say = async (text) => { d.querySelector('#compText').value = text; ev(d.querySelector('#composer'), 'submit'); await idle(); };
    const tap = async (label) => { const b = [...d.querySelectorAll('#chat .chip')].reverse().find((x) => x.textContent === label); if (!b) throw new Error('no button ' + label); b.click(); await idle(); };

    await sleep(1500);
    ok(/Connected to the Hunar-QR backend/.test(d.querySelector('#modeNote').textContent), 'page detects the backend: ' + d.querySelector('#modeNote').textContent.slice(0, 90));
    ok(!d.querySelector('#composer').hidden, 'chat composer is shown');
    ok(d.querySelector('#passportFull .pp'), 'demo passport loaded from the server');
    ok(d.querySelector('#qrBox img') && /\/qr\.png\?s=/.test(d.querySelector('#qrBox img').src), 'server QR image shown');
    ok(d.querySelector('#vres .verdict.ok'), 'server verifies the demo passport: ' + (d.querySelector('#vres .verdict') || {}).textContent);
    ok(/\/v\/HQR-TN-\d\d-\d{6}\?s=/.test(d.querySelector('#payload').value), 'QR payload is the verification link');
    const tags = [...d.querySelectorAll('#trace .tag')].map((x) => x.textContent);
    ok(tags.length === 7, 'trace rendered');

    // Flow A through the API
    d.querySelector('#trade').value = 'tailoring'; ev(d.querySelector('#trade'), 'change');
    d.querySelector('[data-lang=ta]').click();
    d.querySelector('#mlang').value = 'ta';
    ev(d.querySelector('#formA'), 'submit'); await sleep(100); await idle();
    const states = [...d.querySelectorAll('#trace .tr')].map((e) => e.dataset.state);
    ok(states.every((s) => s === 'done'), 'flow A trace all done: ' + states.join(','));
    ok(w.eval('S.registry.length') === 2 && w.eval('S.registry[1].server'), 'passport minted by the server');
    ok(d.querySelector('#chat .pp.compact .qr img'), 'passport card in chat uses the server QR image');
    ok((await stats()).passports_issued === 2, 'server counted 2 passports');
    const taskTags = [...d.querySelectorAll('#trace .tag')].map((x) => x.textContent);
    ok(taskTags[1] === 'Sample output' && taskTags[3] === 'Sample output', 'mock providers are labelled as sample');

    // verify tab + tamper
    d.querySelector('#t-verify').click(); await sleep(400);
    ok(d.querySelector('#vres .verdict.ok'), 'new passport verifies on the server');
    d.querySelector('#tamperBtn').click(); await sleep(500);
    ok(d.querySelector('#vres .verdict.bad'), 'altered hours fail verification on the server');
    d.querySelector('#tamperBtn').click(); await sleep(500);
    ok(d.querySelector('#vres .verdict.ok'), 'undo verifies again');
    const ta = d.querySelector('#payload'); const orig = ta.value; ta.value = orig.slice(0, -3) + (orig.endsWith('AAA') ? 'BBB' : 'AAA');
    d.querySelector('#vBtn').click(); await sleep(500);
    ok(d.querySelector('#vres .verdict.bad'), 'edited QR payload fails');
    d.querySelector('#t-demo').click();

    // Flow B through the API
    d.querySelector('input[name=flow][value=B]').click(); ev(d.querySelector('input[name=flow][value=B]'), 'change');
    d.querySelector('#chips .chip').click();
    ev(d.querySelector('#formB'), 'submit'); await sleep(100); await idle();
    ok(d.querySelector('#chat .alertc.danger'), 'server flags the scam as danger');
    ok(d.querySelectorAll('#chat .listing').length === 3, '3 listings shown');
    ok((await stats()).messages_checked >= 1, 'server counted the check');

    // Free chat with the real bot
    d.querySelector('#clear').click(); await idle();
    await say('hello');
    ok([...d.querySelectorAll('#chat .chip')].some((c) => c.textContent === 'தமிழ்'), 'bot offers language buttons');
    await tap('English'); await tap('Skill Passport');
    await say('Anitha R.'); await tap('Tailoring'); await say('Lakshmi Ammal'); await say('40'); await tap('Yes');
    d.querySelector('#compPhoto').click(); await idle();
    ok(/voice note/.test([...d.querySelectorAll('#chat .msg.bot')].pop().textContent), 'bot accepted the photo and asks for the voice note');
    d.querySelector('#compVoice').click(); await idle();
    const qrImg = [...d.querySelectorAll('#chat img.ev')].pop();
    ok(qrImg && qrImg.src.startsWith('data:image/png;base64,'), 'bot sent the passport QR image');
    ok((await stats()).passports_issued === 3, 'bot minted a third passport');
    const open = [...d.querySelectorAll('#chat button')].find((b) => b.textContent === 'Open verification page' && !b.closest('.pp'));
    ok(!!open, 'bot offers the verification page');
    open.click(); await sleep(800);
    ok(w.eval('S.registry.length') === 3 && !d.querySelector('#tab-verify').hidden && d.querySelector('#vres .verdict.ok'), 'verification page for the bot-made passport is valid');
    ok(/Anitha R\./.test(d.querySelector('#passportFull').textContent), 'passport shows the name typed in chat');

    // scam forward in chat, and an image without a QR
    d.querySelector('#t-demo').click();
    await say('Pay ₹99 processing fee at bit.ly/pm-kaushal-claim');
    ok(/Danger/.test([...d.querySelectorAll('#chat .msg.bot')].slice(-2)[0].textContent), 'bot flags a forwarded scam');

    ok(errs.length === 0, errs.length ? 'runtime errors:\n' + errs.join('\n') : 'no runtime errors');
    w.close();
  } catch (e) {
    failed++; console.log('FAIL e2e crashed:', e.stack || e); if (errs.length) console.log(errs.join('\n'));
  } finally {
    srv.proc.kill();
  }
  console.log(failed ? `${failed} check(s) failed` : 'all checks passed');
  process.exit(failed ? 1 : 0);
})();
