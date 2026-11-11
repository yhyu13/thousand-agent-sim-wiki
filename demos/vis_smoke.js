const fs = require('fs'); const path = require('path');
const dir = process.argv[2];
const html = fs.readFileSync(path.join(dir, 'visualize.html'), 'utf8');
const js = html.match(/<script>([\s\S]*)<\/script>/)[1];
const elements = {};
function mkEl(id) { return { id, innerHTML: '', textContent: '', dataset: {},
  classList: { add() {}, remove() {} }, addEventListener() {}, getAttribute() { return 'fr'; }, click() {} }; }
const tabButtons = [0,1,2].map(i => ({ dataset: { night: String(i) },
  addEventListener(ev, fn) { if (ev === 'click') this._click = fn; } }));
global.document = { getElementById: id => elements[id] || (elements[id] = mkEl(id)),
  querySelectorAll: sel => sel === '.tabs button' ? tabButtons : [] };
let alerts = [];
global.alert = m => { alerts.push(m); };
global.FileReader = class { readAsText() {} };
eval(js + '\nglobal.__vis = { ingest, render, state, updateLoadState };');
const { ingest, render, state } = global.__vis;
const app = () => elements['app'].innerHTML;
const ls = () => elements['loadstate'].textContent;
let pass = 0, fail = 0;
function check(name, cond) { if (cond) { pass++; console.log('PASS', name); } else { fail++; console.log('FAIL', name); } }

// 1. 初始合成
check('synthetic label', ls().includes('合成示例'));
check('synthetic banner', app().includes('概览为内置合成示例'));
check('synthetic distinct cost', app().includes('0.1235') && !app().includes('0.2050'));

// 2. R7 MAJOR-1 XSS 向量：minute/day 恶意字符串
const evil = [
  {type:'conversation',day:0,minute:'"><img src=x onerror=window.__x=1>',mode:'llm',text:'hi'},
  {type:'conversation',day:'"><img src=x onerror=window.__x=2>',minute:730,mode:'llm',text:'hi'},
  {_stream:'audit',type:'rollback',day:0,minute:'"><img src=x onerror=window.__x=3>',detail:'d'},
  {_stream:'audit',type:'breaker_open',day:'"><img src=x onerror=window.__x=4>',minute:760,detail:'d'},
];
ingest('evil.jsonl', evil.map(e => JSON.stringify(e)).join('\n'));
render();
check('XSS minute cx escaped/skipped', !app().includes('<img src=x'));
check('XSS day escaped', !app().includes('<img src=x') && app().includes('&lt;img') || !app().includes('<img'));
check('no raw onerror attr', !/onerror=window/.test(app().replace(/&lt;img[^>]*onerror=window[^&]*&gt;/g, '')));

// 3. R7 MAJOR-2：只载入 report → 时间轴合成 + 标注
ingest('morning_report.json', fs.readFileSync(path.join(dir, 'out/morning_report.json'), 'utf8'));
render();
check('report-only loadstate', ls().includes('真实报告') && ls().includes('时间轴为合成示例'));
check('report-only timeline note', app().includes('时间轴当前为合成示例'));
check('report-only real overview', app().includes('2fe29e0a8fe988bd') && !app().includes('概览为内置合成示例'));
// 再载入 events → 全真实
ingest('events.jsonl', fs.readFileSync(path.join(dir, 'out/events.jsonl'), 'utf8'));
render();
check('both loaded label', ls().includes('真实运行数据') && !ls().includes('合成'));
check('real timeline no synth note', !app().includes('时间轴当前为合成示例'));
// 只载入 events（全新状态，未载入 report）→ 概览合成横幅
eval(js + '\nglobal.__vis2 = { ingest, render, state };');
const v2 = global.__vis2;
v2.ingest('events2.jsonl', fs.readFileSync(path.join(dir, 'out/events.jsonl'), 'utf8'));
v2.render();
check('events-only overview banner', elements['app'].innerHTML.includes('概览为内置合成示例'));
check('events-only loadstate', elements['loadstate'].textContent.includes('概览为合成示例'));

