// Aegis Drone Command — Shared Shell
const PAGES = [
  { label: 'Live Feed', href: '/' },
  { label: 'Video Analysis', href: '/static/video.html' },
  { label: 'Alerts', href: '/static/alerts.html' },
  { label: 'Query Frames', href: '/static/query.html' },
  { label: 'Daily Summary', href: '/static/summary.html' },
];
const SIDEBAR_LINKS = [
  { icon: 'precision_manufacturing', label: 'Systems', id: 'systems' },
  { icon: 'airplanemode_active', label: 'Drones', id: 'drones' },
  { icon: 'settings_input_component', label: 'Telemetry', id: 'telemetry', active: true },
  { icon: 'view_in_ar', label: 'Payload', id: 'payload' },
  { icon: 'admin_panel_settings', label: 'Security', id: 'security' },
];

// Panel content for each sidebar item
const PANEL_DATA = {
  systems: {
    title: 'SYSTEM STATUS',
    icon: 'precision_manufacturing',
    rows: [
      { label: 'Core Engine', val: 'ONLINE', color: 'secondary-fixed-dim' },
      { label: 'GPU Cluster', val: 'ACTIVE', color: 'secondary-fixed-dim' },
      { label: 'Neural Net v4.2', val: 'LOADED', color: 'secondary-fixed-dim' },
      { label: 'Memory Usage', val: '67%', color: 'primary' },
      { label: 'CPU Load', val: '42%', color: 'primary' },
      { label: 'Uptime', val: '14d 07h 33m', color: 'on-surface' },
      { label: 'Last Reboot', val: '2026-04-28', color: 'outline' },
      { label: 'Firmware', val: 'v8.1.4-mil', color: 'outline' },
    ]
  },
  drones: {
    title: 'DRONE FLEET',
    icon: 'airplanemode_active',
    rows: [
      { label: 'Unit-01 (Alpha)', val: 'PATROL', color: 'secondary-fixed-dim' },
      { label: 'Unit-02 (Alpha)', val: 'PATROL', color: 'secondary-fixed-dim' },
      { label: 'Unit-03 (Bravo)', val: 'STANDBY', color: 'primary' },
      { label: 'Unit-04 (Delta)', val: 'ENGAGED', color: 'error' },
      { label: 'Unit-07 (Delta)', val: 'ACTIVE', color: 'secondary-fixed-dim' },
      { label: 'Unit-09 (Charlie)', val: 'CHARGING', color: 'tertiary' },
      { label: 'Unit-12 (Bravo)', val: 'MAINTENANCE', color: 'tertiary' },
      { label: 'Unit-15 (Alpha)', val: 'PATROL', color: 'secondary-fixed-dim' },
    ]
  },
  telemetry: {
    title: 'TELEMETRY FEED',
    icon: 'settings_input_component',
    rows: [
      { label: 'Altitude', val: '120m AGL', color: 'secondary-fixed-dim' },
      { label: 'Ground Speed', val: '14.2 m/s', color: 'on-surface' },
      { label: 'Heading', val: '247° WSW', color: 'on-surface' },
      { label: 'Battery', val: '78%', color: 'secondary-fixed-dim' },
      { label: 'Signal Strength', val: '-42 dBm', color: 'secondary-fixed-dim' },
      { label: 'GPS Satellites', val: '14 locked', color: 'on-surface' },
      { label: 'Wind Speed', val: '8.3 kts NE', color: 'primary' },
      { label: 'Temperature', val: '22.4°C', color: 'outline' },
    ]
  },
  payload: {
    title: 'PAYLOAD STATUS',
    icon: 'view_in_ar',
    rows: [
      { label: 'Camera (RGB)', val: 'ACTIVE', color: 'secondary-fixed-dim' },
      { label: 'Camera (IR)', val: 'STANDBY', color: 'primary' },
      { label: 'LIDAR Module', val: 'SCANNING', color: 'secondary-fixed-dim' },
      { label: 'Spotlight', val: 'OFF', color: 'outline' },
      { label: 'Speaker Array', val: 'ARMED', color: 'tertiary' },
      { label: 'Gas Sensor', val: 'NOMINAL', color: 'secondary-fixed-dim' },
      { label: 'Storage Used', val: '34.2 GB', color: 'on-surface' },
      { label: 'Transmission', val: 'ENCRYPTED', color: 'secondary-fixed-dim' },
    ]
  },
  security: {
    title: 'SECURITY CONFIG',
    icon: 'admin_panel_settings',
    rows: [
      { label: 'Auth Level', val: 'LEVEL 4', color: 'secondary-fixed-dim' },
      { label: 'Encryption', val: 'AES-256', color: 'secondary-fixed-dim' },
      { label: 'Firewall', val: 'ACTIVE', color: 'secondary-fixed-dim' },
      { label: 'IDS Status', val: 'MONITORING', color: 'secondary-fixed-dim' },
      { label: 'Last Breach', val: 'NONE', color: 'outline' },
      { label: 'Perimeter', val: 'SECURED', color: 'secondary-fixed-dim' },
      { label: 'Access Tokens', val: '3 active', color: 'on-surface' },
      { label: 'Audit Log', val: '1,247 entries', color: 'outline' },
    ]
  },
  logs: {
    title: 'SYSTEM LOGS',
    icon: 'list_alt',
    rows: [
      { label: '20:14:22', val: 'SYS_BOOT complete', color: 'secondary-fixed-dim' },
      { label: '20:14:25', val: 'Network link established', color: 'secondary-fixed-dim' },
      { label: '20:15:01', val: 'Auth token refreshed', color: 'on-surface' },
      { label: '20:15:44', val: 'Drone fleet sync OK', color: 'secondary-fixed-dim' },
      { label: '20:16:12', val: 'Patrol route loaded', color: 'on-surface' },
      { label: '20:18:03', val: 'Sensor calibration done', color: 'on-surface' },
      { label: '20:19:30', val: 'Operator login: Unit 07', color: 'primary' },
      { label: '20:20:00', val: 'System nominal', color: 'secondary-fixed-dim' },
    ]
  },
  terminal: {
    title: 'TERMINAL',
    icon: 'terminal',
    rows: [
      { label: '$', val: 'aegis status --all', color: 'secondary-fixed-dim' },
      { label: '>', val: 'All subsystems operational', color: 'on-surface' },
      { label: '$', val: 'drone list --active', color: 'secondary-fixed-dim' },
      { label: '>', val: '7 units online, 1 maintenance', color: 'on-surface' },
      { label: '$', val: 'alert count --today', color: 'secondary-fixed-dim' },
      { label: '>', val: '3 alerts (0 critical)', color: 'on-surface' },
      { label: '$', val: 'uptime', color: 'secondary-fixed-dim' },
      { label: '>', val: '14 days, 7 hours, 33 minutes', color: 'on-surface' },
    ]
  },
  settings: {
    title: 'SETTINGS',
    icon: 'settings',
    rows: [
      { label: 'Theme', val: 'DARK MODE', color: 'on-surface' },
      { label: 'Language', val: 'ENGLISH', color: 'on-surface' },
      { label: 'Notifications', val: 'ENABLED', color: 'secondary-fixed-dim' },
      { label: 'Sound Alerts', val: 'ON', color: 'secondary-fixed-dim' },
      { label: 'Auto-Refresh', val: '5 SEC', color: 'on-surface' },
      { label: 'Map Overlay', val: 'TACTICAL', color: 'on-surface' },
      { label: 'Data Retention', val: '90 DAYS', color: 'outline' },
      { label: 'API Version', val: 'v2.4.1', color: 'outline' },
    ]
  },
};

