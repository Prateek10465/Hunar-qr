const fs=require('fs'); const {JSDOM,VirtualConsole}=require('jsdom');
const html=fs.readFileSync(require('path').join(__dirname,'..','web','index.html'),'utf8');
const errs=[]; const vc=new VirtualConsole();
vc.on('jsdomError',e=>{ if(!/Could not parse CSS|Not implemented/.test(e.message)) errs.push('jsdomError: '+(e.detail&&e.detail.stack||e.message)); });
vc.on('error',e=>errs.push('console.error: '+e));
const qrgen=require('qrcode-generator'), jsQR=require('jsqr');
const dom=new JSDOM(html,{runScripts:'dangerously',pretendToBeVisual:true,url:'https://example.test/',virtualConsole:vc,
  beforeParse(w){
    Object.defineProperty(w,'crypto',{value:require('crypto').webcrypto,configurable:true});
    w.TextEncoder=TextEncoder; w.qrcode=qrgen; w.jsQR=jsQR;
    w.matchMedia=q=>({matches:/reduced-motion/.test(q),addEventListener(){},removeEventListener(){}});
    w.scrollTo=()=>{}; w.Element.prototype.scrollIntoView=function(){};
    w.addEventListener('error',e=>errs.push('window error: '+e.message));
    w.addEventListener('unhandledrejection',e=>errs.push('unhandled rejection: '+(e.reason&&e.reason.stack||e.reason)));
  }});
const w=dom.window, d=w.document;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const ok=(c,m)=>console.log((c?'PASS ':'FAIL ')+m);
async function idle(max=20000){ const t=Date.now(); while(w.eval('S.running')&&Date.now()-t<max) await sleep(50); await sleep(100); }
const ev=(el,t)=>el.dispatchEvent(new w.Event(t,{bubbles:true,cancelable:true}));
(async()=>{
  await sleep(1500);
  ok(d.querySelector('#chat .msg.bot'),'greeting rendered');
  ok(d.querySelector('#passportFull .pp'),'sample passport rendered');
  ok(d.querySelector('#qrBox svg'),'QR svg rendered');
  ok(d.querySelector('#vres .verdict.ok'),'sample passport verifies: '+(d.querySelector('#vres .verdict')||{}).textContent);
  const ids=[...d.querySelectorAll('[id]')].map(e=>e.id); ok(ids.length===new Set(ids).size,'no duplicate ids');

  // Flow A in Tamil
  d.querySelector('[data-lang=ta]').click(); 
  ev(d.querySelector('#formA'),'submit'); await sleep(100); await idle();
  const states=[...d.querySelectorAll('#trace .tr')].map(e=>e.dataset.state);
  ok(states.every(s=>s==='done'),'flow A trace all done: '+states.join(','));
  ok(d.querySelector('#chat .pp.compact .qr svg'),'passport card with QR in chat');
  ok(w.eval('S.registry.length')===2,'second passport minted');
  // tamper
  d.querySelector('#t-verify').click(); await sleep(200);
  d.querySelector('#tamperBtn').click(); await sleep(300);
  ok(d.querySelector('#vres .verdict.bad'),'tamper fails verification');
  d.querySelector('#tamperBtn').click(); await sleep(300);
  ok(d.querySelector('#vres .verdict.ok'),'undo tamper verifies again');
  // edit payload char
  const ta=d.querySelector('#payload'); const orig=ta.value; ta.value=orig.slice(0,-3)+(orig.endsWith('AAA')?'BBB':'AAA');
  d.querySelector('#vBtn').click(); await sleep(300);
  ok(d.querySelector('#vres .verdict.bad'),'edited payload fails');
  d.querySelector('#t-demo').click();

  // Flow B text
  d.querySelector('input[name=flow][value=B]').click(); ev(d.querySelector('input[name=flow][value=B]'),'change');
  d.querySelector('#chips .chip').click();
  ev(d.querySelector('#formB'),'submit'); await sleep(100); await idle();
  ok(d.querySelector('#chat .alertc.danger'),'danger alert shown');
  ok(d.querySelectorAll('#chat .listing').length===3,'3 listings shown');
  // safe sample
  d.querySelectorAll('#chips .chip')[4].click(); ev(d.querySelector('#formB'),'submit'); await sleep(100); await idle();
  ok(d.querySelector('#chat .alertc.safe'),'safe alert for official link');

  // QR path: rasterize the sample QR and decode with jsQR
  const SAMPLE=w.eval('SAMPLE_UPI');
  const q=qrgen(0,'M'); q.addData(SAMPLE); q.make(); const n=q.getModuleCount(), px=6, W=(n+8)*px;
  const data=new Uint8ClampedArray(W*W*4).fill(255);
  for(let r=0;r<n;r++)for(let c=0;c<n;c++) if(q.isDark(r,c)) for(let y=0;y<px;y++)for(let x=0;x<px;x++){const i=(((r+4)*px+y)*W+(c+4)*px+x)*4; data[i]=data[i+1]=data[i+2]=0;}
  const dec=jsQR(data,W,W); ok(dec&&dec.data===SAMPLE,'jsQR decodes the generated sample QR');
  d.querySelector('#qrsample').click(); ok((w.eval('S.qrSrc')||'').startsWith('data:image/svg+xml'),'sample QR image attached');
  ok(!d.querySelector('#qrPrev').hidden,'QR preview visible');
  w.decodeQr=async()=>dec.data;
  d.querySelector('#fwd').value='Scan this QR to claim your grant.';
  ev(d.querySelector('#formB'),'submit'); await sleep(100); await idle();
  const last=[...d.querySelectorAll('#chat .alertc')].pop();
  ok(last&&last.classList.contains('danger'),'QR-only fee request flagged danger');
  ok(d.querySelector('#trace #tr-recv .det').textContent.includes('QR image decoded'),'trace notes QR decode');

  // criteria + calc
  d.querySelector('#t-crit').click(); await sleep(100);
  ok(!d.querySelector('#tab-crit').hidden,'criteria tab visible');
  d.querySelector('#nSlider').value='5000'; ev(d.querySelector('#nSlider'),'input');
  const dds=[...d.querySelectorAll('#calcOut dd')].map(e=>e.textContent); ok(dds[4]==='₹7,000','calc total for 5,000 = '+dds.join(' | '));

  // guided tour
  d.querySelector('#autoBtn').click(); const t0=Date.now();
  while((w.eval('S.tour')||!d.querySelector('#tourbar').hidden)&&Date.now()-t0<90000) await sleep(200);
  await sleep(300);
  ok(!w.eval('S.tour')&&d.querySelector('#tourbar').hidden,'guided demo completes ('+Math.round((Date.now()-t0)/1000)+'s)');
  ok(d.querySelector('#chat .alertc.danger'),'tour ends with danger alert');
  console.log(errs.length?('ERRORS:\n'+errs.join('\n')):'no runtime errors');
  w.close(); process.exit(0);
})().catch(e=>{console.log('SMOKE CRASH',e); console.log(errs.join('\n')); process.exit(1);});
