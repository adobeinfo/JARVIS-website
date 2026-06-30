const API = '';
let tg = null;
let user = null;
let currentPage = 'home';
let searchTimer = null;
let pageHistory = [];

try {
    tg = window.Telegram?.WebApp;
    if (tg) {
        tg.ready();
        tg.expand();
        tg.setHeaderColor('#0a0a0f');
        tg.setBackgroundColor('#0a0a0f');
        user = tg.initDataUnsafe?.user || null;
    }
} catch(e) {}

if (!tg) {
    user = { id: 123456789, first_name: 'Demo User', username: 'demo' };
}

function showPage(name) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const page = document.getElementById('page-' + name);
    if (page) {
        page.classList.add('active');
        page.querySelectorAll('.animate-in').forEach((el, i) => {
            el.style.animationDelay = (i * 0.05) + 's';
        });
    }
    document.querySelectorAll('.nav-item').forEach(n => {
        n.classList.toggle('active', n.dataset.page === name);
    });
    currentPage = name;
}

function loadPage(name, extra) {
    if (currentPage !== name) {
        pageHistory.push(currentPage);
    }
    showPage(name);
    if (name === 'home') loadHome();
    else if (name === 'popular') loadList('popular');
    else if (name === 'new') loadList('new');
    else if (name === 'premium') loadList('premium');
    else if (name === 'category' && extra) loadCategory(extra);
}

async function apiFetch(url, opts) {
    try {
        const r = await fetch(API + url, opts);
        return await r.json();
    } catch(e) {
        console.error('API error:', e);
        return null;
    }
}

function renderProjectCard(p, index) {
    const discount = p.discount_percent > 0
        ? Math.round(p.price - (p.price * p.discount_percent / 100))
        : p.price;
    const isFree = p.is_free || p.price === 0;
    const priceText = isFree ? 'Бесплатно' : `${discount} ⭐`;
    const badgeHtml = p.is_premium ? '<div class="project-badge premium">Premium</div>'
        : p.is_new ? '<div class="project-badge new">New</div>'
        : p.is_free ? '<div class="project-badge free">Free</div>'
        : p.discount_percent > 0 ? `<div class="project-badge">-${p.discount_percent}%</div>` : '';
    const imgHtml = p.cover_url && !p.cover_url.startsWith('AgAC')
        ? `<img class="project-cover" src="${p.cover_url}" alt="${p.title}" loading="lazy" onerror="this.outerHTML='<div class=\\'project-cover-placeholder\\'>🎬</div>'">`
        : `<div class="project-cover-placeholder">🎬</div>`;
    return `
        <div class="project-card animate-in" onclick="openProject(${p.id})" style="animation-delay:${(index||0)*0.05}s">
            ${badgeHtml}
            <button class="project-fav" onclick="event.stopPropagation();toggleFav(${p.id})">🤍</button>
            ${imgHtml}
            <div class="project-info">
                <div class="project-name">${esc(p.title)}</div>
                <div class="project-meta">
                    <span class="project-price ${isFree ? 'free' : ''}">${priceText}</span>
                    <span class="project-stats">📥 ${p.downloads || 0}</span>
                </div>
            </div>
        </div>`;
}

function esc(s) {
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
}

function gridHtml(projects, id) {
    const el = document.getElementById(id);
    if (!el) return;
    if (!projects || projects.length === 0) {
        el.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>Пока пусто</p></div>';
        return;
    }
    el.innerHTML = projects.slice(0, 10).map((p, i) => renderProjectCard(p, i)).join('');
}

async function loadHome() {
    const [cats, popular, fresh, prem] = await Promise.all([
        apiFetch('/api/categories'),
        apiFetch('/api/popular'),
        apiFetch('/api/new'),
        apiFetch('/api/premium'),
    ]);
    const cg = document.getElementById('categories-grid');
    if (cg && cats) {
        cg.innerHTML = cats.map(c => `
            <div class="category-card animate-in" onclick="loadPage('category', ${c.id})">
                <span class="category-icon">${c.icon}</span>
                <span class="category-name">${esc(c.name)}</span>
            </div>`).join('');
    }
    gridHtml(popular, 'popular-grid');
    gridHtml(fresh, 'new-grid');
    gridHtml(prem, 'premium-grid');
}

async function loadList(type) {
    const data = await apiFetch(`/api/${type}`);
    const el = document.getElementById(type === 'popular' ? 'popular-full' : type === 'new' ? 'new-full' : 'premium-full');
    if (!el || !data) return;
    if (data.length === 0) {
        el.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>Пока пусто</p></div>';
        return;
    }
    el.innerHTML = data.map((p, i) => renderProjectCard(p, i)).join('');
}

async function loadCategory(catId) {
    const data = await apiFetch('/api/projects');
    const projects = (data || []).filter(p => p.category_id === catId);
    const cats = await apiFetch('/api/categories');
    const cat = cats ? cats.find(c => c.id === catId) : null;
    const titleEl = document.getElementById('category-title');
    if (titleEl && cat) titleEl.textContent = cat.icon + ' ' + cat.name;
    const el = document.getElementById('category-projects');
    if (!el) return;
    if (projects.length === 0) {
        el.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>Пока пусто</p></div>';
        return;
    }
    el.innerHTML = projects.map((p, i) => renderProjectCard(p, i)).join('');
}