let activePanelId = null;

function isActive(href) {
  const p = window.location.pathname;
  if (href === '/') return p === '/' || p === '/static/index.html';
  return p === href;
}

function openPanel(id) {
  const wasOpen = activePanelId === id;
  closePanel();
  if (wasOpen) return;
  activePanelId = id;
  updateSidebarHighlight(id);
  const data = PANEL_DATA[id];
  if (!data) return;
  const overlay = document.createElement('div');
  overlay.id = 'aegis-panel-overlay';
  overlay.className = 'fixed inset-0 bg-black/40 z-[55]';
  overlay.onclick = () => closePanel();
  document.body.appendChild(overlay);

  const panel = document.createElement('div');
  panel.id = 'aegis-panel';
  panel.className = 'fixed top-16 left-60 w-80 bg-surface-container-high border-2 border-surface-dim shadow-[0_10px_40px_rgba(0,0,0,0.9)] z-[60] flex flex-col overflow-hidden';
  panel.style.maxHeight = 'calc(100vh - 5rem)';
  panel.style.animation = 'panelSlide .2s ease-out';

  let rowsHtml = data.rows.map(r =>
    `<div class="flex justify-between items-center py-2 px-4 border-b border-surface-dim/50 hover:bg-surface-container transition-colors">
      <span class="font-display-code text-[12px] text-on-surface-variant">${r.label}</span>
      <span class="font-label-caps text-[11px] text-${r.color}">${r.val}</span>
    </div>`
  ).join('');

  panel.innerHTML = `
    <div class="bg-surface-container-highest px-4 py-3 border-b-2 border-surface-dim flex justify-between items-center">
      <div class="flex items-center gap-2">
        <span class="material-symbols-outlined text-secondary-fixed-dim text-[18px]" style="font-variation-settings:'FILL' 1">${data.icon}</span>
        <span class="font-label-caps text-[12px] text-on-surface uppercase tracking-widest">${data.title}</span>
      </div>
      <button onclick="closePanel()" class="text-outline hover:text-on-surface p-1 rounded hover:bg-surface-bright transition-colors">
        <span class="material-symbols-outlined text-[16px]">close</span>
      </button>
    </div>
    <div class="flex-1 overflow-y-auto">${rowsHtml}</div>
    <div class="bg-surface-dim px-4 py-2 border-t border-surface-container flex items-center justify-between">
      <div class="flex items-center gap-1.5">
        <div class="w-2 h-2 rounded-full bg-secondary-fixed-dim shadow-[0_0_6px_#00e639] animate-pulse"></div>
        <span class="font-display-code text-[10px] text-outline">LIVE DATA</span>
      </div>
      <span class="font-display-code text-[10px] text-outline">${new Date().toLocaleTimeString('en-US',{hour12:false})} UTC</span>
    </div>`;
  document.body.appendChild(panel);
}

