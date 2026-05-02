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
  // Auto-resize
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 100) + "px";
  // Фильтрация подсказок
  showFilteredSuggestions(el.value.trim());
}