// 4. 健壮性
const badTok = JSON.parse(fs.readFileSync(path.join(dir, 'out/morning_report.json'), 'utf8'));
badTok.tokens.T1 = [null, 5];
ingest('badtok.json', JSON.stringify(badTok)); render();
check('null token no crash', alerts.length === 0 && app().includes('数据无效'));
const manyNights = JSON.parse(fs.readFileSync(path.join(dir, 'out/morning_report.json'), 'utf8'));
manyNights.nights_planned = 50000;
ingest('many.json', JSON.stringify(manyNights)); render();
check('nights capped 366', (app().match(/data-night/g) || []).length === 366);
ingest('bom.json', '﻿' + fs.readFileSync(path.join(dir, 'out/morning_report.json'), 'utf8')); render();
check('BOM report routed', ls().includes('真实报告'));
// R8 修复守卫：null/标量行过滤、dayLabel null、CSS 暗色覆盖源顺序
ingest('nullline.jsonl', 'null\n' + JSON.stringify({type:'conversation',day:0,minute:730,mode:'llm',text:'ok'}) + '\n42');
render();
check('null/scalar lines filtered', alerts.length === 0 && state.events.length === 1);
ingest('nullday.jsonl', JSON.stringify({_stream:'audit',type:'rollback',day:null,minute:760,detail:'d'}));
render();
check('dayLabel null -> ?', app().includes('第?夜'));
const cssDarkIdx = html.lastIndexOf('.badge { color: #0f172a; }');
const cssBaseIdx = html.indexOf('.badge { display:');
check('dark badge override after base (R8 MINOR-1)', cssDarkIdx > cssBaseIdx && cssDarkIdx > 0);
// R9 守卫：sample_events null 渲染安全、畸形行容错、全无效拒绝
const badReport = JSON.parse(fs.readFileSync(path.join(dir, 'out/morning_report.json'), 'utf8'));
badReport.sample_events = [null];
let renderOk = true;
try { ingest('badreport.json', JSON.stringify(badReport)); render(); } catch (e) { renderOk = false; }
check('sample_events null render safe', renderOk);
ingest('mixed.jsonl', 'null\n{bad\n' + JSON.stringify({type:'conversation',day:0,minute:730,mode:'llm',text:'ok'}));
render();
check('bad line tolerated', state.events.length === 1);
let threw = false;
try { ingest('allbad.jsonl', '{bad\n[1,2]'); } catch (e) { threw = true; }
check('all-invalid file rejected', threw);
// R10 M6 守卫（R11 MINOR-2 校准）：**结构守卫是有效 M6 守卫**（正则查 try/catch 存在）；
// 行为点击只验证处理器接线——render 对 JSON 数据高度容错，无法区分 try/catch 有无（M7 实证），不声称行为兜底。
check('tab handler render guard present (M6)', /addEventListener\("click"[\s\S]{0,160}try \{ render\(\); \}/.test(html));
ingest('badreport2.json', JSON.stringify(badReport));
render();
let tabThrew = false;
try { tabButtons[1]._click(); } catch (e) { tabThrew = true; }
check('tab click wiring no uncaught throw (aux)', !tabThrew);
// 5. R30 居民记忆流查看器（检查点载入 + XSS + 容错 + 独立性）
check('synth resident section', app().includes('居民记忆流') && app().includes('baker-001'));
const ck = { tick: 144, world: { seed: 1, n: 2, day: 1, abs_minute: 1440,
  residents: [
    { id: 'nurse-001', role: 'nurse', home: 'h1', work: 'w1', focus: 'health',
      memories: [{ day: 0, minute: 600, text: '正常记忆', importance: 5, kind: 'event', keywords: ['工作'] }] },
    { id: '<img src=x onerror=window.__r=1>', role: '<script>alert(1)</script>', home: 'h2', work: 'w2', focus: null,
      memories: [{ day: 0, minute: '"><img src=x onerror=window.__r=2>', text: '<img src=x onerror=window.__r=3>',
        importance: 7, kind: 'event', keywords: ['<img src=x onerror=window.__r=4>'] }] } ],
  plans: { 'nurse-001': [{ start: 0, end: 360, state: 'sleep', location: 'h1' }] } } };
ingest('ckpt.json', JSON.stringify(ck)); render();
check('checkpoint loadstate', ls().includes('检查点') && ls().includes('居民记忆流真实'));
check('checkpoint real resident rendered', app().includes('nurse-001') && app().includes('正常记忆'));
check('resident XSS id/role/text escaped', !app().includes('<img src=x') && !app().includes('<script>alert'));
check('resident selector present', app().includes('id="resSelect"') && app().includes('<option'));
check('checkpoint plan rendered', app().includes('当日计划') && app().includes('sleep'));
check('checkpoint keeps report (independent)', state.report !== null && state.realReport === true);
const ckNull = { tick: 1, world: { residents: [{ id: 'x-001', role: 'baker',
  memories: [null, { text: 'ok', importance: 'nan', minute: 'bad' }] }], plans: {} } };
let ckOk = true;
try { ingest('cknull.json', JSON.stringify(ckNull)); render(); } catch (e) { ckOk = false; }
check('null memory render safe', ckOk && alerts.length === 0);
eval(js + '\nglobal.__vis3 = { ingest, render, state };');
const v3 = global.__vis3;
v3.state.checkpoint = { tick: 1, world: { residents: [] } };
v3.render();
check('empty-checkpoint note', elements['app'].innerHTML.includes('当前未载入'));
// 6. R31 硬化：居民/计划上限 + 记忆精确计数
const manyRes = { tick: 1, world: { residents: [], plans: {} } };
for (let i = 0; i < 2001; i++) manyRes.world.residents.push({ id: 'r-' + i, role: 'baker', memories: [] });
ingest('manyres.json', JSON.stringify(manyRes)); render();
check('resident options capped 2000', (app().match(/<option/g) || []).length === 2000 && app().includes('仅显示前 2000'));
const manyPlan = { tick: 1, world: { residents: [{ id: 'p-001', role: 'baker',
  memories: [null, { text: 'ok', importance: 5, minute: 600, kind: 'event', keywords: [] }] }], plans: { 'p-001': [] } } };
for (let i = 0; i < 301; i++) manyPlan.world.plans['p-001'].push({ start: i, end: i + 1, state: 'work', location: 'w' });
ingest('manyplan.json', JSON.stringify(manyPlan)); render();
check('plan rows capped 300', (app().match(/<tr><td>\d+–\d+<\/td>/g) || []).length === 300 && app().includes('计划段过多'));
check('memory count excludes null', app().includes('记忆 1 条'));
// 7. R32 微硬化：数组记忆排除 + 分数索引归整
const arrMem = { tick: 1, world: { residents: [
  { id: 'a-001', role: 'baker', memories: [null, 42, 'str', [], { text: 'ok', importance: 5, minute: 600, kind: 'e', keywords: [] }] },
  { id: 'b-002', role: 'nurse', memories: [] } ], plans: {} } };
ingest('arrmem.json', JSON.stringify(arrMem)); render();
check('array memory excluded', app().includes('记忆 1 条'));
state.selectedResident = 1.5; render();
check('fractional index truncated to resident 1', app().includes('<b>b-002</b>'));
console.log('alerts:', alerts.length ? alerts : 'none');
console.log('RESULT:', pass, 'pass /', fail, 'fail');
process.exit(fail ? 1 : 0);
