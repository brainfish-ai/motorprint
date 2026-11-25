import { createBotDetector, FEATURE_NAMES, MODEL, type BotScore } from '../src/index';

const $ = (id: string) => document.getElementById(id)!;
const grid = $('grid');
for (let i = 0; i < 9; i++) {
  const b = document.createElement('button');
  b.textContent = ['Sign up', 'Pricing', 'Docs', 'Buy now', 'Contact', 'Login', 'Blog', 'Careers', 'Demo'][i];
  b.id = `btn${i + 1}`;
  grid.appendChild(b);
}
const sb = $('scrollbox');
for (let i = 0; i < 40; i++) { const p = document.createElement('p'); p.textContent = `Line ${i + 1}: scroll me with the wheel or trackpad.`; sb.appendChild(p); }
let bytes = 0;
for (const l of MODEL.layers) bytes += l.w.length;
$('msize').textContent = `${MODEL.layers.map((l) => l.o).slice(0, -1).join('-')} hidden units, ${MODEL.layers[0].bits === 32 ? 'float32' : `int${MODEL.layers[0].bits}`} weights`;

const table = $('ftable') as HTMLTableElement;
const rows = FEATURE_NAMES.map((n) => {
  const tr = table.insertRow();
  tr.innerHTML = `<td class="n">${n}</td><td class="v">0</td><td class="b"><div style="width:0"></div></td>`;
  return tr;
});
const history: number[] = [];
const spark = $('spark') as HTMLCanvasElement;
function drawSpark() {
  const c = spark.getContext('2d')!, w = spark.width, h = spark.height;
  c.clearRect(0, 0, w, h);
  c.strokeStyle = '#2c3550'; c.beginPath(); c.moveTo(0, h / 2); c.lineTo(w, h / 2); c.stroke();
  c.strokeStyle = '#7cf'; c.lineWidth = 2; c.beginPath();
  history.forEach((v, i) => { const x = (i / 59) * w, y = h - v * (h - 4) - 2; i ? c.lineTo(x, y) : c.moveTo(x, y); });
  c.stroke();
}
function render(s: BotScore) {
  (window as unknown as { __score: BotScore }).__score = s;
  $('score').textContent = s.score.toFixed(2);
  ($('arc') as unknown as SVGPathElement).style.strokeDashoffset = String(251.3 * (1 - s.score));
  $('needle').setAttribute('transform', `rotate(${-90 + 180 * s.score} 100 110)`);
  const v = $('verdict');
  const cls = s.windows < 3 ? 'unsure' : s.score >= 0.7 ? 'bot' : s.score <= 0.3 ? 'human' : 'unsure';
  v.className = `verdict ${cls}`;
  v.textContent = cls === 'bot' ? 'looks automated' : cls === 'human' ? 'looks human' : s.windows < 3 ? 'gathering signal' : 'uncertain';
  $('windows').textContent = `${s.windows} windows`;
  $('raw').textContent = `raw ${s.raw.toFixed(2)}`;
  $('inf').textContent = `${(s.inferenceMs * 1000).toFixed(0)} µs`;
  FEATURE_NAMES.forEach((n, i) => {
    const val = s.features[n];
    rows[i].cells[1].textContent = val.toFixed(2);
    const z = Math.min(1, Math.abs((val - MODEL.mean[i]) / MODEL.std[i]) / 3);
    (rows[i].cells[2].firstChild as HTMLElement).style.width = `${z * 100}%`;
  });
  history.push(s.score); if (history.length > 60) history.shift();
  drawSpark();
}
createBotDetector({ onScore: render });
