'use strict';
const $ = s => document.querySelector(s);
const params = new URLSearchParams(location.search);
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
const alphabet = ' ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:/-';
const columns = [
  ['time', 'TIME', 5], ['airport', 'AIRPORT', 3], ['direction', 'A / D', 3],
  ['flight', 'FLIGHT', 7], ['destination', 'FROM / TO', 18], ['gate', 'GATE', 4], ['status', 'STATUS', 10]
];
let config, saved, airports = [], rows = [], data = [], feeds = [];
let requestId = 0, refreshTimer, demoTimer, turningTimer, screenMode = params.has('screensaver'), demoStep = 0;
let lastUpdate = null, nextRefresh = null, dismissed = false;
let draftDirty = false;

function clean(value) {
  return String(value ?? '').toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/Ø/g, 'O').replace(/Æ/g, 'AE').replace(/[^ A-Z0-9:/-]/g, ' ');
}

class Flap {
  constructor() {
    this.el = document.createElement('div'); this.el.className = 'flap';
    this.el.setAttribute('aria-hidden', 'true');
    this.el.innerHTML = '<div class="face upper"><span> </span></div><div class="face lower"><span> </span></div><div class="face upper swing-upper"><span> </span></div><div class="face lower swing-lower"><span> </span></div>';
    this.faces = [...this.el.querySelectorAll('span')]; this.current = ' '; this.target = ' '; this.version = 0;
  }
  instant(char) { this.faces.forEach(face => face.textContent = char); this.current = char; this.el.classList.remove('flipping'); }
  set(char, delay = 0, replay = false) {
    if (!replay && char === this.target) return;
    const version = ++this.version; this.target = char;
    if (reducedMotion.matches || document.hidden) { this.instant(char); return; }
    const steps = replay || this.current === ' ' ? 3 + Math.floor(Math.random() * 3) : 2;
    let step = 0;
    const flip = () => {
      if (version !== this.version || !this.el.isConnected) return;
      const next = ++step >= steps ? char : alphabet[(Math.max(0, alphabet.indexOf(this.current)) + 3 + step * 2) % alphabet.length];
      this.el.classList.remove('flipping');
      this.faces[0].textContent = next; this.faces[1].textContent = this.current;
      this.faces[2].textContent = this.current; this.faces[3].textContent = next;
      void this.el.offsetWidth; this.el.classList.add('flipping');
      setTimeout(() => {
        if (version !== this.version || !this.el.isConnected) return;
        this.instant(next);
        if (step < steps) flip();
      }, 185);
    };
    setTimeout(flip, delay);
  }
}

function createBoard() {
  rows.forEach(r => Object.values(r.cells).flat().forEach(c => c.version++));
  $('#rows').replaceChildren(); $('.column-labels').replaceChildren(); rows = [];
  for (const [key, label, length] of columns) {
    const el = document.createElement('div'); el.textContent = label; el.dataset.column = key;
    el.style.width = `calc(var(--cell-w) * ${length} + var(--cell-gap) * ${length - 1})`;
    $('.column-labels').append(el);
  }
  for (let i = 0; i < config.rows; i++) {
    const el = document.createElement('div'); el.className = 'flight-row';
    const cells = {};
    for (const [key, , length] of columns) {
      const group = document.createElement('div'); group.className = `flap-group group-${key}`;
      cells[key] = Array.from({length}, () => new Flap()); cells[key].forEach(c => group.append(c.el)); el.append(group);
    }
    $('#rows').append(el); rows.push({el, cells, id: null});
  }
  fitBoard(); renderBoard();
}

function fitBoard() {
  if (!config) return;
  const area = $('#rows').getBoundingClientRect();
  const width = area.width; const small = width < 750;
  const groupGap = small ? 7 : 17; const cellGap = width < 550 ? 1 : small ? 2 : 3;
  const count = columns.reduce((sum, c) => sum + c[2], 0);
  const cellWidth = (width - groupGap * (columns.length - 1) - cellGap * (count - columns.length)) / count;
  const rowGap = Math.max(3, Math.min(9, area.height / config.rows * .12));
  const height = Math.max(12, (area.height - rowGap * (config.rows - 1)) / config.rows);
  const fontSize = Math.max(7, Math.min(cellWidth * 1.6, height * .62));
  const style = document.documentElement.style;
  style.setProperty('--cell-w', cellWidth + 'px'); style.setProperty('--cell-h', height + 'px');
  style.setProperty('--font-size', fontSize + 'px'); style.setProperty('--cell-gap', cellGap + 'px');
  style.setProperty('--group-gap', groupGap + 'px');
}

