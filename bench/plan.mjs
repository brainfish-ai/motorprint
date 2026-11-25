// Deterministic session plan: which task and inputs each tool session uses. Same plan for every tool.
// Usage: node bench/plan.mjs [N per tool] -> bench/plan.json
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
const N = +(process.argv[2] || process.env.BENCH_N || 300);
let s = 20261125; const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 2 ** 32);
const pick = (a) => a[Math.floor(rnd() * a.length)];
const FIRST = ['Ana', 'Ben', 'Chloe', 'Dev', 'Emma', 'Farid', 'Grace', 'Hiro', 'Isla', 'Jai', 'Kim', 'Liam', 'Mia', 'Noah', 'Omar', 'Priya'];
const LAST = ['Smith', 'Nguyen', 'Patel', 'Garcia', 'Kim', 'Brown', 'Singh', 'Tanaka', 'Muller', 'Lee'];
const COUNTRY = ['Australia', 'Canada', 'Germany', 'India', 'Japan', 'United States'];
const MSG = ['a friend', 'google search', 'podcast ad', 'instagram', 'my sister', 'news article', 'youtube'];
const QUERY = ['red shoes', 'leather bag', 'sun hat', 'gift card', 'running socks', 'travel mug', 'phone case'];
const TASKS = ['form', 'nav', 'read', 'search'];
const plan = [];
for (let i = 0; i < N; i++) {
  const first = pick(FIRST), last = pick(LAST);
  plan.push({ i, task: TASKS[i % 4], seed: Math.floor(rnd() * 1e9), first, last,
    email: `${first}.${last}${Math.floor(rnd() * 90 + 10)}@example.com`.toLowerCase(), country: pick(COUNTRY), msg: pick(MSG),
    query: pick(QUERY), result: Math.floor(rnd() * 6), nav: Array.from({ length: 3 + Math.floor(rnd() * 2) }, () => Math.floor(rnd() * 4)),
    scrolls: 4 + Math.floor(rnd() * 5), scrollPx: pick([100, 200, 300, 400]) });
}
writeFileSync(join(import.meta.dirname, 'plan.json'), JSON.stringify(plan));
console.log('plan', plan.length, 'sessions per tool');
