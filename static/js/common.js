/* Grab & Go — shared helpers for every page */
(function () {
  'use strict';

  // ---------- icons (inline stroke SVG, no emoji) ----------
  const P = {
    bag: '<path d="M6 7h12l-1 13H7L6 7z"/><path d="M9 7a3 3 0 0 1 6 0"/>',
    scan: '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/>',
    camera: '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3.5"/>',
    cameraOff: '<path d="M2 2l20 20"/><path d="M9.5 4h5L17 7h3a2 2 0 0 1 2 2v7.5M14.1 14.1A3.5 3.5 0 0 1 9.9 9.9M21 20H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h3"/>',
    phoneCall: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/>',
    lang: '<path d="M5 8l6 6M4 14l6-6 2-3M2 5h12M7 2h1M22 22l-5-10-5 10M14 18h6"/>',
    undo: '<path d="M9 14L4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
    check: '<path d="M5 12l5 5L20 7"/>',
    checkCircle: '<circle cx="12" cy="12" r="10"/><path d="M8 12l3 3 5-6"/>',
    arrowR: '<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>',
    arrowL: '<path d="M19 12H5"/><path d="M11 6l-6 6 6 6"/>',
    trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/>',
    minus: '<path d="M5 12h14"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    basket: '<path d="M5 11l2-6M19 11l-2-6M2 11h20l-2 9H4l-2-9z"/><path d="M9 15v2M15 15v2M12 15v2"/>',
    card: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/>',
    wallet: '<path d="M20 7H5a2 2 0 0 1 0-4h13v4"/><path d="M3 5v14a2 2 0 0 0 2 2h15V7"/><path d="M16 14h.01"/>',
    qr: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><path d="M14 14h3v3h-3zM20 14v.01M14 20h.01M17 20h3v-3"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    sms: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    refresh: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
    plusCircle: '<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>',
    minusCircle: '<circle cx="12" cy="12" r="9"/><path d="M8 12h8"/>',
    alert: '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
    cpu: '<rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
    video: '<path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/>',
    grid: '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
    receipt: '<path d="M4 2v20l3-2 3 2 2-2 2 2 3-2 3 2V2l-3 2-3-2-2 2-2-2-3 2-3-2z"/><path d="M8 9h8M8 13h8"/>',
    // product categories
    chips: '<path d="M7 3h10l-1 3 1 3-1 3 1 3-1 3 1 3H7l1-3-1-3 1-3-1-3 1-3-1-3z"/><path d="M10 9h4M10 13h4"/>',
    drink: '<path d="M8 2h8M9 2v3l-2 4v11a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9l-2-4V2"/><path d="M7 13h10"/>',
    candy: '<path d="M9.5 7.5l7 7"/><rect x="6" y="6" width="12" height="12" rx="3" transform="rotate(45 12 12)"/><path d="M4 4l2.5 2.5M17.5 17.5L20 20"/>',
    cookie: '<path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/><path d="M8.5 8.5h.01M16 15.5h.01M12 12h.01M11 17h.01M7 14h.01"/>',
    noodles: '<path d="M4 11h16a8 8 0 0 1-16 0z"/><path d="M8 11V4M12 11V3M16 11V5"/>',
    apple: '<path d="M12 6c-2-2-6-2-7 2-1 3 1 9 4 11 1 .6 2 .6 3 0 1 .6 2 .6 3 0 3-2 5-8 4-11-1-4-5-4-7-2z"/><path d="M12 6c0-2 1-3 3-4"/>',
    leaf: '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10z"/><path d="M2 21c0-3 1.9-5.4 5.2-6"/>',
    phone: '<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M11 18h2"/>',
    bread: '<path d="M5 11a4 4 0 0 1 0-8h14a4 4 0 0 1 0 8v9H5z"/><path d="M9 7v2M13 7v2"/>',
    tag: '<path d="M20.6 13.4L13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><path d="M7 7h.01"/>'
  };
  function icon(name, cls) {
    return '<svg class="i ' + (cls || '') + '" viewBox="0 0 24 24" aria-hidden="true">' + (P[name] || P.bag) + '</svg>';
  }
  const CATEGORY_ICON = {
    'chips & snacks': 'chips', 'beverages': 'drink', 'chocolates': 'candy', 'biscuits & cookies': 'cookie',
    'instant food': 'noodles', 'fruits': 'apple', 'vegetables': 'leaf', 'electronics': 'phone',
    'bakery': 'bread', 'packaged': 'tag'
  };
  function productIcon(category) { return icon(CATEGORY_ICON[(category || '').toLowerCase()] || 'bag'); }

  // ---------- formatting ----------
  const inr = new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  function money(v, whole) {
    const n = Number(v) || 0;
    if (whole && Number.isInteger(n)) return '₹' + n.toLocaleString('en-IN');
    return '₹' + inr.format(n);
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  function timeAgo(iso) {
    const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
    if (s < 10) return 'just now';
    if (s < 60) return Math.floor(s) + 's ago';
    if (s < 3600) return Math.floor(s / 60) + 'm ago';
    return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  }

  // ---------- API ----------
  async function api(path, opts) {
    const o = Object.assign({ headers: {} }, opts || {});
    if (o.body && typeof o.body !== 'string') { o.body = JSON.stringify(o.body); o.headers['Content-Type'] = 'application/json'; }
    const res = await fetch(path, o);
    let data = null;
    try { data = await res.json(); } catch (e) { /* non-JSON */ }
    if (!res.ok) { const err = new Error((data && data.error) || ('HTTP ' + res.status)); err.status = res.status; err.data = data; throw err; }
    return data;
  }
  const get = (p) => api(p);
  const post = (p, body) => api(p, { method: 'POST', body: body || {} });

  // ---------- toasts ----------
  function toast(title, detail, kind, iconName) {
    let box = document.getElementById('toasts');
    if (!box) { box = document.createElement('div'); box.id = 'toasts'; box.className = 'toasts'; box.setAttribute('role', 'status'); box.setAttribute('aria-live', 'polite'); document.body.appendChild(box); }
    const el = document.createElement('div');
    el.className = 'toast ' + (kind || '');
    el.innerHTML = '<div class="tile">' + icon(iconName || (kind === 'warn' ? 'minusCircle' : kind === 'err' ? 'alert' : 'checkCircle')) + '</div>' +
      '<div><div class="t">' + esc(title) + '</div>' + (detail ? '<div class="d">' + esc(detail) + '</div>' : '') + '</div>';
    box.prepend(el);
    while (box.children.length > 4) box.lastChild.remove();
    setTimeout(() => { el.classList.add('out'); setTimeout(() => el.remove(), 300); }, 4200);
  }

  // ---------- live store socket (/ws/cart) ----------
  function liveSocket(onMessage) {
    let ws, ping, retry = 0, closed = false;
    function open() {
      ws = new WebSocket((location.protocol === 'https:' ? 'wss' : 'ws') + '://' + location.host + '/ws/cart');
      ws.onopen = () => { retry = 0; ping = setInterval(() => ws.readyState === 1 && ws.send('ping'), 25000); };
      ws.onmessage = (e) => { try { onMessage(JSON.parse(e.data)); } catch (err) { console.error(err); } };
      ws.onclose = () => { clearInterval(ping); if (!closed) setTimeout(open, Math.min(8000, 1000 * Math.pow(2, retry++))); };
    }
    open();
    return { close() { closed = true; ws && ws.close(); } };
  }

  // ---------- staff call ----------
  async function callStaff(btn) {
    if (btn) btn.disabled = true;
    try {
      await post('/api/staff-call', { reason: 'Shopper needs help' });
      toast(t('staffComing'), t('staffComingD'), '', 'phoneCall');
    } catch (e) {
      toast(t('error'), e.message, 'err');
    } finally {
      if (btn) setTimeout(() => { btn.disabled = false; }, 4000);
    }
  }

  // ---------- English / Hindi ----------
  const STR = {
    en: {
      headline: 'Hold an item up to the camera', sub: "It's added to your cart automatically. Barcodes work too.",
      camReady: 'Camera ready', camOff: 'Camera off', camStarting: 'Starting camera…', camReconnect: 'Reconnecting…',
      startTitle: 'Start the camera to begin scanning', startSub: 'Hold each item inside the frame. We recognise the product or its barcode and add it for you.',
      startBtn: 'Initialize camera', stopBtn: 'Stop camera', scanning: 'Scanning', aiReady: 'AI ready',
      holdHint: 'Hold the item inside the frame', added: 'Added to cart', undo: 'Undo',
      s1: 'Show item', s1d: 'Hold it up to the camera', s2: 'Check cart', s2d: 'Items add by themselves', s3: 'Pay', s3d: 'UPI, card or wallet',
      cart: 'Your cart', items: 'items', item: 'item', subtotal: 'Subtotal', gst: 'GST', total: 'Total', pay: 'Pay', clear: 'Clear cart',
      emptyT: 'Your cart is empty', emptyD: 'Hold an item up to the camera to add it.', each: 'each',
      callStaff: 'Call staff', staffComing: 'Staff has been notified', staffComingD: 'Someone will be with you shortly.', error: 'Something went wrong',
      camDenied: 'Camera permission was blocked. Allow camera access in the browser address bar, then try again.',
      camNone: 'No camera was found on this device.', camBusy: 'The camera is being used by another app. Close it and try again.',
      camInsecure: 'The camera only works on http://127.0.0.1 or https:// pages.'
    },
    hi: {
      headline: 'सामान कैमरे के सामने रखें', sub: 'यह अपने आप आपकी कार्ट में जुड़ जाएगा। बारकोड भी चलता है।',
      camReady: 'कैमरा तैयार', camOff: 'कैमरा बंद', camStarting: 'कैमरा शुरू हो रहा है…', camReconnect: 'फिर से जुड़ रहा है…',
      startTitle: 'स्कैन शुरू करने के लिए कैमरा चालू करें', startSub: 'हर सामान को फ़्रेम के अंदर रखें। हम उसे पहचान कर कार्ट में जोड़ देंगे।',
      startBtn: 'कैमरा चालू करें', stopBtn: 'कैमरा बंद करें', scanning: 'स्कैन हो रहा है', aiReady: 'AI तैयार',
      holdHint: 'सामान को फ़्रेम के अंदर रखें', added: 'कार्ट में जोड़ा गया', undo: 'वापस लें',
      s1: 'सामान दिखाएँ', s1d: 'कैमरे के सामने रखें', s2: 'कार्ट देखें', s2d: 'सामान अपने आप जुड़ता है', s3: 'भुगतान', s3d: 'UPI, कार्ड या वॉलेट',
      cart: 'आपकी कार्ट', items: 'सामान', item: 'सामान', subtotal: 'उप-योग', gst: 'GST', total: 'कुल', pay: 'भुगतान करें', clear: 'कार्ट खाली करें',
      emptyT: 'आपकी कार्ट खाली है', emptyD: 'जोड़ने के लिए सामान कैमरे के सामने रखें।', each: 'प्रति',
      callStaff: 'स्टाफ़ बुलाएँ', staffComing: 'स्टाफ़ को सूचना दी गई', staffComingD: 'कोई जल्द ही आपकी मदद करेगा।', error: 'कुछ गलत हो गया',
      camDenied: 'कैमरे की अनुमति बंद है। ब्राउज़र में कैमरा अनुमति दें और फिर कोशिश करें।',
      camNone: 'इस डिवाइस पर कोई कैमरा नहीं मिला।', camBusy: 'कैमरा किसी दूसरे ऐप में चल रहा है। उसे बंद करके फिर कोशिश करें।',
      camInsecure: 'कैमरा केवल http://127.0.0.1 या https:// पर चलता है।'
    }
  };
  let lang = 'en';
  try { lang = localStorage.getItem('gg-lang') || 'en'; } catch (e) { /* storage blocked */ }
  function t(key) { return (STR[lang] && STR[lang][key]) || STR.en[key] || key; }
  function applyLang() {
    document.documentElement.lang = lang;
    document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
    const b = document.getElementById('langBtn');
    if (b) b.querySelector('.lbl').textContent = lang === 'en' ? 'EN' : 'हिं';
  }
  function toggleLang() {
    lang = lang === 'en' ? 'hi' : 'en';
    try { localStorage.setItem('gg-lang', lang); } catch (e) { /* ignore */ }
    applyLang();
    document.dispatchEvent(new CustomEvent('gg:lang'));
  }

  // ---------- bottom nav highlight ----------
  function markNav() {
    const path = location.pathname;
    document.querySelectorAll('.nav-pill a').forEach(a => {
      const on = a.getAttribute('href') === path;
      a.classList.toggle('on', on);
      if (on) a.setAttribute('aria-current', 'page');
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-icon]').forEach(el => { el.insertAdjacentHTML('afterbegin', icon(el.dataset.icon)); });
    markNav();
    applyLang();
    const lb = document.getElementById('langBtn');
    if (lb) lb.addEventListener('click', toggleLang);
    document.querySelectorAll('[data-call-staff]').forEach(b => b.addEventListener('click', () => callStaff(b)));
  });

  window.GG = { icon, productIcon, money, esc, timeAgo, api, get, post, toast, liveSocket, callStaff, t, applyLang,
                get lang() { return lang; } };
})();