function zone(flight) { return config.timezone === 'utc' ? 'UTC' : config.timezone === 'local' ? undefined : flight?.timezone || 'Europe/Oslo'; }
function timeText(value, timezone) { return new Intl.DateTimeFormat('en-GB', {hour:'2-digit', minute:'2-digit', timeZone:timezone}).format(new Date(value)); }

function visibleFlights() {
  const now = Date.now();
  return data.filter(f => {
    if (config.mode === 'arrivals' && f.direction !== 'A' || config.mode === 'departures' && f.direction !== 'D') return false;
    return Date.parse(f.estimated) > now;
  }).sort((a, b) => Date.parse(a.estimated) - Date.parse(b.estimated)).slice(0, config.rows);
}

function renderBoard(replay = false) {
  if (!config || !rows.length) return;
  const visible = visibleFlights();
  const isEmpty = !visible.length;
  $('#empty').hidden = !isEmpty;
  if (isEmpty && (feeds.length || config.demo)) {
    const allFailed = !config.demo && feeds.every(f => f.error && !f.fetchedAt);
    $('#empty h2').textContent = allFailed ? 'The connection is taking a break' : 'A quiet moment on the runway';
    $('#empty p').textContent = allFailed ? 'The live feed is unavailable. We’ll retry automatically. You can try the animation demo in Settings.' : 'No upcoming flights match this view. Try another airport, show both directions, or explore the animation demo in Settings.';
  }
  rows.forEach((row, i) => {
    const f = visible[i];
    const values = f ? {time:timeText(f.estimated, zone(f)), airport:f.airport, direction:f.direction === 'A' ? 'ARR' : 'DEP',
      flight:f.flight, destination:f.destination, gate:f.gate || '—', status:f.status} : {};
    row.id = f?.id; row.el.classList.toggle('row-complete', !!f?.complete);
    row.el.setAttribute('aria-label', f ? `${f.airport} ${f.direction === 'A' ? 'arrival from' : 'departure to'} ${f.destination}, ${f.flight}, ${values.time}, ${f.status}${f.gate ? ', gate ' + f.gate : ''}` : 'Empty row');
    row.el.title = f ? `${f.flight} · ${f.destination} (${f.otherAirport}) · Scheduled ${timeText(f.scheduled, zone(f))} · ${f.status}` : '';
    let offset = 0;
    for (const [key, , length] of columns) {
      const value = clean(values[key] || '').padEnd(length).slice(0, length);
      row.cells[key].forEach((cell, j) => cell.set(value[j], i * 32 + (offset + j) * 7, replay)); offset += length;
    }
  });
}

function applyConfig(rebuild = false) {
  ['background', 'grid', 'letters'].forEach(key => document.documentElement.style.setProperty('--' + key, config[key]));
  $('#title').replaceChildren(document.createTextNode(config.mode === 'arrivals' ? 'Arrivals' : config.mode === 'departures' ? 'Departures' : 'Arrivals & departures'));
  const period = document.createElement('span'); period.textContent = '.'; $('#title').append(period);
  $('#eyebrow').textContent = config.demo ? 'ANIMATION DEMO · SIMULATED FLIGHTS' : 'A WINDOW TO THE WORLD';
  $('#airport-summary').replaceChildren();
  config.airports.forEach((code, i) => {
    const span = document.createElement('span'); const b = document.createElement('b'); b.textContent = code;
    const name = document.createElement('span'); name.className = 'airport-name'; name.textContent = airports.find(a=>a.code === code)?.name || code;
    span.append(b, name); $('#airport-summary').append(span);
    if (i < config.airports.length - 1) { const dot = document.createElement('span'); dot.className = 'dot'; dot.textContent = '·'; $('#airport-summary').append(dot); }
  });
  $('#time-note').textContent = config.timezone === 'utc' ? 'ALL TIMES UTC' : config.timezone === 'local' ? 'TIMES IN YOUR LOCAL ZONE' : 'TIMES LOCAL TO AIRPORT';
  if (rebuild || rows.length !== config.rows) createBoard(); else renderBoard();
  updateClock(); updateStatus();
}

