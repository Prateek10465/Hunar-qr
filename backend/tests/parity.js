// Runs the browser fraud engine (the <script id="logic"> block of web/index.html) on a JSON list of messages.
// usage: node parity.js <index.html> <corpus.json>
const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf8');
const logic = /<script id="logic">([\s\S]*?)<\/script>/.exec(html)[1];
const HQ = new Function(logic + ';return HQ;')();
const corpus = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const out = corpus.map((t) => {
  const a = HQ.analyze(t);
  return {
    verdict: a.verdict, score: a.score,
    titles: a.findings.map((f) => f.title),
    urls: a.urls.map((u) => [u.host, u.flagged]),
    upis: a.upis.map((u) => [u.kind, u.pa, u.am]),
  };
});
process.stdout.write(JSON.stringify(out));