function closePanel() {
  const p = document.getElementById('aegis-panel');
  const o = document.getElementById('aegis-panel-overlay');
  if (p) p.remove();
  if (o) o.remove();
  activePanelId = null;
  updateSidebarHighlight(null);
}

function updateSidebarHighlight(activeId) {
  const links = document.querySelectorAll('#aegis-sidebar nav a[data-panel]');
  links.forEach(a => {
    const id = a.getAttribute('data-panel');
    if (id === activeId) {
      a.className = 'flex items-center gap-3 px-3 py-2.5 rounded font-label-caps text-[12px] bg-surface-container-highest text-secondary-fixed shadow-[inset_0_2px_4px_rgba(0,0,0,0.8)] border-l-4 border-secondary-fixed uppercase';
      a.querySelector('.material-symbols-outlined').style.fontVariationSettings = "'FILL' 1";
    } else {
      a.className = 'flex items-center gap-3 px-3 py-2.5 rounded font-label-caps text-[12px] text-outline hover:text-on-surface-variant hover:bg-surface-container-high transition-all active:scale-95 uppercase';
      a.querySelector('.material-symbols-outlined').style.fontVariationSettings = "'FILL' 0";
    }
  });
}

function emergencyStop(el) {
  const btn = el ? el.closest('button') : (window.event ? window.event.target.closest('button') : null);
  if (!btn || btn.dataset.stopping) return;
  btn.dataset.stopping = '1';
  btn.classList.add('translate-y-[3px]');
  btn.innerHTML = `<span class="material-symbols-outlined text-[16px] animate-spin" style="font-variation-settings:'FILL' 1">sync</span>HALTING...`;

  // Call the backend halt endpoint
  fetch('/api/halt', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      // Also reset simulation state
      return fetch('/api/reset', { method: 'POST' });
    })
    .then(r => r.json())
    .then(() => {
      btn.innerHTML = `<span class="material-symbols-outlined text-[16px]" style="font-variation-settings:'FILL' 1">check_circle</span>ALL HALTED`;
      btn.classList.remove('bg-error'); btn.classList.add('bg-secondary-fixed-dim','text-black');

      // Dispatch a global halt event so pages can clean up their EventSource / state
      window.dispatchEvent(new CustomEvent('aegis-halt'));

      setTimeout(() => {
        btn.classList.remove('translate-y-[3px]','bg-secondary-fixed-dim','text-black');
        btn.classList.add('bg-error');
        btn.innerHTML = `<span class="material-symbols-outlined text-[16px]" style="font-variation-settings:'FILL' 1">warning</span>EMERGENCY STOP`;
        delete btn.dataset.stopping;
      }, 2500);
    })
    .catch(err => {
      btn.innerHTML = `<span class="material-symbols-outlined text-[16px]" style="font-variation-settings:'FILL' 1">error</span>HALT FAILED`;
      setTimeout(() => {
        btn.classList.remove('translate-y-[3px]');
        btn.innerHTML = `<span class="material-symbols-outlined text-[16px]" style="font-variation-settings:'FILL' 1">warning</span>EMERGENCY STOP`;
        delete btn.dataset.stopping;
      }, 2000);
    });
}

