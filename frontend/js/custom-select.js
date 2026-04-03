/**
 * CustomSelect — кастомный dropdown с поиском и возможностью создания элементов.
 *
 * Атрибуты:
 *   data-custom-select    — активировать компонент
 *   data-add-new          — текст кнопки "Добавить новый..."
 *   data-add-api          — API endpoint для POST (простое создание: 1 поле)
 *   data-add-field        — имя поля для отправки (default: "name")
 *   data-add-placeholder  — placeholder в мини-форме
 *   data-add-handler      — имя глобальной функции-обработчика вместо стандартного POST
 *                           Сигнатура: handler(onCreated) где onCreated(id, name)
 */

(function () {
    'use strict';

    const TOKEN = () => localStorage.getItem('token') || sessionStorage.getItem('token');
    const API = 'http://127.0.0.1:8000';
    const CLOSE_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    const ARROW_SVG = '<svg class="cs-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>';
    const CHEVRON_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>';

    // ── Styles ──────────────────────────────────────────────
    const STYLE_ID = 'custom-select-styles';
    if (!document.getElementById(STYLE_ID)) {
        const s = document.createElement('style');
        s.id = STYLE_ID;
        s.textContent = `
/* ── Trigger ── */
.cs-wrap { position: relative; }
.cs-trigger {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 12px; border: 1.5px solid var(--border); border-radius: 10px;
    background: #fafafa; cursor: pointer; font-size: 13px; color: var(--text-primary);
    transition: all 0.2s; min-height: 40px; user-select: none;
}
.cs-trigger:hover, .cs-wrap.open .cs-trigger { border-color: var(--primary); background: #fff; }
.cs-arrow { width: 16px; height: 16px; color: var(--text-muted); transition: transform 0.2s; flex-shrink: 0; }
.cs-wrap.open .cs-arrow { transform: rotate(180deg); }
.cs-value { font-size: 13px; color: var(--text-primary); }
.cs-placeholder { color: var(--text-muted); font-size: 13px; }

/* ── Dropdown ── */
.cs-dropdown {
    position: absolute; top: calc(100% + 4px); left: 0; right: 0;
    background: #fff; border: 1.5px solid var(--border); border-radius: 10px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.12); z-index: 200;
    max-height: 280px; display: none; overflow: hidden;
}
.cs-wrap.open .cs-dropdown { display: flex; flex-direction: column; }

.cs-add-btn {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 14px; font-size: 13px; font-weight: 600; color: var(--primary);
    cursor: pointer; border-bottom: 1px solid var(--border); transition: background 0.15s;
    flex-shrink: 0;
}
.cs-add-btn:hover { background: var(--primary-light); }
.cs-add-btn svg { width: 14px; height: 14px; }

.cs-search-wrap { padding: 8px 10px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.cs-search {
    width: 100%; padding: 6px 10px; border: 1.5px solid var(--border); border-radius: 8px;
    font-size: 12px; color: var(--text-primary); background: #fafafa; outline: none;
    font-family: inherit; transition: border-color 0.2s;
}
.cs-search:focus { border-color: var(--primary); background: #fff; }

.cs-options { overflow-y: auto; flex: 1; }
.cs-option {
    padding: 9px 14px; font-size: 13px; color: var(--text-primary);
    cursor: pointer; transition: background 0.1s;
}
.cs-option:hover { background: var(--primary-light); }
.cs-option.selected { background: var(--primary); color: #fff; }
.cs-option.hidden { display: none; }
.cs-no-results { padding: 12px 14px; font-size: 12px; color: var(--text-muted); text-align: center; display: none; }

/* ── Mini-panel (slide-in from right, on top of main panel) ── */
.cs-mini-overlay {
    position: fixed; inset: 0; z-index: 1100;
    background: rgba(0,0,0,0.25);
    opacity: 0; pointer-events: none; transition: opacity 0.2s;
}
.cs-mini-overlay.open { opacity: 1; pointer-events: all; }

.cs-mini-panel {
    position: fixed; top: 0; right: 0; width: 340px; height: 100vh;
    background: #fff; z-index: 1101;
    transform: translateX(100%); transition: transform 0.3s ease;
    display: flex; flex-direction: column;
    box-shadow: -4px 0 24px rgba(0,0,0,0.1);
}
.cs-mini-overlay.open .cs-mini-panel { transform: translateX(0); }

.cs-mini-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 20px 24px; border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.cs-mini-header h4 { font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0; }
.cs-mini-close {
    width: 32px; height: 32px; border: none; background: transparent; border-radius: 8px;
    display: flex; align-items: center; justify-content: center; cursor: pointer;
    color: var(--text-secondary); transition: all 0.2s;
}
.cs-mini-close:hover { background: var(--bg-body); color: var(--text-primary); }
.cs-mini-close svg { width: 18px; height: 18px; }

.cs-mini-body { padding: 24px; display: flex; flex-direction: column; gap: 16px; overflow-y: auto; flex: 1; }
.cs-mini-body .form-group { display: flex; flex-direction: column; gap: 4px; }
.cs-mini-body .form-group label { font-size: 11px; font-weight: 600; color: var(--text-secondary); }
.cs-mini-body .form-group input,
.cs-mini-body .form-group select {
    padding: 10px 12px; border: 1.5px solid var(--border); border-radius: 10px;
    font-size: 13px; color: var(--text-primary); background: #fafafa; outline: none;
    transition: all 0.2s; font-family: inherit;
}
.cs-mini-body .form-group input:focus,
.cs-mini-body .form-group select:focus {
    border-color: var(--primary); background: #fff; box-shadow: 0 0 0 3px var(--primary-light);
}
.cs-mini-error { font-size: 12px; color: var(--danger); display: none; }

.cs-mini-footer {
    padding: 16px 24px; border-top: 1px solid var(--border);
    display: flex; flex-direction: column; gap: 8px; flex-shrink: 0;
}
.cs-mini-footer button {
    width: 100%; padding: 10px 20px; border-radius: 10px; font-size: 14px;
    font-weight: 600; cursor: pointer; border: none; transition: all 0.2s; text-align: center;
}
.cs-mini-footer .cs-mini-save { background: var(--primary); color: #fff; }
.cs-mini-footer .cs-mini-save:hover { background: var(--primary-dark); }
.cs-mini-footer .cs-mini-save:disabled { opacity: 0.5; cursor: not-allowed; }
.cs-mini-footer .cs-mini-cancel { background: #fff; color: var(--text-secondary); border: 1.5px solid var(--border); }
.cs-mini-footer .cs-mini-cancel:hover { border-color: var(--primary); color: var(--primary); }

/* ── Custom validation ── */
.field-error input, .field-error select, .field-error textarea, .field-error .cs-trigger {
    border-color: var(--danger) !important;
}
.field-error-msg { font-size: 11px; color: var(--danger); margin-top: 3px; display: none; }
.field-error .field-error-msg { display: block; }

@media (max-width: 768px) { .cs-mini-panel { width: 100%; } }
`;
        document.head.appendChild(s);
    }

    // ── CustomSelect class ──────────────────────────────────
    class CustomSelect {
        constructor(selectEl) {
            this.select = selectEl;
            this.select.style.display = 'none';
            this.addNewText = selectEl.dataset.addNew || '';
            this.addApi = selectEl.dataset.addApi || '';
            this.addField = selectEl.dataset.addField || 'name';
            this.addPlaceholder = selectEl.dataset.addPlaceholder || 'Название';
            this.addHandler = selectEl.dataset.addHandler || '';
            this.hasAddNew = !!(this.addNewText && (this.addApi || this.addHandler));
            this.build();
            this.bindEvents();
        }

        build() {
            this.wrap = document.createElement('div');
            this.wrap.className = 'cs-wrap';
            this.trigger = document.createElement('div');
            this.trigger.className = 'cs-trigger';
            this.updateTrigger();
            this.dropdown = document.createElement('div');
            this.dropdown.className = 'cs-dropdown';
            this.renderOptions();
            this.wrap.appendChild(this.trigger);
            this.wrap.appendChild(this.dropdown);
            this.select.parentNode.insertBefore(this.wrap, this.select);
            this.wrap.appendChild(this.select);
        }

        updateTrigger() {
            const sel = this.select.options[this.select.selectedIndex];
            const text = sel && sel.value ? sel.text : '';
            const ph = this.select.options[0] ? this.select.options[0].text : 'Выбрать';
            this.trigger.innerHTML = `<div>${text ? `<div class="cs-value">${text}</div>` : `<div class="cs-placeholder">${ph}</div>`}</div>${ARROW_SVG}`;
        }

        renderOptions() {
            let html = '';
            if (this.hasAddNew) {
                html += `<div class="cs-add-btn">${this.addNewText} ${CHEVRON_SVG}</div>`;
            }
            // Count real options (non-placeholder)
            let realCount = 0;
            const opts = this.select.options;
            for (let i = 0; i < opts.length; i++) {
                if (i === 0 && !opts[i].value) continue;
                realCount++;
            }
            // Search field (show if 3+ options or data-always-search)
            const alwaysSearch = this.select.hasAttribute('data-always-search');
            if (realCount >= 3 || alwaysSearch) {
                html += `<div class="cs-search-wrap"><input class="cs-search" placeholder="Поиск..." type="text"></div>`;
            }
            html += '<div class="cs-options">';
            for (let i = 0; i < opts.length; i++) {
                if (i === 0 && !opts[i].value) continue;
                const s = opts[i].value === this.select.value ? ' selected' : '';
                html += `<div class="cs-option${s}" data-value="${opts[i].value}">${opts[i].text}</div>`;
            }
            html += '<div class="cs-no-results">Не найдено</div>';
            html += '</div>';
            this.dropdown.innerHTML = html;
        }

        bindEvents() {
            this.trigger.addEventListener('click', (e) => { e.stopPropagation(); this.toggle(); });

            this.dropdown.addEventListener('click', (e) => {
                const opt = e.target.closest('.cs-option');
                if (opt) {
                    this.select.value = opt.dataset.value;
                    this.select.dispatchEvent(new Event('change'));
                    this.updateTrigger();
                    this.close();
                    const fg = this.wrap.closest('.form-group');
                    if (fg) fg.classList.remove('field-error');
                    return;
                }
                if (e.target.closest('.cs-add-btn')) { this.close(); this.openMiniPanel(); }
            });

            // Search filtering
            this.dropdown.addEventListener('input', (e) => {
                if (!e.target.classList.contains('cs-search')) return;
                const q = e.target.value.toLowerCase();
                let found = 0;
                this.dropdown.querySelectorAll('.cs-option').forEach(opt => {
                    const match = opt.textContent.toLowerCase().includes(q);
                    opt.classList.toggle('hidden', !match);
                    if (match) found++;
                });
                const noRes = this.dropdown.querySelector('.cs-no-results');
                if (noRes) noRes.style.display = found === 0 ? 'block' : 'none';
            });

            document.addEventListener('click', (e) => { if (!this.wrap.contains(e.target)) this.close(); });
        }

        toggle() {
            const isOpen = this.wrap.classList.contains('open');
            document.querySelectorAll('.cs-wrap.open').forEach(w => w.classList.remove('open'));
            if (!isOpen) {
                this.renderOptions();
                this.wrap.classList.add('open');
                const search = this.dropdown.querySelector('.cs-search');
                if (search) setTimeout(() => search.focus(), 50);
            }
        }

        close() {
            this.wrap.classList.remove('open');
            const search = this.dropdown.querySelector('.cs-search');
            if (search) search.value = '';
        }

        // ── Mini slide-panel (right, on top of main panel) ──
        openMiniPanel() {
            // If custom handler — call it
            if (this.addHandler && window[this.addHandler]) {
                window[this.addHandler]((id, name) => {
                    const opt = document.createElement('option');
                    opt.value = id;
                    opt.textContent = name;
                    this.select.appendChild(opt);
                    this.select.value = id;
                    this.select.dispatchEvent(new Event('change'));
                    this.updateTrigger();
                });
                return;
            }

            if (this._overlay) this._overlay.remove();

            this._overlay = document.createElement('div');
            this._overlay.className = 'cs-mini-overlay';
            this._overlay.innerHTML = `
                <div class="cs-mini-panel">
                    <div class="cs-mini-header">
                        <h4>${this.addNewText}</h4>
                        <button class="cs-mini-close">${CLOSE_SVG}</button>
                    </div>
                    <div class="cs-mini-body">
                        <div class="form-group">
                            <label>${this.addPlaceholder}</label>
                            <input type="text" placeholder="${this.addPlaceholder}" autofocus>
                        </div>
                        <div class="cs-mini-error"></div>
                    </div>
                    <div class="cs-mini-footer">
                        <button class="cs-mini-save">Создать</button>
                        <button class="cs-mini-cancel">Отмена</button>
                    </div>
                </div>
            `;
            document.body.appendChild(this._overlay);
            requestAnimationFrame(() => this._overlay.classList.add('open'));

            const input = this._overlay.querySelector('input');
            const errEl = this._overlay.querySelector('.cs-mini-error');
            const saveBtn = this._overlay.querySelector('.cs-mini-save');

            setTimeout(() => input.focus(), 100);

            this._overlay.querySelector('.cs-mini-close').addEventListener('click', () => this._closeMini());
            this._overlay.querySelector('.cs-mini-cancel').addEventListener('click', () => this._closeMini());
            this._overlay.addEventListener('click', (e) => { if (e.target === this._overlay) this._closeMini(); });
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') saveBtn.click();
                if (e.key === 'Escape') this._closeMini();
            });

            saveBtn.addEventListener('click', async () => {
                const name = input.value.trim();
                if (!name) { errEl.textContent = 'Введите название'; errEl.style.display = 'block'; input.focus(); return; }
                saveBtn.disabled = true; saveBtn.textContent = '...';
                try {
                    const body = {}; body[this.addField] = name;
                    const res = await fetch(API + this.addApi, {
                        method: 'POST',
                        headers: { 'Authorization': 'Bearer ' + TOKEN(), 'Content-Type': 'application/json' },
                        body: JSON.stringify(body)
                    });
                    if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || 'Ошибка'); }
                    const created = await res.json();
                    const opt = document.createElement('option');
                    opt.value = created.id; opt.textContent = created.name || name;
                    this.select.appendChild(opt);
                    this.select.value = created.id;
                    this.select.dispatchEvent(new Event('change'));
                    this.updateTrigger();
                    this._closeMini();
                } catch (err) {
                    errEl.textContent = err.message; errEl.style.display = 'block';
                    saveBtn.disabled = false; saveBtn.textContent = 'Создать';
                }
            });
        }

        _closeMini() {
            if (this._overlay) {
                this._overlay.classList.remove('open');
                setTimeout(() => { if (this._overlay) { this._overlay.remove(); this._overlay = null; } }, 300);
            }
        }

        refresh() { this.renderOptions(); this.updateTrigger(); }
    }

    // ── Custom form validation ───────────────────────────────
    function setupFormValidation(form) {
        if (!form || form.dataset.customValidation) return;
        form.dataset.customValidation = 'true';
        form.setAttribute('novalidate', '');
        form.addEventListener('submit', (e) => {
            form.querySelectorAll('.field-error').forEach(el => el.classList.remove('field-error'));
            let firstInvalid = null;
            form.querySelectorAll('[required]').forEach(field => {
                const fg = field.closest('.form-group');
                if (!fg || fg.style.display === 'none') return;
                let errMsg = fg.querySelector('.field-error-msg');
                if (!errMsg) { errMsg = document.createElement('div'); errMsg.className = 'field-error-msg'; errMsg.textContent = 'Обязательное поле'; fg.appendChild(errMsg); }
                if (!field.value.trim()) { fg.classList.add('field-error'); if (!firstInvalid) firstInvalid = field; }
            });
            if (firstInvalid) {
                e.preventDefault(); e.stopImmediatePropagation();
                const cs = firstInvalid.closest('.cs-wrap');
                if (cs) cs.querySelector('.cs-trigger').focus(); else firstInvalid.focus();
            }
        });
    }

    // ── Init ─────────────────────────────────────────────────
    function initCustomSelects(root) {
        (root || document).querySelectorAll('select[data-custom-select]').forEach(sel => {
            if (sel._customSelect) return;
            sel._customSelect = new CustomSelect(sel);
        });
    }

    function initFormValidation(root) {
        (root || document).querySelectorAll('form').forEach(f => setupFormValidation(f));
    }

    document.addEventListener('DOMContentLoaded', () => { initCustomSelects(); initFormValidation(); });

    window.CustomSelect = CustomSelect;
    window.initCustomSelects = initCustomSelects;
    window.initFormValidation = initFormValidation;
    window.setupFormValidation = setupFormValidation;
    window.validatePanel = function (panelEl) {
        panelEl.querySelectorAll('.field-error').forEach(el => el.classList.remove('field-error'));
        let valid = true;
        panelEl.querySelectorAll('[required]').forEach(field => {
            const fg = field.closest('.form-group');
            if (!fg || fg.style.display === 'none') return;
            let errMsg = fg.querySelector('.field-error-msg');
            if (!errMsg) { errMsg = document.createElement('div'); errMsg.className = 'field-error-msg'; errMsg.textContent = 'Обязательное поле'; fg.appendChild(errMsg); }
            if (!field.value.trim()) { fg.classList.add('field-error'); valid = false; }
        });
        return valid;
    };
})();