function scheduleRefresh() {
  clearTimeout(refreshTimer);
  nextRefresh = null;
  if (config.demo) return;
  nextRefresh = Date.now() + config.refreshMinutes * 60000;
  refreshTimer = setTimeout(fetchLive, config.refreshMinutes * 60000);
}

function scheduleTurning() {
  clearInterval(turningTimer);
  if (!config.constantTurning) return;
  // Replay the current flights locally, independently of the live feed timer.
  turningTimer = setInterval(() => {
    if (!document.hidden && !reducedMotion.matches) renderBoard(true);
  }, 30000);
}

async function fetchLive() {
  const id = ++requestId; const codes = config.airports.join(',');
  clearTimeout(refreshTimer);
  try {
    const response = await fetch('/api/flights?airports=' + encodeURIComponent(codes) + '&refreshMinutes=' + config.refreshMinutes, {signal:AbortSignal.timeout(65000)});
    if (!response.ok) throw new Error('Flight request failed');
    const result = await response.json();
    if (id !== requestId || config.demo) return;
    feeds = result.feeds; data = feeds.flatMap(f => f.flights);
    console.info(`Split-Flap: ${data.length} flights loaded from ${feeds.length} airport feeds.`);
    const fetched = feeds.map(f => f.fetchedAt).filter(Boolean);
    lastUpdate = fetched.length ? Math.min(...fetched) * 1000 : null;
    renderBoard(); updateStatus();
  } catch (error) {
    if (id !== requestId || config.demo) return;
    feeds = config.airports.map(airport => ({airport, stale:true, error:'Connection unavailable', fetchedAt:lastUpdate ? lastUpdate/1000 : null}));
    renderBoard(); updateStatus();
  } finally {
    if (id === requestId) scheduleRefresh();
  }
}

const sampleRoutes = [
  ['LONDON HEATHROW','LHR','SK805','D','E8'], ['COPENHAGEN','CPH','SK1462','A',''],
  ['AMSTERDAM','AMS','KL1198','D','E9'], ['PARIS CDG','CDG','AF1275','D','E13'],
  ['BERGEN','BGO','DY601','A',''], ['NEW YORK JFK','JFK','SK903','D','F26'],
  ['FRANKFURT','FRA','LH861','D','E12'], ['TROMSO','TOS','DY371','A',''],
  ['STOCKHOLM','ARN','SK884','D','D3'], ['REYKJAVIK','KEF','FI319','D','F12'],
  ['HELSINKI','HEL','AY912','D','E2'], ['TRONDHEIM','TRD','SK341','A',''],
  ['ROME FIUMICINO','FCO','DY1870','D','E14'], ['BERLIN','BER','DY1102','D','D8'],
  ['ZURICH','ZRH','LX1211','A',''], ['MUNICH','MUC','LH2453','D','E5'],
  ['VIENNA','VIE','OS336','D','E6'], ['EDINBURGH','EDI','DY1354','D','F16'],
  ['BARCELONA','BCN','DY1740','D','D2'], ['NICE','NCE','DY1407','A','']
];
function makeDemo() {
  const base = Math.floor(Date.now()/60000)*60000;
  data = sampleRoutes.map((r,i) => ({id:'demo'+i, airport:config.airports[i % config.airports.length],
    direction:r[3], flight:r[2], destination:r[0], otherAirport:r[1], gate:r[4],
    scheduled:new Date(base+(i+1)*180000).toISOString(), estimated:new Date(base+(i+1)*180000).toISOString(),
    status:i===2?'BOARDING':i===7?'DELAYED':'ON TIME', complete:false, timezone:'Europe/Oslo'}));
  demoStep=0; renderBoard();
}
function tickDemo() {
  const candidate = visibleFlights()[demoStep % Math.max(1, Math.min(config.rows, visibleFlights().length))];
  if (!candidate) { makeDemo(); return; }
  if (demoStep % 4 === 0) { candidate.status = candidate.direction === 'A' ? 'ARRIVED' : 'DEPARTED'; candidate.complete=true; candidate.statusTime=new Date().toISOString(); candidate.estimated=candidate.statusTime; }
  else if (demoStep % 4 === 1) { candidate.status='DELAYED'; candidate.estimated=new Date(Date.parse(candidate.estimated)+900000).toISOString(); }
  else if (demoStep % 4 === 2) { candidate.status=candidate.direction === 'A'?'EXPECTED':'BOARDING'; }
  else { candidate.gate = 'E'+(2+demoStep%20); candidate.status='GATE CHANGE'; }
  demoStep++; renderBoard();
  if (demoStep > 25) makeDemo();
}