async function openProject(id) {
    pageHistory.push(currentPage);
    showPage('project');
    const p = await apiFetch(`/api/projects/${id}`);
    if (!p) return;
    document.getElementById('project-title').textContent = p.title;
    const detail = document.getElementById('project-detail');
    const isFree = p.is_free || p.price === 0;
    const price = p.discount_percent > 0 ? Math.round(p.price - (p.price * p.discount_percent / 100)) : p.price;
    const coverHtml = p.cover_url && !p.cover_url.startsWith('AgAC')
        ? `<img src="${p.cover_url}" alt="${esc(p.title)}" style="width:100%;display:block" onerror="this.style.display='none'">`
        : '';
    detail.innerHTML = `
        <div class="detail-cover">${coverHtml || '<div class="project-cover-placeholder" style="height:200px">🎬</div>'}</div>
        <h1 class="detail-title">${esc(p.title)}</h1>
        <div class="detail-price ${isFree ? 'free' : ''}">${isFree ? 'Бесплатно' : price + ' ⭐'}</div>
        ${p.description ? `<div class="detail-section"><h3>Описание</h3><p>${esc(p.description)}</p></div>` : ''}
        <div class="detail-section">
            <h3>Характеристики</h3>
            <div class="detail-specs">
                ${spec('Категория', p.category_icon + ' ' + p.category_name)}
                ${spec('Версия AE', p.ae_version || '—')}
                ${spec('Разрешение', p.resolution || '—')}
                ${spec('FPS', p.fps || '—')}
                ${spec('Размер', p.file_size || '—')}
                ${spec('Плагины', p.plugins || '—')}
                ${spec('Скачивания', p.downloads || 0)}
                ${spec('Просмотры', p.views || 0)}
                ${spec('Рейтинг', (p.rating || 0).toFixed(1) + ' ⭐')}
            </div>
        </div>
        ${p.tags ? `<div class="detail-section"><h3>Теги</h3><p>${esc(p.tags)}</p></div>` : ''}
        <div class="detail-actions">
            ${isFree || p._owned
                ? `<button class="btn btn-success" onclick="showToast('📥 Скачивание доступно в Telegram боте')">📥 Скачать</button>`
                : `<button class="btn btn-primary" onclick="showToast('💳 Оплата через Telegram бота')">💰 Купить ${price} ⭐</button>`
            }
            <button class="btn btn-secondary" onclick="toggleFav(${p.id})">❤️</button>
        </div>`;
}

function spec(label, value) {
    return `<div class="spec-item"><div class="spec-label">${esc(label)}</div><div class="spec-value">${esc(String(value))}</div></div>`;
}

async function toggleFav(id) {
    if (!user) { showToast('Откройте через Telegram'); return; }
    const r = await apiFetch('/api/toggle_favorite', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ user_id: user.id, project_id: id })
    });
    showToast(r?.added ? '❤️ Добавлено в избранное' : '💔 Удалено из избранного');
}

function showSearch() {
    document.getElementById('search-panel').classList.remove('hidden');
    document.getElementById('search-input').focus();
}
function hideSearch() {
    document.getElementById('search-panel').classList.add('hidden');
    document.getElementById('search-results').innerHTML = '';
    document.getElementById('search-input').value = '';
}

async function debounceSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(doSearch, 300);
}

async function doSearch() {
    const q = document.getElementById('search-input').value.trim();
    const el = document.getElementById('search-results');
    if (!q) { el.innerHTML = ''; return; }
    const data = await apiFetch('/api/search', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ query: q })
    });
    if (!data || data.length === 0) {
        el.innerHTML = '<div class="empty-state"><p>Ничего не найдено</p></div>';
        return;
    }
    el.innerHTML = data.map(p => {
        const price = p.is_free ? 'Бесплатно' : p.price + ' ⭐';
        const img = p.cover_url && !p.cover_url.startsWith('AgAC')
            ? `<img src="${p.cover_url}" alt="" onerror="this.style.background='var(--bg-secondary)'">`
            : '<div style="width:50px;height:50px;border-radius:8px;background:var(--gradient-1);display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0">🎬</div>';
        return `<div class="search-item" onclick="hideSearch();openProject(${p.id})">
            ${img}
            <div class="search-item-info">
                <h4>${esc(p.title)}</h4>
                <p>${price} · ${p.category_icon || ''} ${esc(p.category_name || '')}</p>
            </div>
        </div>`;
    }).join('');
}

function openTGApp(page) {
    if (tg) {
        tg.sendData(JSON.stringify({ action: 'open_page', page: page }));
    } else {
        showToast('Откройте через Telegram бота');
    }
}

function showToast(text) {
    const t = document.getElementById('toast');
    t.textContent = text;
    t.classList.remove('hidden');
    setTimeout(() => t.classList.add('hidden'), 2500);
}

function closeModal() {
    document.getElementById('modal-overlay').classList.add('hidden');
    document.getElementById('modal').classList.add('hidden');
}

function openModal(html) {
    document.getElementById('modal').innerHTML = `<div class="modal-handle"></div>${html}`;
    document.getElementById('modal-overlay').classList.remove('hidden');
    document.getElementById('modal').classList.remove('hidden');
}

window.addEventListener('popstate', () => {
    if (pageHistory.length > 0) {
        const prev = pageHistory.pop();
        showPage(prev);
    }
});

document.addEventListener('DOMContentLoaded', () => loadHome());
