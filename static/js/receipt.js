/* Grab & Go — receipt page */
(function () {
  'use strict';
  const { productIcon, money, esc, get, post } = window.GG;
  const $ = (id) => document.getElementById(id);
  const RESET_SECONDS = 45;
  const METHOD = { upi: 'UPI', card: 'Card', wallet: 'Wallet' };
  let order = null, left = RESET_SECONDS, timer = 0, paused = false;

  const params = new URLSearchParams(location.search);
  let id = params.get('order_id');
  if (!id) { try { id = sessionStorage.getItem('gg-last-order'); } catch (e) { /* ignore */ } }

  function show(o) {
    order = o;
    $('receipt').hidden = false;
    $('rId').textContent = o.order_id;
    $('rMethod').textContent = METHOD[o.method] || (o.method || '').toUpperCase();
    $('rTime').textContent = new Date(o.timestamp).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    $('rItems').innerHTML = o.items.map(i =>
      '<div class="row"><div class="tile sm">' + productIcon(i.category) + '</div>' +
      '<div class="info"><div class="name">' + esc(i.name) + '</div><div class="meta">' + esc(i.brand) + ' · ' + money(i.price, true) + ' × ' + i.quantity + '</div></div>' +
      '<div class="amt" style="font-size:15px">' + money(i.subtotal, true) + '</div></div>').join('');
    $('rSub').textContent = money(o.total);
    $('rTax').textContent = money(o.tax);
    $('rTotal').textContent = money(o.grand_total);
    startCountdown();
  }

  function tick() {
    $('resetPill').hidden = false;
    $('resetPillText').textContent = 'New order in ' + left + 's';
    $('resetNote').textContent = paused ? 'Auto-reset paused while you type' : 'This kiosk resets automatically in ' + left + ' seconds';
    if (paused) return;
    if (left <= 0) { location.href = '/'; return; }
    left -= 1;
  }
  function startCountdown() { tick(); timer = setInterval(tick, 1000); }

  const phone = $('phone');
  phone.addEventListener('focus', () => { paused = true; tick(); });
  phone.addEventListener('blur', () => { paused = false; left = Math.max(left, 15); });
  phone.addEventListener('input', () => { phone.value = phone.value.replace(/\D/g, '').slice(0, 10); });

  $('smsForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = $('smsMsg');
    msg.hidden = false;
    msg.style.color = '';
    if (!/^[6-9]\d{9}$/.test(phone.value)) {
      msg.textContent = 'Enter a valid 10-digit mobile number.';
      msg.style.color = 'var(--danger)';
      phone.focus();
      return;
    }
    try {
      await post('/api/receipt/sms', { order_id: order.order_id, phone: phone.value });
      msg.textContent = 'Receipt request saved for +91 ' + phone.value.slice(0, 2) + '••••••' + phone.value.slice(-2) + '.';
      msg.style.color = 'var(--brand-ink)';
      phone.value = '';
      phone.blur();
    } catch (err) {
      msg.textContent = err.message;
      msg.style.color = 'var(--danger)';
    }
  });

  get('/api/orders/' + encodeURIComponent(id || 'latest'))
    .then(show)
    .catch(() => { $('noOrder').hidden = false; });
})();
