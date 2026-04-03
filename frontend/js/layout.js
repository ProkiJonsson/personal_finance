/**
 * layout.js — общий layout: sidebar + header
 *
 * Загружается в конце <body>. IIFE выполняется синхронно:
 * 1. Сразу блокирует layout shift через initStyle
 * 2. Инъектирует HTML сайдбара и хедера в DOM
 * 3. Применяет сохранённое состояние сайдбара
 * 4. Устанавливает активные пункты навигации и заголовок страницы
 * 5. Навешивает события: toggle, logout
 * 6. Заполняет имя пользователя из JWT
 * 7. Через двойной rAF снимает блокировку и плавно показывает контент
 */

(function () {
    'use strict';

    // ── 1. Сразу блокируем layout shift ──────────────────────────────────────
    // Если страница уже определила #sidebar-init-style в <head> — используем его.
    // Иначе создаём сами (фолбэк для страниц без pre-defined стиля).
    if (!document.getElementById('sidebar-init-style')) {
        var initStyle = document.createElement('style');
        initStyle.id = 'sidebar-init-style';
        var initCss =
            '.main-content{opacity:0!important;transition:none!important}' +
            '.sidebar{transition:none!important}';
        // Сразу скрываем fund-пункты если кеш говорит что фонды выключены
        if (localStorage.getItem('fundAccountingEnabled') === '0') {
            initCss += '[data-fund-feature]{display:none!important}';
        }
        initStyle.textContent = initCss;
        document.head.appendChild(initStyle);
    }

    // ── 2. Конфигурация страниц ───────────────────────────────────────────────
    var PAGE_CONFIG = {
        'dashboard.html':       { nav: 'dashboard' },
        'operations.html':      { nav: 'operations' },
        'funds.html':           { nav: 'funds' },
        'accounts.html':        { nav: 'accounts' },
        'cascade.html':         { nav: 'cascade' },
        'counterparties.html':  { nav: 'counterparties' },
        'categories.html':      { nav: 'categories' },
        'settings.html':        { nav: 'settings' },
        'admin.html':           { nav: 'admin' },
        '':                     { nav: 'dashboard' },
    };

    var currentPage = window.location.pathname.split('/').pop() || '';
    var cfg = PAGE_CONFIG[currentPage] || { title: '', nav: '' };

    // ── 3. HTML сайдбара ──────────────────────────────────────────────────────
    var SIDEBAR_HTML = [
        '<aside class="sidebar" id="sidebar">',
        '  <div class="sidebar-inner">',
        '    <div class="sidebar-content">',
        '      <div class="sidebar-logo">',
        '        <div class="sidebar-logo-icon">',
        '          <img src="assets/icons/logo.svg" alt="МОЯ ПРИБЫЛЬ">',
        '        </div>',
        '        <img class="sidebar-logo-text" src="assets/icons/logo-text.svg" alt="МОЯ ПРИБЫЛЬ">',
        '      </div>',
        '      <div class="sidebar-header">',
        '        <button class="sidebar-toggle" id="sidebar-toggle" aria-label="Развернуть/свернуть">',
        '          <img src="assets/icons/arrow-double-left.svg" alt="">',
        '        </button>',
        '      </div>',
        '      <nav class="sidebar-nav">',
        '        <a href="dashboard.html" class="nav-item" data-nav="dashboard">',
        '          <div class="nav-item-icon"><img src="assets/icons/dashboard.svg" alt=""></div>',
        '          <span class="nav-item-text">Главная</span>',
        '          <span class="nav-tooltip">Главная</span>',
        '        </a>',
        '        <a href="operations.html" class="nav-item" data-nav="operations">',
        '          <div class="nav-item-icon"><img src="assets/icons/operations.svg" alt=""></div>',
        '          <span class="nav-item-text">Операции</span>',
        '          <span class="nav-tooltip">Операции</span>',
        '        </a>',
        '        <a href="funds.html" class="nav-item" data-nav="funds" data-fund-feature>',
        '          <div class="nav-item-icon"><img src="assets/icons/funds.svg" alt=""></div>',
        '          <span class="nav-item-text">Фонды</span>',
        '          <span class="nav-tooltip">Фонды</span>',
        '        </a>',
        '        <a href="accounts.html" class="nav-item" data-nav="accounts">',
        '          <div class="nav-item-icon"><img src="assets/icons/accounts.svg" alt=""></div>',
        '          <span class="nav-item-text">Счета</span>',
        '          <span class="nav-tooltip">Счета</span>',
        '        </a>',
        '      </nav>',
        '    </div>',
        '    <div class="sidebar-bottom">',
        '      <a href="cascade.html" class="nav-item" data-nav="cascade" data-fund-feature>',
        '        <div class="nav-item-icon"><img src="assets/icons/cascade.svg" alt=""></div>',
        '        <span class="nav-item-text">Каскад Фондов</span>',
        '        <span class="nav-tooltip">Каскад Фондов</span>',
        '      </a>',
        '      <a href="counterparties.html" class="nav-item" data-nav="counterparties" data-fund-feature>',
        '        <div class="nav-item-icon"><img src="assets/icons/counterparties.svg" alt=""></div>',
        '        <span class="nav-item-text">Контрагенты</span>',
        '        <span class="nav-tooltip">Контрагенты</span>',
        '      </a>',
        '      <a href="categories.html" class="nav-item" data-nav="categories">',
        '        <div class="nav-item-icon"><img src="assets/icons/categories.svg" alt=""></div>',
        '        <span class="nav-item-text">Статьи учёта</span>',
        '        <span class="nav-tooltip">Статьи учёта</span>',
        '      </a>',
        '      <a href="admin.html" class="nav-item" data-nav="admin" id="admin-nav-item" style="display:none">',
        '        <div class="nav-item-icon"><img src="assets/icons/settings.svg" alt=""></div>',
        '        <span class="nav-item-text">Админ-панель</span>',
        '        <span class="nav-tooltip">Админ-панель</span>',
        '      </a>',
        '      <a href="settings.html" class="nav-item" data-nav="settings">',
        '        <div class="nav-item-icon"><img src="assets/icons/settings.svg" alt=""></div>',
        '        <span class="nav-item-text">Настройки</span>',
        '        <span class="nav-tooltip">Настройки</span>',
        '      </a>',
        '      <button class="nav-item" id="logout-btn">',
        '        <div class="nav-item-icon"><img src="assets/icons/logout.svg" alt=""></div>',
        '        <span class="nav-item-text">Выйти</span>',
        '        <span class="nav-tooltip">Выйти</span>',
        '      </button>',
        '    </div>',
        '  </div>',
        '</aside>',
    ].join('\n');

    // ── 4. HTML хедера ────────────────────────────────────────────────────────
    var HEADER_HTML = [
        '<header class="header">',
        '  <div class="header-left">',
        '    <h1 class="header-title" id="header-title">Личные финансы</h1>',
        '    <nav class="header-nav">',
        '      <a href="dashboard.html" class="header-nav-item" data-nav="dashboard">Главная</a>',
        '      <a href="operations.html" class="header-nav-item" data-nav="operations">Операции</a>',
        '      <a href="funds.html" class="header-nav-item" data-nav="funds" data-fund-feature>Фонды</a>',
        '      <a href="accounts.html" class="header-nav-item" data-nav="accounts">Счета</a>',
        '    </nav>',
        '  </div>',
        '  <div class="header-right">',
        '    <button class="header-icon-btn" aria-label="Поиск">',
        '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">',
        '        <circle cx="11" cy="11" r="8"/>',
        '        <path d="m21 21-4.35-4.35"/>',
        '      </svg>',
        '    </button>',
        '    <button class="header-icon-btn" aria-label="Уведомления">',
        '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">',
        '        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>',
        '        <path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
        '      </svg>',
        '    </button>',
        '    <div class="user-menu">',
        '      <div class="user-avatar" id="user-avatar">?</div>',
        '      <span class="user-name" id="user-name">Загрузка...</span>',
        '    </div>',
        '  </div>',
        '</header>',
    ].join('\n');

    // ── 5. Инъекция HTML ──────────────────────────────────────────────────────
    var body = document.body;
    var mainContent = body.querySelector('.main-content');

    // Sidebar — перед <main>
    var tmpSidebar = document.createElement('div');
    tmpSidebar.innerHTML = SIDEBAR_HTML;
    body.insertBefore(tmpSidebar.firstElementChild, mainContent);

    // Header — первым ребёнком <main>
    var tmpHeader = document.createElement('div');
    tmpHeader.innerHTML = HEADER_HTML;
    mainContent.insertBefore(tmpHeader.firstElementChild, mainContent.firstChild);

    // ── 6. Восстановить состояние sidebar (без transition — initStyle держит) ─
    var sidebar = document.getElementById('sidebar');
    if (localStorage.getItem('sidebarExpanded') === 'true') {
        sidebar.classList.add('expanded');
        body.classList.add('sidebar-expanded');
    }

    // ── 7. Активные пункты навигации ─────────────────────────────────────────
    if (cfg.nav) {
        document.querySelectorAll('[data-nav="' + cfg.nav + '"]').forEach(function (el) {
            el.classList.add('active');
        });
    }

    // ── 8. Заголовок страницы — всегда "Личные финансы" (задан в HTML) ───────

    // ── 9. Имя пользователя из JWT ────────────────────────────────────────────
    function parseJwtPayload(t) {
        try {
            var b64 = t.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
            b64 += '=='.slice(0, (4 - b64.length % 4) % 4);
            return JSON.parse(atob(b64));
        } catch (e) { return {}; }
    }

    var token = localStorage.getItem('token') || sessionStorage.getItem('token');
    if (!token) {
        window.location.replace('index.html');
        return;
    }
    var payload = parseJwtPayload(token);
    if (!payload.exp || Math.floor(Date.now() / 1000) >= payload.exp) {
        localStorage.removeItem('token');
        sessionStorage.removeItem('token');
        window.location.replace('index.html');
        return;
    }
    if (token) {
        var name = payload.name || payload.email || 'Пользователь';
        var nameEl = document.getElementById('user-name');
        var avatarEl = document.getElementById('user-avatar');
        if (nameEl) { nameEl.textContent = name; }
        if (avatarEl) { avatarEl.textContent = name.charAt(0).toUpperCase(); }
    }

    // ── 9a. Блокировка неактивных пользователей ─────────────────────────────
    if (payload.is_active === false) {
        var mc = document.querySelector('.main-content');
        if (mc) {
            var logoBlock = '<div style="display:inline-flex;align-items:center;gap:12px;margin-bottom:32px">' +
                '<div style="width:40px;height:40px;flex-shrink:0"><img src="assets/icons/logo.svg" alt="" style="width:100%;height:100%"></div>' +
                '<img src="assets/icons/logo-text.svg" alt="МОЯ ПРИБЫЛЬ" style="width:84px;height:33px;flex-shrink:0">' +
                '</div>';
            var btnStyle = 'width:100%;max-width:320px;padding:14px;background:var(--primary);color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;transition:all 0.2s;letter-spacing:0.01em';
            mc.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;min-height:80vh;padding:32px">' +
                '<div style="text-align:center;max-width:400px" id="activation-block">' +
                logoBlock +
                '<h2 style="font-size:20px;font-weight:700;margin-bottom:12px">Ожидание активации</h2>' +
                '<p style="color:var(--text-secondary);font-size:14px;line-height:1.6">Ваш аккаунт ещё не активирован администратором. Пожалуйста, дождитесь подтверждения.</p>' +
                '</div></div>';

            // Периодическая проверка активации (каждые 5 сек)
            var checkInterval = setInterval(function () {
                var apiBase = 'http://127.0.0.1:8000';
                fetch(apiBase + '/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: '', password: '' }),
                }).catch(function () {});
                // Проще: попробуем запросить /settings — если 200, значит активирован
                fetch(apiBase + '/settings', {
                    headers: { 'Authorization': 'Bearer ' + token }
                }).then(function (res) {
                    if (res.ok) {
                        clearInterval(checkInterval);
                        var block = document.getElementById('activation-block');
                        if (block) {
                            block.innerHTML = logoBlock +
                                '<h2 style="font-size:20px;font-weight:700;margin-bottom:12px;color:var(--success)">Аккаунт активирован!</h2>' +
                                '<p style="color:var(--text-secondary);font-size:14px;line-height:1.6;margin-bottom:24px">Поздравляем! Администратор активировал ваш аккаунт. Войдите заново, чтобы начать работу.</p>' +
                                '<button onclick="localStorage.removeItem(\'token\');sessionStorage.removeItem(\'token\');window.location.href=\'index.html\'" style="' + btnStyle + '">Войти в приложение</button>';
                        }
                    }
                }).catch(function () {});
            }, 5000);
            mc.style.opacity = '1';
        }
        // Скрыть sidebar
        var sidebarEl = document.getElementById('sidebar');
        if (sidebarEl) { sidebarEl.style.display = 'none'; }
        if (mc) { mc.style.marginLeft = '0'; }
        // Убрать init-style чтобы контент стал видимым
        var initSt = document.getElementById('sidebar-init-style');
        if (initSt) { initSt.remove(); }
        return;
    }

    // ── 9b. Показать админ-пункт если is_admin ──────────────────────────────
    if (payload.is_admin) {
        var adminNavItem = document.getElementById('admin-nav-item');
        if (adminNavItem) { adminNavItem.style.display = ''; }
    }

    // ── 9c. Фоновое обновление токена (актуализация is_admin/is_active) ─────
    var apiBase = 'http://127.0.0.1:8000';
    fetch(apiBase + '/auth/me', {
        headers: { 'Authorization': 'Bearer ' + token }
    }).then(function (res) {
        if (res.ok) return res.json();
        return null;
    }).then(function (data) {
        if (!data) return;
        var storage = localStorage.getItem('token') ? localStorage : sessionStorage;
        storage.setItem('token', data.access_token);
        var newPayload = parseJwtPayload(data.access_token);
        // Обновить видимость админ-пункта
        var adminNav = document.getElementById('admin-nav-item');
        if (adminNav) {
            adminNav.style.display = newPayload.is_admin ? '' : 'none';
        }
    }).catch(function () {});

    // ── 10. Logout ────────────────────────────────────────────────────────────
    window.handleLogout = function () {
        localStorage.removeItem('token');
        sessionStorage.removeItem('token');
        window.location.href = 'index.html';
    };

    var logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', window.handleLogout);
    }

    // ── 10b. Скрыть fund-пункты если учёт по фондам выключен ───────────────
    // Страница настроек всегда доступна — оттуда включается режим
    var FUND_PAGES_REDIRECT = ['funds.html', 'cascade.html', 'counterparties.html'];

    function setFundFeaturesVisible(visible) {
        document.querySelectorAll('[data-fund-feature]').forEach(function (el) {
            el.style.display = visible ? '' : 'none';
        });
        localStorage.setItem('fundAccountingEnabled', visible ? '1' : '0');
        // Редирект если пользователь на fund-странице (но НЕ на settings)
        if (!visible && FUND_PAGES_REDIRECT.indexOf(currentPage) !== -1) {
            window.location.replace('dashboard.html');
        }
    }

    // Глобальная функция — вызывается из settings.html после сохранения
    window.setFundFeaturesVisible = setFundFeaturesVisible;

    // Сразу применяем кешированное значение (до рендера) — предотвращает прыжок
    var cachedFundEnabled = localStorage.getItem('fundAccountingEnabled');
    if (cachedFundEnabled === '0') {
        setFundFeaturesVisible(false);
    }

    // Async проверка настроек — обновляет кеш и корректирует если изменилось
    if (token) {
        var apiBase = 'http://127.0.0.1:8000';
        fetch(apiBase + '/settings', {
            headers: { 'Authorization': 'Bearer ' + token }
        }).then(function (res) {
            if (res.ok) return res.json();
            return null;
        }).then(function (settings) {
            if (settings) {
                setFundFeaturesVisible(!!settings.fund_accounting_enabled);
            }
        }).catch(function () {
            // Ошибка сети — не скрываем, чтобы не ломать навигацию
        });
    }

    // ── 11. Toggle sidebar ────────────────────────────────────────────────────
    var toggleBtn = document.getElementById('sidebar-toggle');
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', function () {
            var expanded = sidebar.classList.toggle('expanded');
            body.classList.toggle('sidebar-expanded', expanded);
            localStorage.setItem('sidebarExpanded', expanded);
        });
    }

    // ── 12. Убрать layout shift — двойной rAF ─────────────────────────────────
    // Первый rAF: браузер поставил кадр в очередь
    // Второй rAF: браузер УЖЕ отрисовал кадр с корректным layout
    // → только теперь снимаем initStyle и плавно показываем контент
    requestAnimationFrame(function () {
        requestAnimationFrame(function () {
            var style = document.getElementById('sidebar-init-style');
            if (style) { style.remove(); }

            var mc = body.querySelector('.main-content');
            if (mc) {
                mc.style.transition = 'opacity 0.15s ease';
                mc.style.opacity = '1';
                setTimeout(function () {
                    mc.style.transition = '';
                    mc.style.opacity = '';
                }, 200);
            }
        });
    });

    // ── 13. Динамический контент страниц ────────────────────────────────────
    var PAGE_KEY_MAP = {
        'dashboard.html': 'dashboard',
        'operations.html': 'operations',
        'funds.html': 'funds',
        'accounts.html': 'accounts',
        'cascade.html': 'cascade',
        'counterparties.html': 'counterparties',
        'categories.html': 'categories',
        'settings.html': 'settings',
        'admin.html': 'admin',
    };

    function applyPageContent(pageKey, allData) {
        var data = allData[pageKey];
        if (!data) return;
        if (data.tab_title) { document.title = data.tab_title; }
        if (data.header) {
            var h1 = document.querySelector('.page-header h1, .page-header-row h1');
            if (h1) { h1.textContent = data.header; }
            // Обновляем текст в sidebar
            var navItem = document.querySelector('[data-nav="' + pageKey + '"] .nav-item-text');
            if (navItem) { navItem.textContent = data.header; }
            var navTooltip = document.querySelector('[data-nav="' + pageKey + '"] .nav-tooltip');
            if (navTooltip) { navTooltip.textContent = data.header; }
        }
        // data-content-key элементы
        document.querySelectorAll('[data-content-key]').forEach(function (el) {
            var key = el.getAttribute('data-content-key');
            if (data[key] != null) { el.innerHTML = data[key]; }
        });
    }

    window.loadPageContent = function (pageKeyOverride) {
        var pageKey = pageKeyOverride || PAGE_KEY_MAP[currentPage];
        if (!pageKey) return;

        var cached = sessionStorage.getItem('pageContent');
        if (cached) {
            try { applyPageContent(pageKey, JSON.parse(cached)); } catch (e) {}
        }

        var apiBase = 'http://127.0.0.1:8000';
        fetch(apiBase + '/admin/page-content')
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
                if (data) {
                    sessionStorage.setItem('pageContent', JSON.stringify(data));
                    applyPageContent(pageKey, data);
                }
            })
            .catch(function () {});
    };

    // Автозагрузка контента для текущей страницы
    var autoPageKey = PAGE_KEY_MAP[currentPage];
    if (autoPageKey) {
        window.loadPageContent(autoPageKey);
    }

    // ── 14. Money input formatting (1 600 000,00) ─────────────────────────────
    function formatMoney(value) {
        if (value === '' || value == null) return '';
        var num = parseFloat(String(value).replace(/\s/g, '').replace(',', '.'));
        if (isNaN(num)) return '';
        var parts = num.toFixed(2).split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
        return parts[0] + ',' + parts[1];
    }

    function parseMoney(str) {
        if (!str) return '';
        var cleaned = str.replace(/\s/g, '').replace(',', '.');
        var num = parseFloat(cleaned);
        return isNaN(num) ? '' : num;
    }

    function initMoneyInput(input) {
        if (input._moneyInit) return;
        input._moneyInit = true;

        input.addEventListener('focus', function () {
            var val = parseMoney(this.value);
            this.value = val !== '' ? String(val).replace('.', ',') : '';
        });

        input.addEventListener('blur', function () {
            this.value = formatMoney(this.value);
        });

        input.addEventListener('input', function () {
            var pos = this.selectionStart;
            var raw = this.value;
            // Allow only digits, comma, minus
            var cleaned = raw.replace(/[^\d,\-]/g, '');
            if (cleaned !== raw) {
                this.value = cleaned;
                this.selectionStart = this.selectionEnd = pos - (raw.length - cleaned.length);
            }
        });

        // Format initial value if present
        if (input.value) {
            input.value = formatMoney(input.value);
        }
    }

    // Auto-init all data-money inputs
    document.querySelectorAll('[data-money]').forEach(initMoneyInput);

    // Expose globally
    window.formatMoney = formatMoney;
    window.parseMoney = parseMoney;
    window.initMoneyInput = initMoneyInput;

})();
