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