function startData() {
  requestId++; clearTimeout(refreshTimer); clearInterval(demoTimer); data=[]; feeds=[]; lastUpdate=null; nextRefresh=null;
  scheduleTurning();
  $('#empty h2').textContent = 'Connecting to the runway'; $('#empty p').textContent = 'Fetching the latest airport information…';
  if (config.demo) { makeDemo(); demoTimer=setInterval(tickDemo, 6500); } else fetchLive();
  renderBoard(); updateStatus();
}
function updateStatus() {
  if (!config) return;
  const staleAfter = Math.max(180, config.refreshMinutes * 60) * 2;
  const stale = feeds.some(f=>f.error || f.fetchedAt && Date.now()/1000-f.fetchedAt>staleAfter);
  $('#status-dot').className = 'status-dot' + (config.demo ? ' demo' : stale ? ' stale' : '');
  $('#feed-status').textContent = config.demo ? 'DEMO / SIMULATED' : stale ? 'STALE / RETRYING' : !lastUpdate ? 'CONNECTING' : 'LIVE FLIGHT DATA';
  // Keep simulated or stale data identifiable even with the settings drawer closed.
  $('#board-notice').hidden = !config.demo && !stale;
  $('#board-notice').textContent = config.demo ? 'DEMO · SIMULATED FLIGHTS' : stale ? 'STALE DATA · RETRYING' : '';
  if (config.demo) $('#update-status').textContent = 'Sample flights · flips every few seconds';
  else if (lastUpdate) {
    const age=Math.max(0,Math.floor((Date.now()-lastUpdate)/1000));
    $('#update-status').textContent = `Fetched ${age<60?age+'s':Math.floor(age/60)+'m'} ago${stale?' · live feed unavailable':` · ${config.refreshMinutes} min refresh${config.refreshMinutes<3?' · cached between live fetches':''}`}`;
  } else $('#update-status').textContent = stale?'Feed unavailable · retrying automatically':'Fetching airport information';
  $('#update-status').title = feeds.map(f => `${f.airport}: provider updated ${f.sourceUpdatedAt || 'unknown'}${f.error ? ' · '+f.error:''}`).join('\n');
}
function updateClock() {
  if (!config) return;
  const now=new Date(); const timezone=zone();
  $('#clock-time').textContent=new Intl.DateTimeFormat('en-GB',{hour:'2-digit',minute:'2-digit',second:'2-digit',timeZone:timezone}).format(now);
  $('#clock-date').textContent=new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',timeZone:timezone}).format(now).toUpperCase()+' / '+new Intl.DateTimeFormat('en-GB',{timeZoneName:'short',timeZone:timezone}).formatToParts(now).find(p=>p.type==='timeZoneName').value;
}

