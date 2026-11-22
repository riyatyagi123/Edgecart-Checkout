/* Grab & Go — kiosk: live camera scanning, AI auto-add, live cart */
(function () {
  'use strict';
  const { icon, productIcon, money, esc, get, post, toast, liveSocket, t } = window.GG;
  const $ = (id) => document.getElementById(id);

  // ---- tuning ----
  const SEND_EVERY_MS = 250;        // try to send a frame this often (only one in flight at a time)
  const CAPTURE_WIDTH = 640;        // frames are downscaled before upload (faster AI)
  const REQUIRED_FRAMES = 2;        // vision match must hold for N consecutive frames
  const GONE_MS = 1500;             // item must leave the view this long before it can be added again
  const MIN_GAP_MS = 1200;          // minimum gap between any two auto-adds
  const FRESH_MS = 1200;            // overlay is hidden when the last result is older than this

  const els = {
    video: $('video'), view: $('view'), idle: $('camIdle'), live: $('camLive'), err: $('camError'),
    start: $('startBtn'), stop: $('stopBtn'), pill: $('camPill'), pillText: $('camPillText'),
    latency: $('latency'), hint: $('hint'), reticle: $('reticle'), scanline: $('scanline'),
    added: $('addedCard'), addedName: $('addedName'), addedIcon: $('addedIcon'), undo: $('undoBtn'),
    list: $('cartList'), count: $('cartCount'), subtotal: $('subtotal'), tax: $('tax'), grand: $('grand'),
    pay: $('payBtn'), payText: $('payText'), clear: $('clearBtn')
  };
  const ctx = els.view.getContext('2d');
  const grab = document.createElement('canvas');
  const grabCtx = grab.getContext('2d');

  let stream = null, ws = null, sendTimer = null, raf = 0;
  let inFlight = false, inFlightAt = 0, wsRetry = 0, status = 'off';
  let last = null, lastAt = 0;                 // last detection result
  const streak = {}, latched = {}, lastSeen = {};
  let lastAddAt = 0, lastAdded = null, addedTimer = 0;
  let cart = { items: [], total: 0, tax: 0, grand_total: 0, item_count: 0 };
  let prevQty = {};

  // ------------------------------------------------------------ status pill
  function setStatus(s) {
    status = s;
    const map = { off: ['off', 'camOff'], starting: ['warn', 'camStarting'], ready: ['ok live', 'camReady'], reconnect: ['warn', 'camReconnect'] };
    const [cls, key] = map[s];
    els.pill.className = 'pill ' + cls;
    els.pillText.dataset.i18n = key;
    els.pillText.textContent = t(key);
  }
  document.addEventListener('gg:lang', () => { setStatus(status); renderCart(); });

  // ------------------------------------------------------------ camera
  async function startCamera() {
    els.err.hidden = true;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { showCamError(t('camInsecure')); return; }
    setStatus('starting');
    els.start.disabled = true;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: { ideal: 'environment' } }
      });
    } catch (e) {
      els.start.disabled = false;
      setStatus('off');
      const name = e && e.name;
      showCamError(name === 'NotAllowedError' || name === 'SecurityError' ? t('camDenied')
        : name === 'NotFoundError' || name === 'OverconstrainedError' ? t('camNone')
        : name === 'NotReadableError' ? t('camBusy') : (t('error') + ': ' + (e.message || name)));
      return;
    }
    els.video.srcObject = stream;
    await els.video.play().catch(() => {});
    await new Promise(r => (els.video.videoWidth ? r() : els.video.addEventListener('loadedmetadata', r, { once: true })));
    els.view.width = els.video.videoWidth || 1280;
    els.view.height = els.video.videoHeight || 720;
    const scale = Math.min(1, CAPTURE_WIDTH / els.view.width);
    grab.width = Math.round(els.view.width * scale);
    grab.height = Math.round(els.view.height * scale);

    els.idle.hidden = true;
    els.live.hidden = false;
    els.start.disabled = false;
    stream.getVideoTracks()[0].addEventListener('ended', stopCamera);
    connectDetector();
    sendTimer = setInterval(sendFrame, SEND_EVERY_MS);
    raf = requestAnimationFrame(draw);
  }

  function stopCamera() {
    if (stream) stream.getTracks().forEach(tr => tr.stop());
    stream = null;
    clearInterval(sendTimer); cancelAnimationFrame(raf);
    if (ws) { ws.onclose = null; ws.close(); ws = null; }
    inFlight = false; last = null;
    ctx.clearRect(0, 0, els.view.width, els.view.height);
    els.live.hidden = true; els.idle.hidden = false;
    setStatus('off');
  }

  function showCamError(msg) { els.err.textContent = msg; els.err.hidden = false; }

  // ------------------------------------------------------------ detector socket
  function connectDetector() {
    ws = new WebSocket((location.protocol === 'https:' ? 'wss' : 'ws') + '://' + location.host + '/ws/detect');
    ws.onopen = () => { wsRetry = 0; inFlight = false; setStatus('ready'); };
    ws.onmessage = (e) => {
      inFlight = false;
      let data;
      try { data = JSON.parse(e.data); } catch (err) { return; }
      if (data.error) return;
      last = data; lastAt = performance.now();
      if (data.latency_ms != null) els.latency.textContent = '· ' + data.latency_ms + ' ms';
      handleResult(data);
    };
    ws.onclose = () => {
      if (!stream) return;
      setStatus('reconnect');
      setTimeout(() => { if (stream) connectDetector(); }, Math.min(8000, 800 * Math.pow(2, wsRetry++)));
    };
  }

  function sendFrame() {
    if (!ws || ws.readyState !== 1 || !stream) return;
    if (inFlight && performance.now() - inFlightAt < 5000) return;   // wait for the previous answer
    grabCtx.drawImage(els.video, 0, 0, grab.width, grab.height);      // raw frame, no overlay drawn on it
    inFlight = true; inFlightAt = performance.now();
    ws.send(grab.toDataURL('image/jpeg', 0.8));
  }

  // ------------------------------------------------------------ drawing
  function roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }
  let px = 1;   // canvas pixels per on-screen CSS pixel (canvas is shown with object-fit: cover)
  let vis = { x0: 0, y0: 0, x1: 0, y1: 0 };   // part of the canvas that is actually visible
  function label(text, x, y) {
    const fs = 15 * px;
    ctx.font = '600 ' + fs + 'px Inter, system-ui, sans-serif';
    const padX = fs * 0.85, h = fs * 2.2, w = ctx.measureText(text).width + padX * 2;
    let ly = y - h - 8 * px;
    if (ly < vis.y0 + 8 * px) ly = y + 8 * px;                       // no room above: put it inside the box
    const lx = Math.min(Math.max(vis.x0 + 8 * px, x), vis.x1 - w - 8 * px);
    ctx.fillStyle = 'rgba(3, 105, 161, 0.92)';
    roundRect(lx, ly, w, h, h / 2); ctx.fill();
    ctx.fillStyle = '#FFFFFF'; ctx.textBaseline = 'middle';
    ctx.fillText(text, lx + padX, ly + h / 2 + 1);
  }
  function draw() {
    raf = requestAnimationFrame(draw);
    if (!stream || els.video.readyState < 2) return;
    const W = els.view.width, H = els.view.height;
    const r = els.view.getBoundingClientRect();
    px = r.width ? 1 / Math.max(r.width / W, r.height / H) : 1;
    const vw = r.width * px, vh = r.height * px;
    vis = { x0: (W - vw) / 2, y0: (H - vh) / 2, x1: (W + vw) / 2, y1: (H + vh) / 2 };
    ctx.drawImage(els.video, 0, 0, W, H);
    const fresh = last && performance.now() - lastAt < FRESH_MS;
    const dets = fresh ? (last.detections || []) : [];
    const bc = fresh ? last.barcode : null;
    const showing = dets.length > 0 || !!bc;
    els.reticle.hidden = showing; els.scanline.hidden = showing; els.hint.hidden = showing || !els.added.hidden;
    if (!fresh || !last.frame_size) return;
    const sx = W / last.frame_size[0], sy = H / last.frame_size[1];
    const lw = 3 * px;

    dets.forEach(d => {
      const [x1, y1, x2, y2] = d.bbox;
      const X = x1 * sx, Y = y1 * sy, BW = (x2 - x1) * sx, BH = (y2 - y1) * sy;
      ctx.save();
      ctx.lineWidth = lw; ctx.strokeStyle = 'rgba(56, 189, 248, 0.95)';
      ctx.shadowColor = 'rgba(56, 189, 248, 0.6)'; ctx.shadowBlur = 12 * px;
      roundRect(X, Y, BW, BH, Math.min(14 * px, BW / 8)); ctx.stroke();
      ctx.restore();
      label(d.name + '  ' + Math.round(d.confidence * 100) + '%', X, Y);
    });
    if (bc && bc.points && bc.points.length) {
      ctx.save();
      ctx.lineWidth = lw; ctx.strokeStyle = '#38BDF8';
      ctx.beginPath();
      bc.points.forEach((p, i) => (i ? ctx.lineTo(p[0] * sx, p[1] * sy) : ctx.moveTo(p[0] * sx, p[1] * sy)));
      ctx.closePath(); ctx.stroke(); ctx.restore();
      const top = bc.points.reduce((a, p) => (p[1] < a[1] ? p : a), bc.points[0]);
      label('Barcode · ' + bc.name, top[0] * sx, top[1] * sy);
    }
  }

  // ------------------------------------------------------------ auto-add logic
  function handleResult(data) {
    const now = performance.now();
    const seen = new Set();
    const candidates = [];
    if (data.barcode && data.barcode.product_id) {
      seen.add(data.barcode.product_id);
      candidates.push({ pid: data.barcode.product_id, name: data.barcode.name, category: 'Packaged', source: 'barcode', confidence: 1, need: 1 });
    }
    (data.detections || []).slice(0, 1).forEach(d => {
      seen.add(d.product_id);
      candidates.push({ pid: d.product_id, name: d.name, category: d.category, source: 'vision', confidence: d.confidence, need: REQUIRED_FRAMES });
    });
    seen.forEach(pid => { lastSeen[pid] = now; });
    Object.keys(streak).forEach(pid => { if (!seen.has(pid)) streak[pid] = 0; });
    Object.keys(latched).forEach(pid => { if (now - (lastSeen[pid] || 0) > GONE_MS) delete latched[pid]; });

    for (const c of candidates) {
      streak[c.pid] = (streak[c.pid] || 0) + 1;
      if (latched[c.pid] || streak[c.pid] < c.need || now - lastAddAt < MIN_GAP_MS) continue;
      latched[c.pid] = true; lastAddAt = now; streak[c.pid] = 0;
      addFromCamera(c);
      break;
    }
  }

  async function addFromCamera(c) {
    try {
      const res = await post('/api/cart/add', { product_id: c.pid, quantity: 1, source: c.source, confidence: c.confidence });
      setCart(res.cart);
      showAdded(c);
      chime();
    } catch (e) {
      toast(t('error'), e.message, 'err');
    }
  }

  function showAdded(c) {
    lastAdded = c;
    const item = cart.items.find(i => i.product_id === c.pid);
    els.addedName.textContent = item ? item.name : c.name;
    els.addedIcon.innerHTML = productIcon(item ? item.category : c.category);
    els.added.hidden = false;
    clearTimeout(addedTimer);
    addedTimer = setTimeout(() => { els.added.hidden = true; }, 6000);
  }
  els.undo.addEventListener('click', async () => {
    if (!lastAdded) return;
    els.added.hidden = true;
    try { setCart((await post('/api/cart/update', { product_id: lastAdded.pid, quantity_delta: -1 })).cart); }
    catch (e) { toast(t('error'), e.message, 'err'); }
    lastAdded = null;
  });

  let audio = null;
  function chime() {
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      const now = audio.currentTime;
      [880, 1320].forEach((f, i) => {
        const o = audio.createOscillator(), g = audio.createGain();
        o.type = 'sine'; o.frequency.value = f;
        g.gain.setValueAtTime(0.0001, now + i * 0.09);
        g.gain.exponentialRampToValueAtTime(0.18, now + i * 0.09 + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, now + i * 0.09 + 0.25);
        o.connect(g); g.connect(audio.destination); o.start(now + i * 0.09); o.stop(now + i * 0.09 + 0.3);
      });
    } catch (e) { /* audio not available */ }
  }

  // ------------------------------------------------------------ cart
  function setCart(c) {
    if (!c) return;
    cart = c;
    renderCart();
  }
  function renderCart() {
    const items = cart.items || [];
    const n = cart.item_count != null ? cart.item_count : items.reduce((s, i) => s + i.quantity, 0);
    els.count.textContent = n ? n + ' ' + (n === 1 ? t('item') : t('items')) : '';
    if (!items.length) {
      els.list.innerHTML = '<div class="empty"><div class="tile">' + icon('basket') + '</div><b>' + esc(t('emptyT')) + '</b>' + esc(t('emptyD')) + '</div>';
    } else {
      els.list.innerHTML = items.map(i => {
        const changed = prevQty[i.product_id] !== i.quantity;
        return '<div class="row' + (changed ? ' flash' : '') + '" data-pid="' + esc(i.product_id) + '">' +
          '<div class="tile">' + productIcon(i.category) + '</div>' +
          '<div class="info"><div class="name" title="' + esc(i.name) + '">' + esc(i.name) + '</div>' +
          '<div class="meta">' + esc(i.brand) + ' · ' + money(i.price, true) + ' ' + esc(t('each')) + '</div></div>' +
          '<div class="qty">' +
          '<button type="button" data-act="dec" aria-label="Remove one ' + esc(i.name) + '">' + icon('minus') + '</button>' +
          '<span>' + i.quantity + '</span>' +
          '<button type="button" data-act="inc" aria-label="Add one ' + esc(i.name) + '">' + icon('plus') + '</button></div>' +
          '<div class="amt">' + money(i.subtotal, true) + '</div></div>';
      }).join('');
    }
    prevQty = {}; items.forEach(i => { prevQty[i.product_id] = i.quantity; });
    els.subtotal.textContent = money(cart.total);
    els.tax.textContent = money(cart.tax);
    els.grand.textContent = money(cart.grand_total);
    els.payText.textContent = t('pay') + ' ' + money(cart.grand_total);
    els.pay.setAttribute('aria-disabled', items.length ? 'false' : 'true');
    els.clear.hidden = !items.length;
    $('step1').classList.toggle('active', !items.length);
    $('step2').classList.toggle('active', !!items.length);
  }
  els.list.addEventListener('click', async (e) => {
    const b = e.target.closest('button[data-act]');
    if (!b) return;
    const pid = b.closest('.row').dataset.pid;
    b.disabled = true;
    try { setCart((await post('/api/cart/update', { product_id: pid, quantity_delta: b.dataset.act === 'inc' ? 1 : -1 })).cart); }
    catch (err) { toast(t('error'), err.message, 'err'); }
  });
  els.clear.addEventListener('click', async () => {
    try { setCart((await post('/api/cart/clear')).cart); Object.keys(latched).forEach(k => delete latched[k]); }
    catch (err) { toast(t('error'), err.message, 'err'); }
  });
  els.pay.addEventListener('click', (e) => { if (!(cart.items || []).length) e.preventDefault(); });

  // ------------------------------------------------------------ live store events
  liveSocket((msg) => {
    if (msg.type === 'cart') setCart(msg.cart);
    else if (msg.type === 'edge_event') {
      const shelf = msg.node_id.replace(/^shelf-?/i, 'Shelf ');
      if (msg.event === 'Take') { toast(shelf + ' · ' + msg.name + ' picked up', '+' + money(msg.price, true) + ' added to cart', '', 'plusCircle'); chime(); }
      else toast(shelf + ' · ' + msg.name + ' put back', money(msg.price, true) + ' removed from cart', 'warn', 'minusCircle');
    }
  });

  els.start.addEventListener('click', startCamera);
  els.stop.addEventListener('click', stopCamera);
  window.addEventListener('pagehide', stopCamera);
  get('/api/cart').then(setCart).catch(() => renderCart());
  setStatus('off');
})();
