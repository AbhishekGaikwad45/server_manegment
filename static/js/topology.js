const COLOR_MAP = {
  up: { fill: '#f0fdf4', stroke: '#16a34a', text: '#15803d' },
  down: { fill: '#fef2f2', stroke: '#dc2626', text: '#dc2626' },
  warning: { fill: '#fffbeb', stroke: '#d97706', text: '#b45309' },
  unknown: { fill: '#f9fafb', stroke: '#c0bdb8', text: '#6b7280' },
};
const SVG_NS = 'http://www.w3.org/2000/svg';
const NODE_W = 140, NODE_H = 38, COL_GAP = 24, ROW_GAP = 80, GRP_GAP = 48;
const CHILDREN_PER_ROW = 3;

function svgEl(tag, attrs, parent) {
  const e = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

function drawTopology(servers) {
  const svg = document.getElementById('topo-svg');
  const tooltip = document.getElementById('topo-tooltip');
  if (!svg) return;
  svg.innerHTML = '';
  if (!servers || !servers.length) return;

  const defs = svgEl('defs', {}, svg);
  defs.innerHTML = `
    <marker id="arr-norm" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#c0bdb8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker>
    <marker id="arr-red" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#dc2626" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker>`;

  const parents = servers.filter(s => !s.parent_id);
  const childMap = {};
  servers.forEach(s => {
    if (s.parent_id) {
      if (!childMap[s.parent_id]) childMap[s.parent_id] = [];
      childMap[s.parent_id].push(s);
    }
  });

  const pos = {};

  function setPosition(node, x, y) {

    pos[node.id] = { x, y };

    const children = childMap[node.id] || [];

    if (!children.length) return;

    const levelGapX = 260;
    const levelGapY = 150;

    const totalWidth =
      (children.length - 1) * levelGapX;

    let startX = x - totalWidth / 2;

    children.forEach((child, index) => {

      const childX =
        startX + (index * levelGapX);

      const childY =
        y + levelGapY;

      // recursive
      setPosition(child, childX, childY);

    });

  }

  // ROOTS
  parents.forEach((p, index) => {

    setPosition(
      p,
      300 + (index * 900),
      100
    );

  });

  const allX = Object.values(pos).map(p => p.x);
  const allY = Object.values(pos).map(p => p.y);

  const minX = Math.min(...allX);

  const maxX = Math.max(...allX);

  const minY = Math.min(...allY);

  const maxY = Math.max(...allY);

  const PADDING = 400;

  const SVG_W =
    (maxX - minX) + PADDING * 2;

  const SVG_H =
    (maxY - minY) + PADDING * 2;

  svg.setAttribute(
    'viewBox',

    `${minX - PADDING}
   ${minY - PADDING}
   ${SVG_W}
   ${SVG_H}`
  );

  svg.setAttribute('width', SVG_W);

  svg.setAttribute('height', SVG_H);


  // edges
  // edges
  servers.forEach(s => {

    if (!s.parent_id || !pos[s.id] || !pos[s.parent_id]) return;

    const from = pos[s.parent_id];
    const to = pos[s.id];

    const parent = servers.find(x => x.id === s.parent_id);

    const isDown =
      parent &&
      (parent.status === 'down' || s.status === 'down');

    const isWarning =
      parent &&
      (parent.status === 'warning' || s.status === 'warning');

    let strokeColor = '#16a34a';
    let marker = 'url(#arr-norm)';

    if (isDown) {
      strokeColor = '#dc2626';
      marker = 'url(#arr-red)';
    }
    else if (isWarning) {
      strokeColor = '#d97706';
    }

    const x1 = from.x;
    const y1 = from.y + NODE_H / 2;

    const x2 = to.x;
    const y2 = to.y - NODE_H / 2;

    const cy = (y1 + y2) / 2;

    const path = svgEl('path', {

      d: `M${x1},${y1} C${x1},${cy} ${x2},${cy} ${x2},${y2}`,

      fill: 'none',

      stroke: strokeColor,

      'stroke-width': isDown ? '2' : '1.5',

      'stroke-dasharray': '6 4',

      'marker-end': marker,

      opacity: '0.95'

    }, svg);

    const anim = document.createElementNS(
      SVG_NS,
      'animate'
    );

    anim.setAttribute(
      'attributeName',
      'stroke-dashoffset'
    );

    anim.setAttribute('from', '0');

    anim.setAttribute('to', '-20');

    anim.setAttribute(
      'dur',
      isDown ? '0.7s' : '1.4s'
    );

    anim.setAttribute(
      'repeatCount',
      'indefinite'
    );

    path.appendChild(anim);

  });

  // nodes
  servers.forEach(s => {
    const p = pos[s.id];
    if (!p) return;
    const status = s.status || 'unknown';
    const c = COLOR_MAP[status] || COLOR_MAP.unknown;
    const isParent = !s.parent_id;
    const g = svgEl('g', { cursor: 'pointer' }, svg);
    const rx0 = p.x - NODE_W / 2, ry0 = p.y - NODE_H / 2;

    svgEl('rect', {
      x: rx0, y: ry0, width: NODE_W, height: NODE_H, rx: isParent ? 10 : 7,
      fill: c.fill, stroke: c.stroke, 'stroke-width': isParent ? '2' : '0.8'
    }, g);

    if (status === 'down') {
      const pl = svgEl('rect', {
        x: rx0 - 2, y: ry0 - 2, width: NODE_W + 4, height: NODE_H + 4,
        rx: isParent ? 12 : 9, fill: 'none', stroke: '#dc2626', 'stroke-width': '2', opacity: '0'
      }, g);
      const a = document.createElementNS(SVG_NS, 'animate');
      a.setAttribute('attributeName', 'opacity'); a.setAttribute('values', '0;0.7;0');
      a.setAttribute('dur', '1.2s'); a.setAttribute('repeatCount', 'indefinite');
      pl.appendChild(a);
    }

    const dotC = status === 'up' ? '#16a34a' : status === 'down' ? '#dc2626' : status === 'warning' ? '#d97706' : '#9ca3af';
    svgEl('circle', { cx: rx0 + NODE_W - 10, cy: ry0 + 10, r: 5, fill: dotC }, g);

    const raw = s.name || 'Server';
    const label = raw.length > 17 ? raw.slice(0, 16) + '…' : raw;
    const txt = svgEl('text', {
      x: p.x - 4, y: p.y + 1,
      'text-anchor': 'middle', 'dominant-baseline': 'central',
      'font-size': isParent ? '12' : '11',
      'font-weight': isParent ? '600' : '400',
      'font-family': '-apple-system,BlinkMacSystemFont,sans-serif',
      fill: c.text
    }, g);
    txt.textContent = label;

    const parentSrv = s.parent_id ? servers.find(x => x.id === s.parent_id) : null;
    g.addEventListener('mouseenter', () => {
      const statusText =
        status === 'up'
          ? 'ONLINE'
          : status === 'down'
            ? 'OFFLINE'
            : status === 'warning'
              ? 'WARNING'
              : 'UNKNOWN';

      const statusClass =
        status === 'up'
          ? 'tooltip-online'
          : status === 'down'
            ? 'tooltip-offline'
            : status === 'warning'
              ? 'tooltip-warning'
              : 'tooltip-unknown';

      tooltip.innerHTML = `

<div class="tooltip-card">

  <div class="tooltip-header">

    <div class="tooltip-server-name">
      ${s.name}
    </div>

    <div class="tooltip-status ${statusClass}">
      <span class="pulse-dot"></span>
      ${statusText}
    </div>

  </div>

  <div class="tooltip-grid">

    <div class="tooltip-item">
      <span class="tooltip-label">IP</span>
      <span class="tooltip-value">${s.ip || '—'}</span>
    </div>

    <div class="tooltip-item">
      <span class="tooltip-label">Ping</span>
      <span class="tooltip-value">
        ${s.ping_ms ? s.ping_ms + 'ms' : 'timeout'}
      </span>
    </div>

    <div class="tooltip-item">
      <span class="tooltip-label">Type</span>
      <span class="tooltip-value">
        ${isParent ? 'Parent Server' : 'Child Server'}
      </span>
    </div>

    ${parentSrv
          ?
          `
      <div class="tooltip-item">
        <span class="tooltip-label">Parent</span>
        <span class="tooltip-value">${parentSrv.name}</span>
      </div>
      `
          :
          ''
        }

  </div>

</div>
`;
      tooltip.style.opacity = '1';
    });
    g.addEventListener('mousemove', ev => {
      const r = svg.getBoundingClientRect();
      const lx = ev.clientX - r.left, ly = ev.clientY - r.top;
      tooltip.style.left = (lx > r.width * 0.65 ? lx - 178 : lx + 14) + 'px';
      tooltip.style.top = (ly + 10) + 'px';
    });
    g.addEventListener('mouseleave', () => { tooltip.style.opacity = '0'; });
    g.addEventListener('click', () => { if (typeof pingServer === 'function') pingServer(s.id, s.name); });
  });
}
let currentScale = 1;

const wrapper = document.getElementById('topology-wrapper');

wrapper.addEventListener('wheel', (e) => {

    e.preventDefault();

    if (e.deltaY < 0) {
        currentScale += 0.1;
    } else {
        currentScale -= 0.1;
    }

    if (currentScale < 0.3) {
        currentScale = 0.3;
    }

    if (currentScale > 3) {
        currentScale = 3;
    }

    const svg = document.getElementById('topo-svg');

    svg.style.transform = `scale(${currentScale})`;

    svg.style.transformOrigin = 'top left';

});

let topologyScale = 1;

function applyZoom(){

    const svg = document.getElementById('topo-svg');

    svg.style.transform =
        `scale(${topologyScale})`;
}

function zoomIn(){

    topologyScale += 0.1;

    if(topologyScale > 2){
        topologyScale = 2;
    }

    applyZoom();
}

function zoomOut(){

    topologyScale -= 0.1;

    if(topologyScale < 0.5){
        topologyScale = 0.5;
    }

    applyZoom();
}

function resetZoom(){

    topologyScale = 1;

    applyZoom();
}
drawTopology(SERVER_DATA);