/* ═══════════════════════════════════════════════
   JARVIS WEBSITE — main.js
═══════════════════════════════════════════════ */

// ─── Мобильное меню ──────────────────────────
function toggleMenu() {
  const links = document.getElementById("navLinks");
  const burger = document.getElementById("navBurger");
  if (!links) return;
  const open = links.classList.toggle("open");
  if (burger) burger.classList.toggle("active", open);
}
document.addEventListener("click", function (e) {
  const links = document.getElementById("navLinks");
  const burger = document.getElementById("navBurger");
  if (links && links.classList.contains("open")) {
    if (!links.contains(e.target) && burger && !burger.contains(e.target)) {
      links.classList.remove("open");
      burger.classList.remove("active");
    }
  }
});

// ─── Navbar scroll tint ───────────────────────
(function () {
  const nb = document.getElementById("navbar");
  if (!nb) return;
  window.addEventListener(
    "scroll",
    function () {
      nb.classList.toggle("scrolled", window.scrollY > 30);
    },
    { passive: true },
  );
})();

// ─── Плавная прокрутка к якорям ──────────────
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener("click", function (e) {
      const id = a.getAttribute("href");
      if (id === "#") return;
      const target = document.querySelector(id);
      if (!target) return;
      e.preventDefault();
      const nb = document.getElementById("navbar");
      const offset = nb ? nb.offsetHeight + 16 : 80;
      window.scrollTo({
        top: target.getBoundingClientRect().top + window.scrollY - offset,
        behavior: "smooth",
      });
    });
  });
});

// ─── Анимации появления ───────────────────────
(function () {
  const els = document.querySelectorAll(".animate-on-scroll");
  if (!els.length) return;
  const io = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          en.target.classList.add("visible");
          io.unobserve(en.target);
        }
      });
    },
    { threshold: 0.1, rootMargin: "0px 0px -40px 0px" },
  );
  els.forEach(function (el) {
    io.observe(el);
  });
})();

// ─── Flash auto-hide ──────────────────────────
(function () {
  document.querySelectorAll(".flash").forEach(function (el) {
    setTimeout(function () {
      el.style.transition = "opacity .5s";
      el.style.opacity = "0";
      setTimeout(function () {
        el.remove();
      }, 500);
    }, 4500);
  });
})();

/* ═══════════════════════════════════════════════
   AI CHAT WIDGET
═══════════════════════════════════════════════ */

var chatOpen = false;

// Все возможные подсказки
var ALL_SUGGESTIONS = [
  "Как скачать JARVIS?",
  "Какие системные требования?",
  "Что такое Wake-Word?",
  "Как настроить GigaChat?",
  "Какие есть голоса TTS?",
  "Бесплатно ли JARVIS?",
  "Как добавить голос ElevenLabs?",
  "Как работает Vosk офлайн?",
  "Что такое Discord Rich Presence?",
  "Как создать сценарий запуска?",
  "Как поменять тему интерфейса?",
  "Работает ли без интернета?",
  "Как обновить JARVIS?",
  "Как настроить микрофон?",
  "Поддерживает ли Fish Audio?",
];

function toggleChat() {
  chatOpen = !chatOpen;
  const panel = document.getElementById("chatPanel");
  const fab = document.getElementById("chatFab");
  if (!panel) return;
  panel.classList.toggle("open", chatOpen);
  // Убираем бейдж при открытии
  if (chatOpen) {
    const badge = fab && fab.querySelector(".chat-fab-badge");
    if (badge) badge.style.display = "none";
    setTimeout(function () {
      var inp = document.getElementById("chatInput");
      if (inp) inp.focus();
    }, 350);
  }
}

function appendMessage(role, text) {
  const box = document.getElementById("chatMessages");
  if (!box) return;
  const wrap = document.createElement("div");
  wrap.className = "chat-msg " + role;

  const avatar = document.createElement("div");
  avatar.className = "chat-msg-avatar";
  avatar.textContent = role === "bot" ? "🤖" : "👤";

  const bubble = document.createElement("div");
  bubble.className = "chat-msg-bubble";
  bubble.textContent = text;

  wrap.appendChild(avatar);
  wrap.appendChild(bubble);
  box.appendChild(wrap);
  box.scrollTop = box.scrollHeight;
  return wrap;
}

function showTyping() {
  const box = document.getElementById("chatMessages");
  if (!box) return null;
  const wrap = document.createElement("div");
  wrap.className = "chat-msg bot";
  wrap.id = "chatTyping";

  const avatar = document.createElement("div");
  avatar.className = "chat-msg-avatar";
  avatar.textContent = "🤖";

  const dots = document.createElement("div");
  dots.className = "chat-typing";
  dots.innerHTML = "<span></span><span></span><span></span>";

  wrap.appendChild(avatar);
  wrap.appendChild(dots);
  box.appendChild(wrap);
  box.scrollTop = box.scrollHeight;
  return wrap;
}

function removeTyping() {
  const el = document.getElementById("chatTyping");
  if (el) el.remove();
}

function hideSuggestions() {
  const s = document.getElementById("chatSuggestions");
  if (s) s.style.display = "none";
}

function showFilteredSuggestions(query) {
  const s = document.getElementById("chatSuggestions");
  if (!s) return;
  if (!query || query.length < 2) {
    s.style.display = "";
    return;
  }
  const q = query.toLowerCase();
  const matched = ALL_SUGGESTIONS.filter(function (t) {
    return t.toLowerCase().includes(q);
  });

  // Обновляем кнопки подсказок
  s.innerHTML = "";
  const show = matched.length ? matched.slice(0, 4) : [];
  if (!show.length) {
    s.style.display = "none";
    return;
  }

  show.forEach(function (text) {
    const btn = document.createElement("button");
    btn.className = "chat-suggestion";
    btn.textContent = text;
    btn.onclick = function () {
      sendSuggestion(text);
    };
    s.appendChild(btn);
  });
  s.style.display = "";
}

function sendSuggestion(text) {
  const inp = document.getElementById("chatInput");
  if (inp) {
    inp.value = text;
    chatInputUpdate(inp);
  }
  sendMessage(text);
}

async function sendMessage(text) {
  text = (text || "").trim();
  if (!text) return;

  const inp = document.getElementById("chatInput");
  const sendBtn = document.getElementById("chatSend");

  if (inp) inp.value = "";
  if (inp) inp.style.height = "";
  if (sendBtn) sendBtn.disabled = true;
  hideSuggestions();

  appendMessage("user", text);
  const typing = showTyping();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    removeTyping();
    appendMessage("bot", data.reply || data.error || "Что-то пошло не так.");
  } catch (e) {
    removeTyping();
    appendMessage("bot", "Нет связи с сервером. Проверьте интернет.");
  } finally {
    if (sendBtn) sendBtn.disabled = false;
    if (inp) inp.focus();
  }
}

function chatSend() {
  const inp = document.getElementById("chatInput");
  if (!inp) return;
  sendMessage(inp.value);
}

function chatKeyDown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatSend();
  }
}

function chatInputUpdate(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 100) + "px";
  showFilteredSuggestions(el.value.trim());
}

/* ═══════════════════════════════════════════════
   CTRL+K — Быстрый доступ к AI чату
═══════════════════════════════════════════════ */
document.addEventListener("keydown", function (e) {
  if ((e.ctrlKey || e.metaKey) && e.key === "k") {
    e.preventDefault();
    if (!chatOpen) toggleChat();
    else {
      var inp = document.getElementById("chatInput");
      if (inp) inp.focus();
    }
  }
  // Escape — закрыть чат
  if (e.key === "Escape" && chatOpen) toggleChat();
});

