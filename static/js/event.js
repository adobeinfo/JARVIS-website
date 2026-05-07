// ─── Event "Time Capsule" — клиент ──────────────────────────────────────────
// 1. Обратный отсчёт до релиза (раз в секунду)
// 2. Поллинг состояния каждые 30 сек (вдруг открылись новые секреты)
// 3. Разгадывание загадки → POST /api/event/unlock

(function () {
  const $ = (id) => document.getElementById(id);
  const fmt2 = (n) => String(Math.max(0, n)).padStart(2, '0');

  let currentSecretId = null;

  // ─── Большой обратный отсчёт ────────────────────────────────────────────
  const cdRoot = document.querySelector('.ev-countdown');
  const releaseTs = cdRoot ? parseInt(cdRoot.dataset.release, 10) : 0;

  function tickCountdown() {
    const left = releaseTs - Math.floor(Date.now() / 1000);
    if (left <= 0) {
      $('cdDays').textContent = '00';
      $('cdHours').textContent = '00';
      $('cdMin').textContent = '00';
      $('cdSec').textContent = '00';
      return;
    }
    const days = Math.floor(left / 86400);
    const hours = Math.floor((left % 86400) / 3600);
    const min = Math.floor((left % 3600) / 60);
    const sec = left % 60;
    $('cdDays').textContent = fmt2(days);
    $('cdHours').textContent = fmt2(hours);
    $('cdMin').textContent = fmt2(min);
    $('cdSec').textContent = fmt2(sec);
  }

  // ─── Маленькие таймеры на заблокированных карточках ─────────────────────
  function tickSecretTimers() {
    document.querySelectorAll('.ev-secret-timer').forEach(el => {
      const dl = parseInt(el.dataset.deadline, 10);
      const left = dl - Math.floor(Date.now() / 1000);
      if (left <= 0) {
        el.textContent = 'сейчас!';
        return;
      }
      const d = Math.floor(left / 86400);
      const h = Math.floor((left % 86400) / 3600);
      const m = Math.floor((left % 3600) / 60);
      const s = left % 60;
      if (d > 0)      el.textContent = `${d}д ${fmt2(h)}ч ${fmt2(m)}м`;
      else if (h > 0) el.textContent = `${fmt2(h)}:${fmt2(m)}:${fmt2(s)}`;
      else            el.textContent = `${fmt2(m)}:${fmt2(s)}`;
    });
  }

  setInterval(() => { tickCountdown(); tickSecretTimers(); }, 1000);
  tickCountdown(); tickSecretTimers();

  // ─── Поллинг состояния (новые секреты могут стать доступными) ───────────
  let lastState = null;
  async function refreshState() {
    try {
      const r = await fetch('/api/event/state');
      if (!r.ok) return;
      const st = await r.json();
      // Если изменилось число секретов / разгадок — перезагружаем страницу
      if (lastState && (lastState.unlocked_count !== st.unlocked_count
                       || lastState.total !== st.total
                       || lastState.beta_code !== st.beta_code)) {
        location.reload();
        return;
      }
      // Если секрет стал available, а на странице ещё locked — перезагружаем
      st.secrets.forEach(s => {
        const card = document.querySelector(`.ev-secret-card[data-id="${s.id}"]`);
        if (!card) return;
        if (s.available && card.classList.contains('is-locked')) {
          location.reload();
        }
      });
      lastState = st;
    } catch (e) { /* ignore */ }
  }
  setInterval(refreshState, 30000);
  refreshState();

  // ─── Модалка разгадывания ──────────────────────────────────────────────
  function openRiddle(secretId) {
    if (!lastState) return;
    const s = lastState.secrets.find(x => x.id === secretId);
    if (!s) return;
    currentSecretId = secretId;
    $('evRiddleTitle').textContent = '#' + (lastState.secrets.indexOf(s) + 1);
    $('evRiddleQ').textContent = s.riddle || '—';
    $('evRiddleInput').value = '';
    $('evRiddleError').textContent = '';
    $('evRiddleOverlay').hidden = false;
    setTimeout(() => $('evRiddleInput').focus(), 80);
  }
  function closeRiddle() {
    $('evRiddleOverlay').hidden = true;
    currentSecretId = null;
  }

  async function submitRiddle() {
    const ans = $('evRiddleInput').value.trim();
    if (!ans || currentSecretId == null) return;
    $('evRiddleSubmit').disabled = true;
    $('evRiddleError').textContent = '';
    try {
      const r = await fetch('/api/event/unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ secret_id: currentSecretId, answer: ans }),
      });
      const data = await r.json();
      if (data.ok) {
        flash('🔓 Секрет разгадан!');
        closeRiddle();
        setTimeout(() => location.reload(), 600);
      } else {
        const msg = data.reason === 'wrong'        ? '❌ Неверный ответ. Попробуй ещё раз.'
                  : data.reason === 'locked_time'  ? '⏰ Секрет ещё закрыт.'
                  : '❌ Не получилось.';
        $('evRiddleError').textContent = msg;
      }
    } catch (e) {
      $('evRiddleError').textContent = 'Ошибка сети';
    } finally {
      $('evRiddleSubmit').disabled = false;
    }
  }

  function flash(msg) {
    const el = document.createElement('div');
    el.className = 'ev-flash';
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.classList.add('show'), 10);
    setTimeout(() => { el.classList.remove('show'); setTimeout(() => el.remove(), 300); }, 3500);
  }

  // ─── Делегирование кликов по «Разгадать» ────────────────────────────────
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action="open"]');
    if (btn) {
      const id = parseInt(btn.dataset.id, 10);
      if (lastState) openRiddle(id);
      else refreshState().then(() => openRiddle(id));
    }
  });

  $('evRiddleClose').addEventListener('click', closeRiddle);
  $('evRiddleOverlay').addEventListener('click', (e) => {
    if (e.target.id === 'evRiddleOverlay') closeRiddle();
  });
  $('evRiddleSubmit').addEventListener('click', submitRiddle);
  $('evRiddleInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submitRiddle();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !$('evRiddleOverlay').hidden) closeRiddle();
  });
})();
