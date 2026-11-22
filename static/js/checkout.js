/* Grab & Go — checkout: payment method, UPI QR, order summary */
(function () {
  'use strict';
  const { icon, productIcon, money, esc, get, post, toast, liveSocket } = window.GG;
  const $ = (id) => document.getElementById(id);
  let cart = null, method = 'upi', qrFor = null, paying = false;

  const HOW = {
    upi: { title: 'Scan the QR code', steps: ['Open any UPI app on your phone', 'Scan the code and approve the payment', 'This screen confirms by itself'] },
    card: { title: 'Use the card reader', steps: ['Tap your card or phone on the reader', 'Or insert the card and enter your PIN', 'Keep the card until the reader beeps'] },
    wallet: { title: 'Pay from your wallet', steps: ['Open the store app on your phone', 'Choose Wallet and approve the amount', 'This screen confirms by itself'] }
  };

  function render() {
    const items = (cart && cart.items) || [];
    $('emptyState').hidden = items.length > 0;
    $('checkout').hidden = items.length === 0;
    if (!items.length) return;

    $('due').textContent = money(cart.grand_total);
    $('sumSub').textContent = money(cart.total);
    $('sumTax').textContent = money(cart.tax);
    $('sumTotal').textContent = money(cart.grand_total);
    $('confirmBtn').textContent = "I've paid " + money(cart.grand_total);
    $('sumList').innerHTML = items.map(i =>
      '<div class="row"><div class="tile sm">' + productIcon(i.category) + '</div>' +
      '<div class="info"><div class="name">' + esc(i.name) + '</div><div class="meta">Qty ' + i.quantity + '</div></div>' +
      '<div class="amt" style="font-size:15px">' + money(i.subtotal, true) + '</div></div>').join('');
    renderMethod();
  }

  function renderMethod() {
    document.querySelectorAll('.method').forEach(b => b.setAttribute('aria-checked', String(b.dataset.method === method)));
    const how = HOW[method];
    $('payHow').textContent = how.title;
    $('paySteps').innerHTML = how.steps.map((s, i) => '<li><b>' + (i + 1) + '</b>' + esc(s) + '</li>').join('');
    $('qrBox').hidden = method !== 'upi';
    $('readerBox').hidden = method === 'upi';
    $('readerBox').innerHTML = icon(method === 'card' ? 'card' : 'wallet');
    if (method === 'upi' && cart && qrFor !== cart.grand_total) {
      qrFor = cart.grand_total;
      $('qrImg').src = '/api/upi-qr?amount=' + encodeURIComponent(cart.grand_total.toFixed(2));
    }
  }

  document.querySelectorAll('.method').forEach(b => b.addEventListener('click', () => { method = b.dataset.method; renderMethod(); }));
  // arrow keys move between the radio-style buttons
  document.querySelector('.methods').addEventListener('keydown', (e) => {
    if (!['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp'].includes(e.key)) return;
    const all = [...document.querySelectorAll('.method')];
    const i = all.findIndex(b => b.dataset.method === method);
    const n = all[(i + (e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : all.length - 1)) % all.length];
    method = n.dataset.method; renderMethod(); n.focus(); e.preventDefault();
  });
  $('qrImg').addEventListener('error', () => { $('qrBox').innerHTML = '<span class="muted" style="text-align:center;font-size:13px">QR unavailable.<br>Run: pip install qrcode</span>'; });

  $('confirmBtn').addEventListener('click', async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    paying = true;
    try {
      const order = await post('/api/checkout', { method });
      try { sessionStorage.setItem('gg-last-order', order.order_id); } catch (err) { /* ignore */ }
      location.href = '/payment-success?order_id=' + encodeURIComponent(order.order_id);
    } catch (err) {
      btn.disabled = false;
      paying = false;
      toast('Payment could not be completed', err.message, 'err');
    }
  });

  liveSocket((msg) => { if (msg.type === 'cart' && !paying) { cart = msg.cart; render(); } });
  get('/api/cart').then(c => { cart = c; render(); }).catch(err => toast('Could not load cart', err.message, 'err'));
})();