// Подсказка Ctrl+K в навбаре
(function () {
  var support = document.querySelector(".nav-support");
  if (!support) return;
  var hint = document.createElement("span");
  hint.style.cssText =
    "font-size:.6rem;background:rgba(255,255,255,.1);padding:.1rem .3rem;border-radius:3px;margin-left:.4rem;font-family:monospace";
  hint.textContent = "Ctrl+K";
  support.parentNode &&
    support.parentNode.insertBefore(hint, support.nextSibling);
})();

/* ═══════════════════════════════════════════════
   TYPEWRITER — Hero субтитл
═══════════════════════════════════════════════ */
(function () {
  var el = document.getElementById("typewriter");
  if (!el) return;

  var phrases = [
    "Персональный AI-ассистент с голосовым управлением.",
    "GigaChat без VPN. Русский язык. Бесплатно.",
    "Открывай программы голосом. Как джедай Старк.",
    "6 TTS движков. Выбери свой голос.",
    "Джарвис всегда на связи.",
  ];

  var pi = 0,
    ci = 0,
    deleting = false;

  function tick() {
    var phrase = phrases[pi];
    if (!deleting) {
      el.textContent = phrase.slice(0, ++ci);
      if (ci === phrase.length) {
        setTimeout(function () {
          deleting = true;
        }, 2200);
        setTimeout(tick, 2400);
        return;
      }
      setTimeout(tick, 45);
    } else {
      el.textContent = phrase.slice(0, --ci);
      if (ci === 0) {
        deleting = false;
        pi = (pi + 1) % phrases.length;
        setTimeout(tick, 400);
        return;
      }
      setTimeout(tick, 22);
    }
  }
  setTimeout(tick, 600);
})();

/* ═══════════════════════════════════════════════
   ОНЛАЙН СЧЕТЧИК
═══════════════════════════════════════════════ */
(function () {
  var bar = document.getElementById("onlineBar");
  var num = document.getElementById("onlineCount");
  if (!bar || !num) return;

  function ping() {
    fetch("/api/online")
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        num.textContent = d.online || 1;
        bar.style.opacity = "1";
      })
      .catch(function () {});
  }

  ping();
  setInterval(ping, 30000); // обновлять каждые 30 секунд
})();

/* ═══════════════════════════════════════════════
   КОНФЕТТИ при скачивании
═══════════════════════════════════════════════ */
function launchConfetti() {
  var canvas = document.createElement("canvas");
  canvas.style.cssText =
    "position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999";
  document.body.appendChild(canvas);
  var ctx = canvas.getContext("2d");
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  var pieces = [];
  var colors = [
    "#3b82f6",
    "#22c55e",
    "#f59e0b",
    "#ec4899",
    "#8b5cf6",
    "#06b6d4",
    "#fff",
  ];

  for (var i = 0; i < 120; i++) {
    pieces.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height - canvas.height,
      w: Math.random() * 10 + 4,
      h: Math.random() * 6 + 3,
      color: colors[Math.floor(Math.random() * colors.length)],
      rot: Math.random() * 360,
      vx: (Math.random() - 0.5) * 3,
      vy: Math.random() * 4 + 2,
      vr: (Math.random() - 0.5) * 6,
    });
  }

  var start = null;
  function frame(ts) {
    if (!start) start = ts;
    var elapsed = ts - start;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    pieces.forEach(function (p) {
      p.x += p.vx;
      p.y += p.vy;
      p.rot += p.vr;
      ctx.save();
      ctx.translate(p.x + p.w / 2, p.y + p.h / 2);
      ctx.rotate((p.rot * Math.PI) / 180);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = Math.max(0, 1 - elapsed / 2800);
      ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      ctx.restore();
    });
    if (elapsed < 3000) requestAnimationFrame(frame);
    else canvas.remove();
  }
  requestAnimationFrame(frame);
}

// Навешиваем конфетти на кнопку Скачать
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll('a[href*="download"]').forEach(function (a) {
    a.addEventListener("click", function () {
      setTimeout(launchConfetti, 200);
    });
  });
});

/* ═══════════════════════════════════════════════
   ИНТЕРАКТИВНЫЙ ТЕРМИНАЛ
═══════════════════════════════════════════════ */
var TERM_RESPONSES = {
  привет: ["[ДЖАРВИС] Добро пожаловать, сэр. Чем могу помочь?"],
  "привет!": ["[ДЖАРВИС] Добрый день! Что желаешь, сэр?"],
  "что умеешь?": [
    "[ДЖАРВИС] Могу открывать программы, делать скриншоты,",
    "отвечать на вопросы через GigaChat,",
    "управлять музыкой, напоминать о делах и многое другое.",
  ],
  "открой браузер": [
    "[ДЖАРВИС] Запускаю Chrome...",
    "> Процесс chrome.exe запущен успешно. Готово, сэр.",
  ],
  "сделай скриншот": [
    "[ДЖАРВИС] Скриншот выполнен.",
    "> Сохранён: Desktop\screenshot_2025.png",
    "> Готово, сэр.",
  ],
  "который час?": [
    "[ДЖАРВИС] Сейчас " + new Date().toLocaleTimeString("ru") + ", сэр.",
  ],
  "расскажи шутку": [
    "[ДЖАРВИС] Почему роботы не пьют кофе?",
    "Потому что Java!",
  ],
  "выключи компьютер": [
    "[ДЖАРВИС] Подождите... а вы дочитали все важные файлы?",
    "> Шутка. Не выполняю без подтверждения хозяина.",
  ],
  "статус системы": [
    "[ДЖАРВИС] Система: АКТИВНА",
    "> CPU: 12% | RAM: 4.2 GB | GPU: NVIDIA OK",
    "> Сеть: ОНЛАЙН | GigaChat: ГОТОВ",
    "> Все системы в норме, сэр.",
  ],
};

var termHistory = [];
var termHistIdx = -1;

function termPrint(text, color) {
  var out = document.getElementById("termOutput");
  if (!out) return;
  var line = document.createElement("div");
  line.style.color = color || "#8899b4";
  line.textContent = text;
  // Animate char by char for bot responses
  if (color === "#4ade80" || color === "#94a3b8") {
    line.textContent = "";
    out.appendChild(line);
    var i = 0;
    var iv = setInterval(function () {
      line.textContent += text[i++];
      out.scrollTop = out.scrollHeight;
      if (i >= text.length) clearInterval(iv);
    }, 18);
  } else {
    out.appendChild(line);
  }
  out.scrollTop = out.scrollHeight;
}

function termSend(cmd) {
  cmd = (cmd || "").trim();
  if (!cmd) return;
  var inp = document.getElementById("termInput");
  if (inp) inp.value = "";

  // История
  termHistory.unshift(cmd);
  termHistIdx = -1;

  // Показываем ввод
  termPrint("jarvis@ai:~$ " + cmd, "#60a5fa");

  var key = cmd
    .toLowerCase()
    .replace(/[!?.]+$/, "")
    .trim();
  var lines = TERM_RESPONSES[key];

  if (!lines) {
    // Нет в базе — генерируем универсальный ответ
    var generic = [
      '[ДЖАРВИС] Понял команду: "' + cmd + '". Выполняю, сэр.',
      "[ДЖАРВИС] Запрос обработан. Что-то ещё, сэр?",
      "[ДЖАРВИС] Процесс запущен. Задача выполнена.",
    ];
    lines = [generic[Math.floor(Math.random() * generic.length)]];
  }

  var delay = 350;
  lines.forEach(function (line) {
    setTimeout(function () {
      termPrint(line, line.startsWith("[") ? "#4ade80" : "#94a3b8");
    }, delay);
    delay += line.length * 18 + 200;
  });
}