function selectedAirports() {
  $('#selected-airports').replaceChildren(); $('#selected-count').textContent=config.airports.length+' SELECTED';
  config.airports.forEach(code=>{
    const b=document.createElement('button'); b.type='button'; b.className='chip'; b.textContent=code;
    const x=document.createElement('span'); x.textContent='×'; b.append(x); b.setAttribute('aria-label','Remove '+code); b.disabled=config.airports.length===1;
    b.onclick=()=>{config.airports=config.airports.filter(c=>c!==code); changedAirports();};
    $('#selected-airports').append(b);
  });
  searchAirports();
}
function changedAirports(){draftDirty=true;selectedAirports();applyConfig();startData();}
function searchAirports() {
  const term=$('#airport-search').value.trim().toUpperCase(); $('#airport-results').replaceChildren();
  let matches=airports.filter(a=>!config.airports.includes(a.code) && (term ? clean(a.name).includes(clean(term))||a.code.includes(term):a.live));
  matches.sort((a,b)=>(b.code===term)-(a.code===term)||Number(b.live)-Number(a.live)||a.name.localeCompare(b.name));
  matches.slice(0,30).forEach(a=>{
    const b=document.createElement('button'); b.type='button';b.className='airport-result';b.disabled=!a.live||config.airports.length>=12;
    const code=document.createElement('b');code.textContent=a.code;const name=document.createElement('span');name.textContent=a.name;
    const info=document.createElement('small');info.textContent=a.live?'FREE LIVE +':'NO FREE FEED YET';b.append(code,name,info);
    b.onclick=()=>{config.airports.push(a.code);$('#airport-search').value='';changedAirports();};$('#airport-results').append(b);
  });
  if (!matches.length){const p=document.createElement('p');p.className='hint';p.textContent='No matching airports.';$('#airport-results').append(p);}
}
const timingFields = [['screensaverMinutes','screensaver-minutes'], ['lockMinutes','lock-minutes'], ['screenOffMinutes','screen-off-minutes']];
let integrationStatus = {active: false, configured: false};
function showIntegrationStatus(status) {
  integrationStatus = status;
  $('#integration-status').textContent = status.active ? 'Automatic screensaver enabled.' : 'Automatic screensaver is not enabled.';
  $('#enable-integration').hidden = status.active;
  $('#enable-integration').disabled = false;
  $('#restore-integration').hidden = !status.configured;
  updateTimingControls();
}
async function refreshIntegrationStatus() {
  try {
    const response = await fetch('/api/integration');
    const status = await response.json();
    if (!response.ok) throw new Error(status.error);
    showIntegrationStatus(status);
  } catch (error) { $('#integration-status').textContent = error.message; }
}
async function changeIntegration(action) {
  const buttons = [$('#enable-integration'), $('#restore-integration')];
  buttons.forEach(button => button.disabled = true);
  $('#integration-status').textContent = action === 'enable' ? 'Enabling screensaver and checking the lock service…' : 'Restoring previous setup…';
  try {
    if (action === 'enable') {
      const error = timingError(config);
      if (error) throw new Error(error);
      const savedResponse = await fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(config)});
      if (!savedResponse.ok) throw new Error((await savedResponse.json()).error);
      saved = structuredClone(config); draftDirty = false;
    }
    const response = await fetch('/api/integration', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action})});
    const status = await response.json();
    if (!response.ok) throw new Error(status.error);
    showIntegrationStatus(status);
  } catch (error) { $('#integration-status').textContent = error.message; }
  finally { buttons.forEach(button => button.disabled = false); }
}
function updateTimingControls() {
  const error = timingError(config);
  timingFields.forEach(([,id]) => $('#'+id).setCustomValidity(error));
  $('#timing-error').textContent=error; $('#timing-error').hidden=!error;
  $('#timing-summary').textContent=error ? '' : `${integrationStatus.active ? '' : 'When enabled: '}board visible from minute ${config.screensaverMinutes} to ${config.screenOffMinutes}. Lock at minute ${config.lockMinutes}.`;
}

function openSettings() {
  saved=structuredClone(config);draftDirty=false;
  ['background','grid','letters','mode','timezone'].forEach(key=>$('#'+key).value=config[key]);
  $('#row-count').value=config.rows;$('#row-value').textContent=config.rows;$('#demo').checked=config.demo;
  $('#refresh-minutes').value=String(config.refreshMinutes);
  $('#constant-turning').checked=config.constantTurning;
  timingFields.forEach(([key,id]) => $('#'+id).value=config[key]);
  updateTimingControls();
  $('#save-message').textContent='Preferences are saved on this computer.';
  selectedAirports();$('#settings-dialog').showModal();
  refreshIntegrationStatus();
}
function closeSettings() {
  if(draftDirty){config=saved;applyConfig();startData();}
  $('#settings-dialog').close();$('#settings').focus();
}
function toast(text){$('#toast').textContent=text;$('#toast').hidden=false;setTimeout(()=>$('#toast').hidden=true,3000);}
function native(action){if(window.webkit?.messageHandlers?.native){window.webkit.messageHandlers.native.postMessage(action);return true;}return false;}
function fullscreen(){if(native('fullscreen'))return;if(document.fullscreenElement)document.exitFullscreen();else document.documentElement.requestFullscreen().catch(()=>toast('Use your window’s fullscreen command.'));}

