/* Grab & Go — store dashboard */
(function () {
  'use strict';
  const { icon, money, esc, timeAgo, get, post, toast, liveSocket } = window.GG;
  const $ = (id) => document.getElementById(id);
  const ONLINE_MS = 90 * 1000;
  let events = [], newIds = new Set();

  function badgeClass(kind) { return (kind || '').toLowerCase(); }

  function renderEvents() {
    if (!events.length) {
      $('events').innerHTML = '<div class="empty"><div class="tile">' + icon('video') + '</div><b>No events yet</b>Scans at the kiosk and shelf pick-ups show up here.</div>';
      return;
    }
    $('events').innerHTML = events.slice(0, 40).map(ev => {
      const action = ev.needs_action && !ev.resolved
        ? '<button class="btn" type="button" data-resolve="' + ev.id + '" style="min-height:36px;border-color:var(--warn);color:var(--warn)">' + (ev.kind === 'Help' ? 'Mark done' : 'Reviewed') + '</button>'
        : (ev.needs_action ? '<span class="muted" style="font-size:12.5px">Resolved</span>' : '');
      return '<div class="ev' + (newIds.has(ev.id) ? ' new' : '') + '">' +
        '<span class="badge ' + badgeClass(ev.kind) + '">' + esc(ev.kind) + '</span>' +
        '<div class="info"><div class="p">' + esc(ev.product) + '</div><div class="d">' + esc(ev.detail) + ' · ' + esc(ev.node) + '</div></div>' +
        action + '<span class="when" title="' + esc(new Date(ev.ts).toLocaleString('en-IN')) + '">' + timeAgo(ev.ts) + '</span></div>';
    }).join('');
    newIds.clear();
  }

  function render(d) {
    $('kOrders').textContent = d.orders_today;
    $('kItems').textContent = d.items_sold_today + ' item' + (d.items_sold_today === 1 ? '' : 's') + ' sold';
    $('kRevenue').textContent = money(d.revenue_today);
    $('kActions').textContent = d.open_actions;
    $('kActions').style.color = d.open_actions ? 'var(--warn)' : '';
    $('kActionsS').textContent = d.open_actions ? 'Help requests or detections to review' : 'All clear';

    const now = Date.now();
    const nodes = d.edge_nodes.map(n => ({ name: n.node_id, kind: 'Shelf camera · edge node',
      online: n.last_seen && now - new Date(n.last_seen).getTime() < ONLINE_MS,
      stats: (n.events || 0) + ' events · last ' + (n.last_seen ? timeAgo(n.last_seen) : 'never') }));
    const kiosks = d.kiosks.map((k, i) => ({ name: 'Kiosk camera ' + (i + 1), kind: 'Browser camera · ' + esc(k.client), online: true,
      stats: k.frames + ' frames analysed' + (k.last_ms != null ? ' · ' + k.last_ms + ' ms per frame' : '') }));
    const all = kiosks.concat(nodes);
    const online = all.filter(n => n.online).length;
    $('kDevices').textContent = online + ' / ' + all.length;
    $('kDevicesS').textContent = all.length ? (online === all.length ? 'All reporting' : (all.length - online) + ' not reporting') : 'Start the kiosk camera or an edge node';
    $('devices').innerHTML = all.length ? all.map(n =>
      '<div class="node"><div class="tile sm">' + icon(n.kind.startsWith('Shelf') ? 'video' : 'camera') + '</div>' +
      '<div style="flex:1;min-width:0"><div style="display:flex;justify-content:space-between;gap:8px"><b style="font-size:14.5px">' + esc(n.name) + '</b>' +
      '<span class="pill ' + (n.online ? 'ok' : 'off') + '" style="height:24px;font-size:12px;padding:0 9px">' + (n.online ? 'Online' : 'Offline') + '</span></div>' +
      '<div class="muted" style="font-size:13px">' + n.kind + '</div><div class="muted" style="font-size:13px">' + esc(n.stats) + '</div></div></div>').join('')
      : '<div class="empty" style="padding:28px 16px">No devices connected yet.<br>Open the kiosk and start the camera, or run <code>edge/edge_node.py</code>.</div>';

    const v = d.vision || {};
    const rows = [
      ['Mode', v.mode ? v.mode.split(' (')[0] : 'disabled'],
      ['Detector', v.yolo ? 'YOLOv8 · loaded' : 'not loaded'],
      ['Brand model', v.clip ? 'CLIP ViT-B/32 · loaded' : 'not loaded'],
      ['Barcode', v.barcode || 'unavailable'],
      ['Device', (v.device || '-').toUpperCase()]
    ];
    $('engine').innerHTML = rows.map(r => '<div class="r"><span>' + esc(r[0]) + '</span><span>' + esc(r[1]) + '</span></div>').join('') +
      (v.errors && Object.keys(v.errors).length ? '<div class="note" style="margin-top:10px;color:#8A3B07;background:var(--warn-tint);border-color:#FCE3C2">' + icon('alert') + esc(Object.keys(v.errors).join(', ') + ' could not be loaded') + '</div>' : '');

    $('orders').innerHTML = d.recent_orders.length ? d.recent_orders.map(o =>
      '<div class="node"><div class="tile sm">' + icon('receipt') + '</div><div style="flex:1;min-width:0">' +
      '<div style="display:flex;justify-content:space-between"><b style="font-size:14.5px">' + esc(o.order_id) + '</b><b class="money">' + money(o.grand_total) + '</b></div>' +
      '<div class="muted" style="font-size:13px">' + o.item_count + ' items · ' + esc((o.method || '').toUpperCase()) + ' · ' + timeAgo(o.timestamp) + '</div></div></div>').join('')
      : '<div class="empty" style="padding:28px 16px">No orders yet today.</div>';

    $('updated').textContent = 'Updated ' + new Date().toLocaleTimeString('en-IN');
  }

  async function refresh() {
    try {
      const [d, ev] = await Promise.all([get('/api/dashboard'), get('/api/events?limit=60')]);
      events = ev;
      render(d); renderEvents();
    } catch (e) {
      toast('Could not load dashboard', e.message, 'err');
    }
  }

  $('events').addEventListener('click', async (e) => {
    const b = e.target.closest('[data-resolve]');
    if (!b) return;
    b.disabled = true;
    try { await post('/api/events/' + b.dataset.resolve + '/resolve'); refresh(); }
    catch (err) { b.disabled = false; toast('Could not update', err.message, 'err'); }
  });
  $('refreshBtn').addEventListener('click', refresh);

  let pending = 0;
  liveSocket((msg) => {
    if (msg.type === 'event') {
      events.unshift(msg.event); newIds.add(msg.event.id); renderEvents();
      if (msg.event.kind === 'Help') toast('Help requested', msg.event.detail, 'warn', 'phoneCall');
      clearTimeout(pending); pending = setTimeout(refresh, 400);
    } else if (msg.type === 'event_update') {
      clearTimeout(pending); pending = setTimeout(refresh, 200);
    }
  });
  refresh();
  setInterval(refresh, 10000);
  setInterval(renderEvents, 30000);   // keep "2m ago" labels fresh
})();