function buildTopNav() {
  const nav = document.createElement('header');
  nav.id = 'aegis-topnav';
  nav.className = 'bg-surface-container-highest fixed w-full top-0 border-b-4 border-surface-dim shadow-[0_4px_10px_rgba(0,0,0,0.8)] flex justify-between items-center px-6 h-16 z-50';
  const brand = document.createElement('div');
  brand.className = 'flex items-center gap-3 shrink-0';
  brand.innerHTML = `<span class="material-symbols-outlined text-secondary-fixed-dim text-[22px]" style="font-variation-settings:'FILL' 1">security</span>
    <span class="font-headline-lg text-on-surface uppercase tracking-widest text-[20px]">Aegis Drone Command</span>`;
  const tabs = document.createElement('nav');
  tabs.className = 'hidden md:flex items-center h-full gap-1 ml-8';
  PAGES.forEach(p => {
    const a = document.createElement('a');
    a.href = p.href;
    a.textContent = p.label;
    a.className = isActive(p.href)
      ? 'h-full flex items-center px-4 text-secondary-fixed-dim border-b-2 border-secondary-fixed-dim font-bold shadow-[0_0_12px_rgba(0,230,57,0.3)] bg-surface-container/50 font-label-caps text-[13px] uppercase tracking-wider'
      : 'h-full flex items-center px-4 text-on-surface-variant hover:bg-surface-bright hover:text-on-surface transition-colors font-label-caps text-[13px] uppercase tracking-wider';
    tabs.appendChild(a);
  });
  const right = document.createElement('div');
  right.className = 'flex items-center gap-2 shrink-0';
  right.innerHTML = `<button onclick="openPanel('settings')" class="p-2 hover:bg-surface-bright rounded transition-colors text-primary"><span class="material-symbols-outlined text-[20px]">settings</span></button>
    <button onclick="emergencyStop(this)" class="p-2 hover:bg-surface-bright rounded transition-colors text-error"><span class="material-symbols-outlined text-[20px]">power_settings_new</span></button>`;
  nav.appendChild(brand); nav.appendChild(tabs); nav.appendChild(right);
  return nav;
}

