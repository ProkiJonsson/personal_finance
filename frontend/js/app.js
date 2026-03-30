const API_URL = "http://127.0.0.1:8000";

const balanceEl  = document.getElementById("total-balance");
const incomeEl   = document.getElementById("total-income");
const expenseEl  = document.getElementById("total-expense");
const listEl     = document.getElementById("transaction-list");
const form       = document.getElementById("add-transaction");

const CATEGORY_LABELS = {
    food:          "Еда",
    transport:     "Транспорт",
    salary:        "Зарплата",
    entertainment: "Развлечения",
    other:         "Другое",
};

function fmt(amount) {
    return new Intl.NumberFormat("ru-RU", {
        style: "currency",
        currency: "RUB",
        minimumFractionDigits: 2,
    }).format(amount);
}

function fmtDate(iso) {
    return new Date(iso).toLocaleString("ru-RU", {
        day: "2-digit", month: "2-digit", year: "numeric",
        hour: "2-digit", minute: "2-digit",
    });
}

async function loadSummary() {
    const res = await fetch(`${API_URL}/summary`);
    const data = await res.json();
    balanceEl.textContent = fmt(data.balance);
    incomeEl.textContent  = fmt(data.income);
    expenseEl.textContent = fmt(data.expense);
}

async function loadTransactions() {
    const res = await fetch(`${API_URL}/transactions`);
    const transactions = await res.json();

    listEl.innerHTML = "";

    if (transactions.length === 0) {
        listEl.innerHTML = '<li class="empty-state">Транзакций пока нет</li>';
        return;
    }

    transactions.forEach(tx => {
        const li = document.createElement("li");
        li.className = tx.type;
        li.dataset.id = tx.id;

        const sign = tx.type === "income" ? "+" : "−";

        li.innerHTML = `
            <div class="tx-info">
                <div class="tx-desc">${tx.description}</div>
                <div class="tx-meta">${CATEGORY_LABELS[tx.category] ?? tx.category} · ${fmtDate(tx.created_at)}</div>
            </div>
            <span class="tx-amount ${tx.type}">${sign}${fmt(tx.amount)}</span>
            <button class="btn-delete" title="Удалить">✕</button>
        `;

        li.querySelector(".btn-delete").addEventListener("click", () => deleteTransaction(tx.id));
        listEl.appendChild(li);
    });
}

async function deleteTransaction(id) {
    await fetch(`${API_URL}/transactions/${id}`, { method: "DELETE" });
    await Promise.all([loadSummary(), loadTransactions()]);
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const body = {
        description: document.getElementById("description").value.trim(),
        amount:      parseFloat(document.getElementById("amount").value),
        type:        document.getElementById("type").value,
        category:    document.getElementById("category").value,
    };

    await fetch(`${API_URL}/transactions`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(body),
    });

    form.reset();
    await Promise.all([loadSummary(), loadTransactions()]);
});

// Initial load
Promise.all([loadSummary(), loadTransactions()]);