async function init() {
  try {
    const responses=await Promise.all([fetch('/api/settings'),fetch('/api/airports')]);
    if(responses.some(r=>!r.ok))throw new Error('Setup unavailable');
    [config,airports]=await Promise.all(responses.map(r=>r.json()));
    config.refreshMinutes ??= 3;
    config.constantTurning ??= false;
    config.screensaverMinutes ??= 5; config.lockMinutes ??= 7; config.screenOffMinutes ??= 20;
    applyConfig(true);startData();console.info('Split-Flap: board and settings ready.');
  } catch(error) {$('#empty h2').textContent='Unable to open the board';$('#empty p').textContent='The local service is unavailable. Close and reopen Split-Flap Board.';return;}
  $('#settings').onclick=openSettings;$('#close-settings').onclick=closeSettings;
  $('#settings-dialog').addEventListener('cancel',e=>{e.preventDefault();closeSettings();});
  $('#airport-search').addEventListener('input',searchAirports);
  $('#row-count').addEventListener('input',e=>{config.rows=Number(e.target.value);$('#row-value').textContent=config.rows;draftDirty=true;applyConfig();});
  $('#refresh-minutes').addEventListener('change',e=>{config.refreshMinutes=Number(e.target.value);draftDirty=true;scheduleRefresh();updateStatus();});
  timingFields.forEach(([key,id]) => $('#'+id).addEventListener('input', e=>{config[key]=Number(e.target.value);draftDirty=true;updateTimingControls();}));
  $('#lock-appearance').hidden=!window.webkit?.messageHandlers?.native;
  $('#lock-appearance').onclick=()=>native('lock-appearance');
  $('#enable-integration').onclick=()=>changeIntegration('enable');
  $('#restore-integration').onclick=()=>changeIntegration('restore');
  $('#constant-turning').addEventListener('change',e=>{config.constantTurning=e.target.checked;draftDirty=true;scheduleTurning();});
  ['background','grid','letters','mode','timezone'].forEach(key=>$('#'+key).addEventListener('input',e=>{config[key]=e.target.value;draftDirty=true;applyConfig();}));
  $('#demo').addEventListener('change',e=>{config.demo=e.target.checked;draftDirty=true;applyConfig();startData();});
  document.querySelectorAll('[data-preset]').forEach(b=>b.onclick=()=>{
    const palette={classic:['#10120f','#282b25','#efc477'],ivory:['#131515','#282d2d','#eeeee4'],mint:['#0c1613','#20342b','#b7e6c2']}[b.dataset.preset];
    ['background','grid','letters'].forEach((key,i)=>{config[key]=palette[i];$('#'+key).value=palette[i];});draftDirty=true;applyConfig();
  });
  $('#settings-form').addEventListener('submit',async e=>{
    e.preventDefault();updateTimingControls();if(timingError(config))return;const button=e.submitter;button.disabled=true;
    try{const response=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(config)});
      if(!response.ok)throw new Error((await response.json()).error||'Could not save');
      saved=structuredClone(config);draftDirty=false;$('#settings-dialog').close();toast('Board settings saved');
    }catch(error){$('#save-message').textContent=error.message;}finally{button.disabled=false;}
  });
  $('#animate').onclick=()=>renderBoard(true);$('#fullscreen').onclick=fullscreen;
  document.addEventListener('keydown',e=>{if(!screenMode&&!$('#settings-dialog').open&&!['INPUT','SELECT'].includes(e.target.tagName)){if(e.key.toLowerCase()==='f')fullscreen();if(e.key.toLowerCase()==='s')openSettings();if(e.key==='Escape'){if(!native('leave-fullscreen')&&document.fullscreenElement)document.exitFullscreen();}}});
  if(params.has('settings')&&!screenMode)openSettings();
  if(screenMode){
    document.body.classList.add('screensaver'); const start=performance.now();let pointer;
    const dismiss=()=>{if(performance.now()-start<1800||dismissed)return;dismissed=true;if(!native('dismiss')){document.body.classList.remove('screensaver');screenMode=false;toast('Screensaver preview ended');}};
    document.addEventListener('keydown',dismiss);document.addEventListener('pointerdown',dismiss);document.addEventListener('wheel',dismiss);
    document.addEventListener('pointermove',e=>{if(!pointer){pointer=[e.clientX,e.clientY];return;}if(Math.hypot(e.clientX-pointer[0],e.clientY-pointer[1])>12)dismiss();});
  }
  setInterval(()=>{updateClock();updateStatus();},1000);
  setInterval(()=>renderBoard(),15000);
}
new ResizeObserver(fitBoard).observe($('#rows'));
document.fonts.ready.then(fitBoard);
init();