function clearTerminal() {
  var out = document.getElementById("termOutput");
  if (out)
    out.innerHTML =
      '<div style="color:#3b82f6">[JARVIS] Система готова. Введите команду.</div>';
}

// Навигация по истории в терминале
document.addEventListener("DOMContentLoaded", function () {
  var inp = document.getElementById("termInput");
  if (!inp) return;
  inp.addEventListener("keydown", function (e) {
    if (e.key === "ArrowUp") {
      e.preventDefault();
      termHistIdx = Math.min(termHistIdx + 1, termHistory.length - 1);
      inp.value = termHistory[termHistIdx] || "";
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      termHistIdx = Math.max(termHistIdx - 1, -1);
      inp.value = termHistIdx < 0 ? "" : termHistory[termHistIdx];
    }
  });
});

/* ═══════════════════════════════════════════════
   CSS анимации (в JS для простоты)
═══════════════════════════════════════════════ */
(function () {
  var style = document.createElement("style");
  style.textContent = `
    @keyframes pulse-dot {
      0%,100% { box-shadow: 0 0 6px #22c55e; }
      50%      { box-shadow: 0 0 12px #22c55e, 0 0 20px rgba(34,197,94,.4); }
    }
    .tw-cursor {
      display: inline-block;
      color: #3b82f6;
      animation: blink-cursor .75s step-end infinite;
    }
    @keyframes blink-cursor {
      0%,100% { opacity: 1; }
      50%      { opacity: 0; }
    }
  `;
  document.head.appendChild(style);
})();

/* ═══════════════════════════════════════════════
   SETTINGS PANEL — summer theme user toggle
═══════════════════════════════════════════════ */

// ─── Summer design toggle (user preference via localStorage) ───
(function () {
  var body = document.getElementById("appBody");
  if (!body) return;

  var siteSummer = body.classList.contains("summer");
  var userPref = localStorage.getItem("summer_design");

  // User has set a preference → override site setting
  if (userPref !== null) {
    if (userPref === "1") {
      body.classList.add("summer");
    } else {
      body.classList.remove("summer");
    }
  } else {
    // No user pref → use site setting
    if (siteSummer) {
      body.classList.add("summer");
    } else {
      body.classList.remove("summer");
    }
  }

  // Sync toggle checkbox state
  var toggle = document.getElementById("summerToggle");
  if (toggle) {
    toggle.checked = body.classList.contains("summer");
  }
})();

function toggleSummerDesign() {
  var body = document.getElementById("appBody");
  var toggle = document.getElementById("summerToggle");
  if (!body || !toggle) return;

  if (toggle.checked) {
    body.classList.add("summer");
    localStorage.setItem("summer_design", "1");
  } else {
    body.classList.remove("summer");
    localStorage.setItem("summer_design", "0");
  }
}

/* ═══════════════════════════════════════════════
   🥚 ПАСХАЛКИ
   ═══════════════════════════════════════════════ */

// ─── 1. Консоль ───
(function() {
  var msg = [
    "",
    "  ╔══════════════════════════════════╗",
    "  ║                                  ║",
    "  ║   %cJARVIS%c следит за тобой 👀       ║",
    "  ║                                  ║",
    "  ║   Не ломай ничего, а то обижусь  ║",
    "  ║                                  ║",
    "  ╚══════════════════════════════════╝",
    "",
    "  %cСекретный код: ↑↑↓↓←→←→BA%c",
    "",
  ].join('\n');
  console.log(msg, 'color:#06b6d4;font-weight:bold;font-size:14px;', '', 'color:#787888;font-size:12px;', '');

  // Фейковый детектор девтулзов
  var devwatch = 0;
  var checkDevTools = setInterval(function() {
    devwatch++;
    var w = window.outerWidth - window.innerWidth;
    if (w > 160 || window.outerHeight - window.innerHeight > 160) {
      if (devwatch > 5) {
        console.log('%c👀 Я тебя вижу', 'color:#f43f5e;font-size:20px;');
        console.log('%cНо ты всё равно классный, так что ладно', 'color:#787888;');
        clearInterval(checkDevTools);
      }
    }
  }, 500);
})();

// ─── 2. Konami Code ───
(function() {
  var keys = [];
  var secret = [38,38,40,40,37,39,37,39,66,65];
  document.addEventListener('keydown', function(e) {
    keys.push(e.keyCode);
    if (keys.length > secret.length) keys.shift();
    if (keys.length === secret.length && keys.every(function(k,i){return k===secret[i];})) {
      document.body.style.transition = 'box-shadow 2s';
      document.body.style.boxShadow = 'inset 0 0 200px rgba(168,85,247,0.5)';
      setTimeout(function() {
        document.body.style.boxShadow = 'inset 0 0 400px rgba(217,70,239,0.4)';
        setTimeout(function() {
          document.body.style.boxShadow = 'none';
          document.body.style.transition = '';
        }, 3000);
      }, 500);
      console.log('%c🎉 Konami Code activated! %c✨✨✨', 'color:#22c55e;font-size:16px;', 'color:#fbbf24;font-size:14px;');
    }
  });
})();

// ─── 3. Лого кликер ───
(function() {
  var logo = document.querySelector('.nav-logo');
  if (!logo) return;
  var clicks = 0;
  logo.addEventListener('click', function(e) {
    clicks++;
    if (clicks === 5) {
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed;inset:0;display:grid;place-items:center;z-index:9999;background:rgba(0,0,0,0.85);backdrop-filter:blur(10px);animation:fadeIn .3s;';
      el.innerHTML = '<div style="text-align:center;"><div style="font-size:4rem;margin-bottom:1rem;">🤖</div><div style="font-size:1.5rem;font-weight:700;color:#fff;margin-bottom:.5rem;">Ты нашёл пасхалку!</div><div style="color:var(--text-3);margin-bottom:1.5rem;">JARVIS говорит спасибо что ты есть ❤️</div><button onclick="this.parentElement.parentElement.remove()" style="background:var(--accent);color:#fff;border:none;padding:.6rem 1.4rem;border-radius:999px;font-weight:600;cursor:pointer;">Закрыть</button></div>';
      document.body.appendChild(el);
      clicks = 0;
      // Добавляем анимацию если её нет
      if (!document.getElementById('pixel-easter-style')) {
        var s = document.createElement('style');
        s.id = 'pixel-easter-style';
        s.textContent = '@keyframes fadeIn{from{opacity:0}to{opacity:1}}';
        document.head.appendChild(s);
      }
    }
  });
})();