function buildSidebar() {
  const aside = document.createElement('aside');
  aside.id = 'aegis-sidebar';
  aside.className = 'bg-surface-container-low fixed left-0 h-full w-60 border-r-4 border-surface-dim shadow-[10px_0_20px_rgba(0,0,0,0.5)] flex flex-col pt-16 pb-4 z-40';
  const profile = document.createElement('div');
  profile.className = 'px-5 py-5 border-b border-surface-variant flex items-center gap-3';
  profile.innerHTML = `<div class="w-10 h-10 rounded bg-surface-container-highest border border-surface-variant flex items-center justify-center shadow-[inset_0_2px_4px_rgba(0,0,0,0.5)]">
      <span class="material-symbols-outlined text-outline text-[20px]">person</span></div>
    <div><div class="font-headline-md text-[16px] text-on-surface leading-none uppercase">Unit 07</div>
    <div class="font-label-caps text-[10px] text-on-surface-variant mt-1">Sector Delta</div></div>`;
  aside.appendChild(profile);
  const navCont = document.createElement('nav');
  navCont.className = 'flex-1 py-4 flex flex-col gap-1 px-3 overflow-y-auto';
  SIDEBAR_LINKS.forEach(l => {
    const a = document.createElement('a');
    a.href = '#'; a.setAttribute('data-panel', l.id);
    a.onclick = (e) => { e.preventDefault(); openPanel(l.id); };
    a.className = 'flex items-center gap-3 px-3 py-2.5 rounded font-label-caps text-[12px] text-outline hover:text-on-surface-variant hover:bg-surface-container-high transition-all active:scale-95 uppercase';
    a.innerHTML = `<span class="material-symbols-outlined text-[18px]">${l.icon}</span>${l.label}`;
    navCont.appendChild(a);
  });
  aside.appendChild(navCont);
  const footer = document.createElement('div');
  footer.className = 'mt-auto px-3 flex flex-col gap-2';
  footer.innerHTML = `<button onclick="emergencyStop(this)" class="w-full py-2.5 bg-error text-on-error font-label-caps text-[12px] uppercase rounded shadow-[0_3px_0_#93000a] active:shadow-none active:translate-y-[3px] border border-red-400/30 flex items-center justify-center gap-2 transition-all">
      <span class="material-symbols-outlined text-[16px]" style="font-variation-settings:'FILL' 1">warning</span>EMERGENCY STOP</button>
    <div class="h-px bg-surface-container-highest my-1"></div>
    <div class="flex gap-1">
      <a href="#" onclick="event.preventDefault();openPanel('logs')" class="flex items-center gap-2 px-3 py-2 rounded font-label-caps text-[11px] text-outline hover:text-on-surface-variant hover:bg-surface-container-high flex-1"><span class="material-symbols-outlined text-[16px]">list_alt</span>Logs</a>
      <a href="#" onclick="event.preventDefault();openPanel('terminal')" class="flex items-center gap-2 px-3 py-2 rounded font-label-caps text-[11px] text-outline hover:text-on-surface-variant hover:bg-surface-container-high flex-1"><span class="material-symbols-outlined text-[16px]">terminal</span>Terminal</a>
    </div>`;
  aside.appendChild(footer);
  return aside;
}

// CSS animation
function injectStyles() {
  if (document.getElementById('aegis-shell-styles')) return;
  const s = document.createElement('style');
  s.id = 'aegis-shell-styles';
  s.textContent = `@keyframes panelSlide{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:translateY(0)}}`;
  document.head.appendChild(s);
}

function injectShell() {
  document.querySelectorAll('#aegis-topnav, #aegis-sidebar, #aegis-panel, #aegis-panel-overlay').forEach(e => e.remove());
  injectStyles();
  document.body.prepend(buildSidebar());
  document.body.prepend(buildTopNav());
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', injectShell);
else injectShell();