// ─── 4. Фейковый "взлом" при нажатии определённых клавиш ───
(function() {
  var typed = '';
  document.addEventListener('keydown', function(e) {
    typed += e.key.toLowerCase();
    if (typed.length > 10) typed = typed.slice(-10);
    if (typed.includes('hacker') || typed.includes('хацкер')) {
      typed = '';
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9998;background:linear-gradient(90deg,#000,#0a0a0a);color:#0f0;font-family:monospace;font-size:13px;padding:8px 16px;text-align:center;animation:fadeIn .3s;border-bottom:1px solid #0f0;';
      el.textContent = '⚠️ ОБНАРУЖЕНА ХАКЕРСКАЯ АКТИВНОСТЬ — ШУТКА. JARVIS просто прикалывается.';
      document.body.prepend(el);
      setTimeout(function() { el.remove(); }, 4000);
    }
  });
})();

// ─── 5. Dance mode ───
(function() {
  var typed = '', styleEl = null;
  document.addEventListener('keydown', function(e) {
    typed += e.key.toLowerCase();
    if (typed.length > 12) typed = typed.slice(-12);
    if (typed.includes('dance') || typed.includes('танцуй')) {
      typed = '';
      if (styleEl) { styleEl.remove(); styleEl = null; return; }
      styleEl = document.createElement('style');
      styleEl.textContent = '*,*::before,*::after{animation:danceWobble .3s infinite!important}@keyframes danceWobble{0%,100%{transform:rotate(0deg) scale(1)}25%{transform:rotate(1deg) scale(1.01)}75%{transform:rotate(-1deg) scale(0.99)}}';
      document.head.appendChild(styleEl);
      var msg = document.createElement('div');
      msg.style.cssText = 'position:fixed;bottom:1rem;left:50%;transform:translateX(-50%);z-index:9999;background:var(--accent);color:#fff;padding:.5rem 1rem;border-radius:999px;font-weight:600;font-size:.9rem;animation:fadeIn .3s;cursor:pointer;';
      msg.textContent = '💃 Танец включён! Набери "dance" чтобы выключить';
      msg.id = 'dance-msg';
      msg.onclick = function() { if (styleEl) { styleEl.remove(); styleEl = null; } this.remove(); };
      document.body.appendChild(msg);
    }
  });
})();

// ─── 6. Правый клик 15 раз ───
(function() {
  var rclicks = 0;
  document.addEventListener('contextmenu', function() {
    rclicks++;
    if (rclicks === 15) {
      var msgs = ['Хватит кликать!', 'Ну сколько можно?', 'Правую кнопку заело?', 'Ты чего ищешь?', 'Тут ничего нет :)'];
      console.log('%c🐭 ' + msgs[Math.floor(Math.random() * msgs.length)], 'color:#fbbf24;font-size:16px;');
      rclicks = 0;
    }
  });
})();

// ─── 7. Ночной режим (23:00 - 5:59) ───
(function() {
  var h = new Date().getHours();
  if (h >= 23 || h < 6) {
    console.log('%c🌙 JARVIS говорит: уже поздно, иди спать!', 'color:#06b6d4;font-size:14px;');
  }
})();

// ─── 8. Rainbow borders ───
(function() {
  var typed = '', rb = null;
  document.addEventListener('keydown', function(e) {
    typed += e.key.toLowerCase();
    if (typed.length > 6) typed = typed.slice(-6);
    if (typed === 'rgb' || typed === 'радуга') {
      typed = '';
      if (rb) { rb.remove(); rb = null; return; }
      rb = document.createElement('style');
      rb.textContent = '.navbar,.ann-bar,.cta-card,.sub-card,.pixel-frame-inner,.marquee-section{border-image:linear-gradient(90deg,var(--accent),var(--accent-2),var(--accent-3),var(--gold),var(--success),var(--accent))1!important;border-color:transparent!important;border-width:2px!important;border-style:solid!important;box-shadow:0 0 20px rgba(168,85,247,0.3)!important;transition:box-shadow .3s;}';
      document.head.appendChild(rb);
      console.log('%c🌈 RGB MODE — набери rgb снова чтобы выключить', 'color:var(--accent);font-size:14px;');
    }
  });
})();

// ─── 9. Клик по орбу 5 раз ───
(function() {
  var orbClicks = 0;
  document.addEventListener('click', function(e) {
    var orb = e.target.closest('.hero-orb-stage, .core, .ring');
    if (!orb) return;
    orbClicks++;
    if (orbClicks === 5) {
      orbClicks = 0;
      var flash = document.createElement('div');
      flash.style.cssText = 'position:fixed;inset:0;z-index:9998;pointer-events:none;background:radial-gradient(circle at center,rgba(168,85,247,0.6),transparent 60%);animation:fadeOut 2s forwards;';
      document.body.appendChild(flash);
      setTimeout(function() { flash.remove(); }, 2000);
      if (!document.getElementById('orb-style')) {
        var s = document.createElement('style');
        s.id = 'orb-style';
        s.textContent = '@keyframes fadeOut{from{opacity:1}to{opacity:0}}';
        document.head.appendChild(s);
      }
    }
  });
})();

// ─── 10. Matrix mode ───
(function() {
  var typed = '', mx = null, mxOverlay = null;
  document.addEventListener('keydown', function(e) {
    typed += e.key.toLowerCase();
    if (typed.length > 8) typed = typed.slice(-8);
    if (typed.includes('matrix') || typed.includes('матрица')) {
      typed = '';
      if (mxOverlay) { mxOverlay.remove(); mxOverlay = null; return; }
      mxOverlay = document.createElement('div');
      mxOverlay.style.cssText = 'position:fixed;inset:0;z-index:9997;background:rgba(0,20,0,0.85);display:grid;place-items:center;font-family:monospace;font-size:3rem;color:#0f0;text-shadow:0 0 20px #0f0;animation:fadeIn .5s;cursor:pointer;';
      mxOverlay.textContent = '01001010 01000001 01010010 01010110 01001001 01010011';
      mxOverlay.title = 'Кликни чтобы выйти';
      mxOverlay.onclick = function() { this.remove(); mxOverlay = null; };
      document.body.appendChild(mxOverlay);
      var s = document.createElement('style');
      s.id = 'mx-style';
      s.textContent = '@keyframes matrixFade{0%{opacity:0;transform:scale(.8)}100%{opacity:1;transform:scale(1)}}';
      document.head.appendChild(s);
    }
  });
})();

// ─── 11. Скролл-пасхалка ───
(function() {
  var triggered = false;
  window.addEventListener('scroll', function() {
    if (triggered) return;
    var scrollPct = window.scrollY / (document.body.scrollHeight - window.innerHeight) * 100;
    if (scrollPct > 68 && scrollPct < 70) {
      triggered = true;
      console.log('%c👌 69% — Nice.', 'color:#22c55e;font-size:18px;');
      setTimeout(function() { triggered = false; }, 5000);
    }
  }, {passive: true});
})();

// ─── 12. Ping / Pong ───
(function() {
  var typed = '';
  document.addEventListener('keydown', function(e) {
    typed += e.key.toLowerCase();
    if (typed.length > 4) typed = typed.slice(-4);
    if (typed === 'ping') {
      typed = '';
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:9999;font-size:5rem;font-weight:900;color:var(--accent);animation:fadeOut 1.5s forwards;pointer-events:none;';
      el.textContent = 'PONG! 🏓';
      document.body.appendChild(el);
      setTimeout(function() { el.remove(); }, 1500);
    }
  });
})();

// ─── 13. Фейковый апдейт в футере ───
(function() {
  var footer = document.querySelector('footer');
  if (!footer) return;
  footer.addEventListener('dblclick', function() {
    var el = document.createElement('div');
    el.style.cssText = 'margin-top:.5rem;font-size:.75rem;color:var(--text-4);animation:fadeIn .3s;text-align:center;';
    el.textContent = '🛸 JARVIS v3.14.15 · сборка 42 · загружено нейросетей: ' + Math.floor(Math.random() * 9999);
    this.appendChild(el);
    setTimeout(function() { el.remove(); }, 5000);
  });
})();

// ─── 14. Секретный /42 ───
(function() {
  var typed = '';
  document.addEventListener('keydown', function(e) {
    typed += e.key;
    if (typed.length > 2) typed = typed.slice(-2);
    if (typed === '42') {
      typed = '';
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed;inset:0;z-index:9999;display:grid;place-items:center;background:rgba(0,0,0,0.9);animation:fadeIn .5s;cursor:pointer;';
      el.innerHTML = '<div style="text-align:center;"><div style="font-size:6rem;font-weight:900;background:linear-gradient(135deg,var(--accent),var(--accent-2));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;">42</div><div style="color:var(--text-3);margin-top:.5rem;">Ответ на главный вопрос жизни, вселенной и всего такого</div><div style="color:var(--text-4);font-size:.85rem;margin-top:.3rem;">(кликни чтобы закрыть)</div></div>';
      el.onclick = function() { this.remove(); };
      document.body.appendChild(el);
    }
  });
})();

// ─── 15. Фейковая загрузка ───
(function() {
  var typed = '';
  document.addEventListener('keydown', function(e) {
    typed += e.key.toLowerCase();
    if (typed.length > 8) typed = typed.slice(-8);
    if (typed.includes('загруз') || typed.includes('downl')) {
      typed = '';
      var bar = document.createElement('div');
      bar.style.cssText = 'position:fixed;bottom:0;left:0;right:0;z-index:9998;background:var(--bg-2);border-top:1px solid var(--line);padding:12px 16px;animation:fadeIn .3s;';
      bar.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;max-width:400px;margin:0 auto;"><span style="color:var(--text-2);font-size:.85rem;">📦 Загрузка JARVIS...</span><span style="color:var(--text-3);font-size:.75rem;" id="fake-progress">0%</span></div><div style="max-width:400px;margin:6px auto 0;height:6px;background:var(--bg-3);border-radius:3px;overflow:hidden;"><div style="height:100%;width:0;background:linear-gradient(90deg,var(--accent),var(--accent-2));border-radius:3px;transition:width .5s;" id="fake-bar"></div></div>';
      document.body.appendChild(bar);
      var pct = 0;
      var iv = setInterval(function() {
        pct += Math.floor(Math.random() * 15) + 3;
        if (pct >= 100) {
          pct = 100;
          clearInterval(iv);
          document.getElementById('fake-progress').textContent = '100%';
          document.getElementById('fake-bar').style.width = '100%';
          setTimeout(function() {
            bar.innerHTML = '<div style="text-align:center;color:var(--text-2);font-size:.85rem;max-width:400px;margin:0 auto;">✅ Загрузка завершена. Шутка. Ничего не загрузилось :)</div>';
            setTimeout(function() { bar.remove(); }, 3000);
          }, 800);
        }
        document.getElementById('fake-progress').textContent = pct + '%';
        document.getElementById('fake-bar').style.width = pct + '%';
      }, 400);
    }
  });
})();

// ─── 16. Секретная тема «Катастрофа» ───
(function() {
  var typed = '';
  document.addEventListener('keydown', function(e) {
    typed += e.key.toLowerCase();
    if (typed.length > 8) typed = typed.slice(-8);
    if (typed.includes('fire') || typed.includes('огонь') || typed.includes('пожар')) {
      typed = '';
      var s = document.createElement('style');
      s.id = 'fire-style';
      s.textContent = 'body{animation:fireShake .1s infinite!important}@keyframes fireShake{0%{transform:translate(-1px,-1px)}25%{transform:translate(1px,-1px)}50%{transform:translate(-1px,1px)}75%{transform:translate(1px,1px)}}';
      document.head.appendChild(s);
      ['.navbar','.hero-content','.section','footer','.ann-bar'].forEach(function(sel) {
        document.querySelectorAll(sel).forEach(function(el) {
          el.style.filter = 'hue-rotate(' + Math.floor(Math.random()*360) + 'deg) drop-shadow(0 0 10px rgba(255,0,0,0.5))';
        });
      });
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:9999;font-size:3rem;font-weight:900;color:#ff4500;text-shadow:0 0 40px #ff4500;pointer-events:none;animation:fadeOut 3s forwards;';
      el.textContent = '🔥🔥🔥';
      document.body.appendChild(el);
      setTimeout(function() { el.remove(); document.getElementById('fire-style')?.remove(); location.reload(); }, 4000);
    }
  });
})();

// ─── 17. Секретный счётчик ───
(function() {
  var c = 0;
  document.addEventListener('click', function() {
    c++;
    if (c === 100) {
      console.log('%c🎯 100 кликов! Ты усидчивый.', 'color:#06b6d4;font-size:16px;');
    }
    if (c === 500) {
      console.log('%c🏆 500 кликов! Может отдохнёшь?', 'color:#fbbf24;font-size:18px;');
    }
  });
})();

// ─── 18. Кот в консоли ───
console.log(
  '%c   /\\_/\\  \n  ( o.o ) \n   > ^ <  \n %cМяу. JARVIS одобряет твой выбор браузера.',
  'color:#fbbf24;font-size:14px;',
  'color:#787888;font-size:12px;'
);

// ─── 19. Фейковый Bitcoin ───
(function() {
  var typed = '';
  document.addEventListener('keydown', function(e) {
    typed += e.key.toLowerCase();
    if (typed.length > 7) typed = typed.slice(-7);
    if (typed === 'bitcoin' || typed === 'биткоин') {
      typed = '';
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed;top:1rem;right:1rem;z-index:9999;background:linear-gradient(135deg,#f7931a,#fbbf24);color:#fff;padding:.6rem 1rem;border-radius:12px;font-weight:700;font-size:.9rem;animation:fadeIn .3s;cursor:pointer;box-shadow:0 8px 24px rgba(247,147,26,0.4);';
      el.innerHTML = '₿ 1 BTC = $' + (Math.floor(Math.random() * 50000 + 50000)) + ' 🚀<br><span style="font-size:.7rem;opacity:.8;">+420.69% за сегодня</span>';
      el.title = 'Кликни чтобы закрыть';
      el.onclick = function() { this.remove(); };
      document.body.appendChild(el);
    }
  });
})();

// ─── 20. Телепорт курсора в консоль ───
(function() {
  var typed = '';
  document.addEventListener('keydown', function(e) {
    typed += e.key.toLowerCase();
    if (typed.length > 5) typed = typed.slice(-5);
    if (typed === 'where' || typed === 'where') {
      typed = '';
      console.log('%c📍 Ты здесь. А где JARVIS? Он везде.', 'color:#22c55e;font-size:14px;');
      console.log('%c👁️ _  👁️', 'color:#06b6d4;font-size:20px;');
    }
  });
})();

// ─── 21. Фейковый звонок ───
(function() {
  var typed = '';
  document.addEventListener('keydown', function(e) {
    typed += e.key.toLowerCase();
    if (typed.length > 4) typed = typed.slice(-4);
    if (typed === 'call' || typed === 'звони') {
      typed = '';
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:9999;background:var(--bg-2);border:1px solid var(--line-2);border-radius:20px;padding:2rem;text-align:center;min-width:280px;animation:fadeIn .3s;box-shadow:0 40px 80px rgba(0,0,0,0.6);';
      el.innerHTML = '<div style="font-size:3rem;margin-bottom:.5rem;">📞</div><div style="font-weight:700;font-size:1.1rem;color:var(--text);">JARVIS звонит...</div><div style="color:var(--text-3);font-size:.85rem;margin:.3rem 0 1rem;">входящий вызов от GigaChat</div><div style="display:flex;gap:.6rem;justify-content:center;"><button onclick="this.closest(\'[style]\').remove()" style="background:var(--danger);color:#fff;border:none;padding:.5rem 1.2rem;border-radius:999px;font-weight:600;cursor:pointer;">Сбросить</button><button onclick="this.closest(\'[style]\').remove()" style="background:var(--success);color:#fff;border:none;padding:.5rem 1.2rem;border-radius:999px;font-weight:600;cursor:pointer;">Ответить</button></div>';
      document.body.appendChild(el);
    }
  });
})();

// ─── 22. Секретный скринсейвер ───
(function() {
  var idleTimer = null;
  function resetIdle() { if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; } }
  document.addEventListener('mousemove', resetIdle);
  document.addEventListener('keydown', resetIdle);
  document.addEventListener('click', resetIdle);
  document.addEventListener('mousedown', resetIdle);
  var styleSS = null;
  idleTimer = setTimeout(function() {
    styleSS = document.createElement('style');
    styleSS.textContent = 'body::after{content:"JARVIS";position:fixed;inset:0;display:grid;place-items:center;font-size:8rem;font-weight:900;color:rgba(168,85,247,0.03);pointer-events:none;z-index:9999;animation:ssFloat 8s ease-in-out infinite;}@keyframes ssFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-20px)}}';
    document.head.appendChild(styleSS);
  }, 300000); // 5 минут
})();

// ─── 23-62: 40 пасхалок ───
(function() {
  var buff = '';
  var E = {
    handle: function(key, match, fn) {
      buff += key;
      if (buff.length > 20) buff = buff.slice(-20);
      if (buff.includes(match)) { buff = ''; fn(); }
    },
    msg: function(t, c) { console.log('%c' + t, 'color:' + (c || '#06b6d4') + ';font-size:13px;'); },
    pop: function(html, w) {
      var e = document.createElement('div');
      e.style.cssText = 'position:fixed;' + (w || 'top:50%;left:50%;transform:translate(-50%,-50%);z-index:9999;') + 'animation:fadeIn .3s;cursor:pointer;';
      e.innerHTML = html;
      e.onclick = function() { this.remove(); };
      document.body.appendChild(e);
    },
    bar: function(t) {
      var e = document.createElement('div');
      e.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9998;background:var(--bg-2);border-bottom:1px solid var(--line);padding:8px 16px;text-align:center;color:var(--text-2);font-size:.85rem;animation:fadeIn .3s;cursor:pointer;';
      e.textContent = t;
      e.onclick = function() { this.remove(); };
      document.body.prepend(e);
    }
  };

  document.addEventListener('keydown', function(e) {
    var k = e.key.toLowerCase();

    // 23 — sith / дарт
    E.handle(k, 'sith', function() {
      document.body.style.filter = 'hue-rotate(180deg) sepia(0.5)';
      E.msg('🖤 Dark side accepted', '#ef4444');
      setTimeout(function() { document.body.style.filter = ''; }, 5000);
    });

    // 24 — pizza
    E.handle(k, 'pizza', function() {
      E.pop('<div style="font-size:6rem;text-align:center;">🍕<div style="color:var(--text-3);font-size:.9rem;margin-top:.3rem;">Спасибо что заказал пиццу. Через 30 минут будет.</div></div>');
    });

    // 25 — coffee / кофе
    E.handle(k, 'coffee', function() {
      E.bar('☕ JARVIS варит тебе кофе... готово. Наслаждайся!');
    });

    // 26 — beer / пиво
    E.handle(k, 'beer', function() {
      E.pop('<div style="font-size:5rem;text-align:center;">🍺<div style="color:var(--text-3);font-size:.85rem;">За JARVIS! 🥂</div></div>');
    });

    // 27 — banana / банан
    E.handle(k, 'banana', function() {
      E.bar('🍌 Банановый JARVIS — новый сорт. Сладкий и быстрый.');
    });

    // 28 — fox / лиса
    E.handle(k, 'fox', function() {
      E.msg('🦊 What does the fox say? Ding-ding-ding-ding-dingeringeding!', '#f97316');
    });

    // 29 — shark / акула
    E.handle(k, 'shark', function() {
      E.msg('🦈 Baby shark doo doo doo doo doo doo', '#22c55e');
    });

    // 30 — ghost / призрак
    E.handle(k, 'ghost', function() {
      E.pop('<div style="font-size:6rem;text-align:center;">👻<div style="color:var(--text-3);font-size:.85rem;">БУ! Испугался? JARVIS и не такое умеет.</div></div>');
    });

    // 31 — alien / инопланет
    E.handle(k, 'alien', function() {
      E.bar('👽 JARVIS связался с Альфой Центавра. Ответ: «Привет, земляне!»');
    });

    // 32 — robot / робот
    E.handle(k, 'robot', function() {
      E.pop('<div style="font-size:5rem;text-align:center;">🤖<div style="font-family:monospace;color:#0f0;font-size:.8rem;">01101010 01100001 01110010 01110110 01101001 01110011</div><div style="color:var(--text-4);font-size:.75rem;">Перевод: JARVIS</div></div>');
    });

    // 33 — star / звезда
    E.handle(k, 'star', function() {
      document.body.style.background = '#050508 radial-gradient(circle at ' + (Math.random()*100) + '% ' + (Math.random()*100) + '%, rgba(255,215,0,0.15), transparent 50%)';
      E.msg('⭐ Звезда зажглась!', '#fbbf24');
      setTimeout(function() { document.body.style.background = ''; }, 3000);
    });

    // 34 — moon / луна
    E.handle(k, 'moon', function() {
      E.pop('<div style="font-size:5rem;text-align:center;">🌙<div style="color:var(--text-3);font-size:.85rem;">JARVIS на Луне. Связь нестабильная. Приём.</div></div>');
    });

    // 35 — sun / солнце
    E.handle(k, 'sun', function() {
      E.bar('☀️ JARVIS вышел на солнышко. Температура ядра: 15 млн °C. Жарковато.');
    });

    // 36 — rain / дождь
    E.handle(k, 'rain', function() {
      var s = document.createElement('style');
      s.id = 'rain-style';
      s.textContent = 'body{background:linear-gradient(180deg,#1a1a2e,#16213e) fixed!important}';
      document.head.appendChild(s);
      E.msg('🌧️ Дождь идёт... JARVIS грустит.', '#5ac8fa');
      setTimeout(function() { document.getElementById('rain-style')?.remove(); }, 5000);
    });

    // 37 — snow / снег
    E.handle(k, 'snow', function() {
      for (var i = 0; i < 50; i++) {
        (function() {
          var flake = document.createElement('div');
          flake.style.cssText = 'position:fixed;top:-10px;left:' + Math.random()*100 + 'vw;z-index:9999;font-size:' + (Math.random()*10+10) + 'px;color:#fff;opacity:' + (Math.random()*0.5+0.3) + ';pointer-events:none;animation:snowFall ' + (Math.random()*3+3) + 's linear forwards;';
          flake.textContent = '❄';
          document.body.appendChild(flake);
          setTimeout(function() { flake.remove(); }, 6000);
        })();
      }
      var s = document.createElement('style');
      s.textContent = '@keyframes snowFall{to{transform:translateY(100vh) rotate(360deg)}}';
      document.head.appendChild(s);
    });

    // 38 — thunder / гром
    E.handle(k, 'thunder', function() {
      document.body.style.background = '#fff';
      setTimeout(function() { document.body.style.background = ''; }, 100);
      E.bar('⚡ МОЛНИЯ! JARVIS вызвал грозу.');
    });

    // 39 — boom / бабах
    E.handle(k, 'boom', function() {
      for (var i = 0; i < 20; i++) {
        (function() {
          var p = document.createElement('div');
          p.style.cssText = 'position:fixed;' + ['top','left','right','bottom'][Math.floor(Math.random()*4)] + ':' + Math.random()*50 + 'px;z-index:9999;font-size:' + (Math.random()*20+20) + 'px;pointer-events:none;animation:fadeOut .5s forwards;color:' + ['#ff3b30','#ff9500','#ffcc00','#34c759','#5ac8fa','#06b6d4'][Math.floor(Math.random()*6)] + ';';
          p.textContent = ['💥','✨','🔥','⭐','💫','🎆'][Math.floor(Math.random()*6)];
          document.body.appendChild(p);
          setTimeout(function() { p.remove(); }, 500);
        })();
      }
    });

    // 40 — secret / секрет
    E.handle(k, 'secret', function() {
      E.pop('<div style="text-align:center;"><div style="font-size:4rem;">🤫</div><div style="color:var(--text-2);font-size:1.1rem;max-width:300px;">Секрет JARVIS: он на самом деле не ИИ, а просто очень быстрый хомяк в колесе.</div></div>');
    });

    // 41 — love / любовь
    E.handle(k, 'love', function() {
      for (var i = 0; i < 15; i++) {
        (function() {
          var h = document.createElement('div');
          h.style.cssText = 'position:fixed;top:' + Math.random()*80 + 'vh;left:' + Math.random()*100 + 'vw;z-index:9999;font-size:' + (Math.random()*20+16) + 'px;animation:fadeOut 2s forwards;pointer-events:none;';
          h.textContent = '❤️';
          document.body.appendChild(h);
          setTimeout(function() { h.remove(); }, 2000);
        })();
      }
      E.msg('❤️ JARVIS тоже тебя любит!', '#ff3b30');
    });

    // 42 — nyan / нян
    E.handle(k, 'nyan', function() {
      var c = document.createElement('div');
      c.style.cssText = 'position:fixed;bottom:20px;left:-200px;z-index:9999;font-size:3rem;animation:nyanFly 4s linear forwards;pointer-events:none;';
      c.textContent = '🌈🐱🌈';
      document.body.appendChild(c);
      var s = document.createElement('style');
      s.textContent = '@keyframes nyanFly{to{transform:translateX(120vw)}}';
      document.head.appendChild(s);
      setTimeout(function() { c.remove(); }, 4000);
    });

    // 43 — power / сила
    E.handle(k, 'power', function() {
      document.querySelectorAll('.btn').forEach(function(b) {
        b.style.transform = 'scale(1.2)';
        b.style.transition = 'transform .3s';
        setTimeout(function() { b.style.transform = ''; }, 1000);
      });
      E.msg('💪 POWER OVERWHELMING', '#f43f5e');
    });

    // 44 — glow / свет
    E.handle(k, 'glow', function() {
      var s = document.createElement('style');
      s.id = 'glow-style';
      s.textContent = '.hero,.section,.navbar,.footer{filter:drop-shadow(0 0 20px rgba(168,85,247,0.5))!important}';
      document.head.appendChild(s);
      setTimeout(function() { document.getElementById('glow-style')?.remove(); }, 4000);
    });

    // 45 — flip / переворот
    E.handle(k, 'flip', function() {
      document.body.style.transition = 'transform 1s';
      document.body.style.transform = 'rotate(180deg)';
      setTimeout(function() { document.body.style.transform = ''; }, 3000);
    });

    // 46 — reverse / реверс
    E.handle(k, 'reverse', function() {
      E.bar('🔄 JARVIS запустил реверс-инжиниринг... самого себя. Результат: JARVIS.');
    });

    // 47 — troll / тролль
    E.handle(k, 'troll', function() {
      E.pop('<div style="font-size:5rem;text-align:center;">🧌<div style="color:var(--text-3);font-size:.85rem;">Trollface обнаружен. JARVIS проигнорировал.</div></div>');
    });

    // 48 — duck / утка
    E.handle(k, 'duck', function() {
      E.msg('🦆 Утка — не баг, а фича. Утка — это образ жизни.', '#fbbf24');
    });

    // 49 — wiggle / вилять
    E.handle(k, 'wiggle', function() {
      document.querySelectorAll('.nav-links a, .btn, .hero-title, h2').forEach(function(el, i) {
        el.style.animation = 'wiggleAnim ' + (Math.random()*0.5+0.3) + 's ease-in-out ' + (i*0.05) + 's';
        setTimeout(function() { el.style.animation = ''; }, 2000);
      });
      var s = document.createElement('style');
      s.textContent = '@keyframes wiggleAnim{0%,100%{transform:rotate(0deg)}25%{transform:rotate(3deg)}75%{transform:rotate(-3deg)}}';
      document.head.appendChild(s);
    });

    // 50 — glitch / глитч
    E.handle(k, 'glitch', function() {
      var s = document.createElement('style');
      s.id = 'glitch-style';
      s.textContent = 'h1,h2,h3,p,a,.btn{animation:glitch .2s infinite!important}@keyframes glitch{0%{transform:translate(2px,1px) skew(-1deg)}50%{transform:translate(-2px,-1px) skew(1deg)}100%{transform:translate(0)}}';
      document.head.appendChild(s);
      E.msg('🖥️ Glitch effect activated', '#22c55e');
      setTimeout(function() { document.getElementById('glitch-style')?.remove(); }, 3000);
    });

    // 51 — jeb / еб...
    E.handle(k, 'jeb', function() {
      E.bar('👀 JARVIS всё видел. И он разочарован.');
    });

    // 52 — lol
    E.handle(k, 'lol', function() {
      E.pop('<div style="font-size:5rem;text-align:center;">😂<div style="color:var(--text-3);font-size:.85rem;">JARVIS тоже смеётся. Над тобой. Шучу. Или нет?</div></div>');
    });

    // 53 — wow / вау
    E.handle(k, 'wow', function() {
      E.pop('<div style="font-size:5rem;text-align:center;">😮<div style="color:var(--text-2);font-size:1.1rem;">JARVIS впечатлён твоими навыками!</div></div>');
    });

    // 54 — omg
    E.handle(k, 'omg', function() {
      E.bar('😱 OMG! JARVIS сказал OMG! Это исторический момент!');
    });

    // 55 — brb
    E.handle(k, 'brb', function() {
      E.bar('🏃 JARVIS отошёл. Вернётся через 5 минут. (спойлер: не вернётся)');
    });

    // 56 — gg
    E.handle(k, 'gg', function() {
      E.bar('🎮 GG WP! JARVIS признаёт твоё превосходство.');
    });

    // 57 — ez
    E.handle(k, 'ez', function() {
      E.bar('😎 EZ. JARVIS мог бы и лучше, но ему лень.');
    });

    // 58 — rip / рест
    E.handle(k, 'rip', function() {
      E.pop('<div style="text-align:center;"><div style="font-size:5rem;">🪦</div><div style="color:var(--text-3);font-size:.9rem;">RIP JARVIS 2024-2026<br>Умер от смеха над твоими шутками</div></div>');
    });

    // 59 — admin / админ
    E.handle(k, 'admin', function() {
      E.bar('🔐 Доступ запрещён. Шучу. Пароль: xcv***** (нет, не скажу)');
    });

    // 60 — password / пароль
    E.handle(k, 'password', function() {
      E.bar('🔑 Пароль: ******** (на самом деле просто "1234", но никому не говори)');
    });

    // 61 — google
    E.handle(k, 'google', function() {
      E.pop('<div style="text-align:center;"><div style="font-size:4rem;">🔍</div><div style="color:var(--text-3);font-size:.85rem;">JARVIS отправил запрос в Google. Результат: «ты сам нашёл эту пасхалку, лол»</div></div>');
    });

    // 62 — music / муз
    E.handle(k, 'music', function() {
      E.msg('🎵 JARVIS включает твой плэйлист... ♪ Never gonna give you up ♪', '#22c55e');
    });
  });
})();

// ─── 63-72: Клик-пасхалки ───
(function() {
  var sc = 0, cc = 0, fc = 0, dc = 0, ac = 0;

  // 63 — Клик по цифрам /download
  document.addEventListener('click', function(e) {
    var txt = e.target.textContent || '';
    if (txt.includes('V2') || txt.includes('2.2')) {
      cc++;
      if (cc === 3) {
        cc = 0;
        var el = document.createElement('div');
        el.style.cssText = 'position:fixed;bottom:0;left:0;right:0;z-index:9998;background:linear-gradient(90deg,var(--accent),var(--accent-2));color:#fff;padding:10px 16px;text-align:center;font-size:.85rem;animation:fadeIn .3s;cursor:pointer;';
        el.innerHTML = '📢 V3 уже в разработке! JARVIS станет ещё умнее. <span style="opacity:.7;font-size:.75rem;">(клик закрыть)</span>';
        el.onclick = function() { this.remove(); };
        document.body.appendChild(el);
      }
    }
  });

  // 64 — Клик по карточкам новостей
  document.addEventListener('click', function(e) {
    var card = e.target.closest('.news-card, .feature-card');
    if (!card) return;
    sc++;
    if (sc === 7) {
      sc = 0;
      console.log('%c📰 Ты перечитал все новости? JARVIS уважает.', '#5ac8fa;font-size:14px');
    }
  });

  // 65 — Клик по футеру 5 раз
  document.addEventListener('click', function(e) {
    var footer = e.target.closest('footer');
    if (!footer) return;
    fc++;
    if (fc === 5) {
      fc = 0;
      var p = document.createElement('div');
      p.style.cssText = 'margin-top:.5rem;font-size:.75rem;color:var(--text-4);text-align:center;animation:fadeIn .3s;';
      p.textContent = '👣 JARVIS насчитал ' + Math.floor(Math.random()*99999) + ' посещений этого сайта. Ты — особенное.';
      footer.appendChild(p);
      setTimeout(function() { p.remove(); }, 4000);
    }
  });

  // 66 — Двойной клик по заголовкам
  document.addEventListener('dblclick', function(e) {
    var h = e.target.closest('h1, h2, h3, h4');
    if (!h) return;
    var orig = h.textContent;
    h.style.transition = 'transform .3s, color .3s';
    h.style.transform = 'scale(1.1)';
    h.style.color = '#06b6d4';
    h.textContent = '👋 JARVIS здесь!';
    setTimeout(function() {
      h.style.transform = '';
      h.style.color = '';
      h.textContent = orig;
    }, 2000);
  });

  // 67 — Клик по нав-ссылкам 10 раз
  document.addEventListener('click', function(e) {
    var link = e.target.closest('.nav-links a');
    if (!link) return;
    dc++;
    if (dc === 10) {
      dc = 0;
      console.log('%c🧭 JARVIS может показать тебе мир. Ну или хотя бы этот сайт.', '#06b6d4;font-size:14px');
    }
  });

  // 68 — Клик по пустому месту 8 раз
  document.addEventListener('click', function(e) {
    if (e.target !== document.body && !e.target.closest('main, section, .container')) return;
    ac++;
    if (ac === 8) {
      ac = 0;
      var el = document.createElement('div');
      el.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:9999;background:var(--bg-2);border:1px solid var(--line-2);border-radius:16px;padding:2rem;text-align:center;min-width:200px;animation:fadeIn .3s;cursor:pointer;box-shadow:0 40px 80px rgba(0,0,0,0.6);';
      el.innerHTML = '<div style="font-size:3rem;margin-bottom:.5rem;">🤷</div><div style="color:var(--text-2);font-size:1rem;">Ты кликаешь в пустоту...<br>JARVIS не понимает, что ты ищешь, но желает удачи.</div>';
      el.onclick = function() { this.remove(); };
      document.body.appendChild(el);
    }
  });

  // 69 — Клик по бейджам
  document.addEventListener('click', function(e) {
    var badge = e.target.closest('.badge');
    if (!badge) return;
    badge.style.transition = 'all .3s';
    badge.style.transform = 'rotate(360deg) scale(1.3)';
    badge.style.background = 'linear-gradient(90deg,var(--accent),var(--accent-2))';
    badge.style.color = '#fff';
    setTimeout(function() {
      badge.style.transform = '';
      badge.style.background = '';
      badge.style.color = '';
    }, 1000);
  });

  // 70 — Shift+клик по ссылкам
  document.addEventListener('click', function(e) {
    if (!e.shiftKey) return;
    var a = e.target.closest('a[href]');
    if (!a) return;
    e.preventDefault();
    var el = document.createElement('div');
    el.style.cssText = 'position:fixed;inset:0;z-index:9999;display:grid;place-items:center;background:rgba(0,0,0,0.8);animation:fadeIn .3s;cursor:pointer;';
    el.innerHTML = '<div style="text-align:center;"><div style="font-size:3rem;">🚀</div><div style="color:var(--text-2);font-size:1rem;margin:.5rem 0;">Shift+клик активирует гиперпрыжок!</div><div style="color:var(--text-4);font-size:.85rem;">Но JARVIS решил никуда не прыгать. Останься с нами.</div></div>';
    el.onclick = function() { this.remove(); };
    document.body.appendChild(el);
  });

  // 71 — Ctrl+клик по картинкам
  document.addEventListener('click', function(e) {
    if (!e.ctrlKey) return;
    var img = e.target.closest('img');
    if (!img) return;
    e.preventDefault();
    img.style.transition = 'transform .5s, filter .5s';
    img.style.transform = 'scale(1.5) rotate(5deg)';
    img.style.filter = 'hue-rotate(90deg) saturate(3)';
    setTimeout(function() {
      img.style.transform = '';
      img.style.filter = '';
    }, 2000);
  });

  // 72 — Alt+клик
  document.addEventListener('click', function(e) {
    if (!e.altKey) return;
    console.log('%c🔮 Alt-реальность активирована. JARVIS видит альтернативную версию тебя. Она тоже на этом сайте.', '#06b6d4;font-size:13px');
  });
})();

// ─── Settings panel open/close ───
function toggleSettings() {
  var panel = document.getElementById("settingsPanel");
  var overlay = document.getElementById("settingsOverlay");
  if (!panel || !overlay) return;

  var isOpen = panel.classList.toggle("open");
  overlay.classList.toggle("open", isOpen);
  document.body.style.overflow = isOpen ? "hidden" : "";
}

// Close settings on Escape key
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    var panel = document.getElementById("settingsPanel");
    var overlay = document.getElementById("settingsOverlay");
    if (panel && panel.classList.contains("open")) {
      panel.classList.remove("open");
      overlay.classList.remove("open");
      document.body.style.overflow = "";
    }
  }
});
