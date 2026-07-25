const MIN_SIZE = 60;
const MAX_SIZE = 280;
const MIN_SATS = 1;

function calculateBubbleSize(sats) {
    if (sats <= 0) return MIN_SIZE;
    const logMin = Math.log(MIN_SATS);
    const logMax = Math.log(100_000_000);
    const logVal = Math.log(Math.max(sats, MIN_SATS));
    const normalized = (logVal - logMin) / (logMax - logMin);
    return MIN_SIZE + normalized * (MAX_SIZE - MIN_SIZE);
}

function formatSats(sats) {
    if (sats >= 1_000_000) return `${(sats / 1_000_000).toFixed(2)}M`;
    if (sats >= 1_000) return `${(sats / 1_000).toFixed(1)}k`;
    return sats.toString();
}

function renderBubble(bubble) {
    const el = document.createElement('div');
    el.className = 'bubble';
    el.dataset.id = bubble.id;

    const size = calculateBubbleSize(bubble.balance_sats);
    el.style.width = `${size}px`;
    el.style.height = `${size}px`;

    el.innerHTML = `
        <span class="sats">${formatSats(bubble.balance_sats)}</span>
        <span class="usd">$${bubble.balance_usd.toFixed(2)}</span>
        ${bubble.name ? `<span class="name">${bubble.name}</span>` : ''}
    `;

    el.addEventListener('click', (e) => {
        if (bubble.balance_sats === 0) {
            openEditModal(bubble);
        } else {
            openBubbleMenu(bubble);
        }
    });

    el.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        openEditModal(bubble);
    });

    return el;
}

function openBubbleMenu(bubble) {
    const action = confirm(
        `Bubble: ${bubble.name || 'Unnamed'}\n` +
        `Balance: ${bubble.balance_sats.toLocaleString()} sats ($${bubble.balance_usd.toFixed(2)})\n\n` +
        `Click OK to DOUBLE this bubble\n` +
        `Click Cancel to WITHDRAW`
    );
    if (action) {
        doubleBubble(bubble.id);
    } else {
        openWithdrawModal(bubble);
    }
}

function openEditModal(bubble) {
    document.getElementById('edit-bubble-id').value = bubble.id;
    document.getElementById('bubble-name').value = bubble.name || '';
    document.getElementById('edit-modal').style.display = 'flex';
}

function openWithdrawModal(bubble) {
    document.getElementById('withdraw-bubble-id').value = bubble.id;
    document.getElementById('withdraw-info').textContent =
        `Withdrawing from bubble with ${bubble.balance_sats.toLocaleString()} sats ($${bubble.balance_usd.toFixed(2)})`;
    document.getElementById('withdraw-invoice').value = '';
    document.getElementById('withdraw-modal').style.display = 'flex';
}

async function saveBubbleName() {
    const id = document.getElementById('edit-bubble-id').value;
    const name = document.getElementById('bubble-name').value;
    await api(`/api/bubble/${id}`, 'PATCH', { name });
    closeEditModal();
    loadBubbles();
}

async function popBubble() {
    const id = document.getElementById('edit-bubble-id').value;
    if (!confirm('Pop this bubble? It must be empty first.')) return;
    const result = await api(`/api/bubble/${id}`, 'DELETE');
    if (result.error) {
        alert(result.error);
    }
    closeEditModal();
    loadBubbles();
}

async function confirmWithdraw() {
    const id = document.getElementById('withdraw-bubble-id').value;
    const invoice = document.getElementById('withdraw-invoice').value.trim();
    if (!invoice) {
        alert('Paste a Lightning invoice');
        return;
    }
    const result = await api('/api/withdraw', 'POST', {
        bubble_id: parseInt(id),
        payment_request: invoice,
    });
    if (result.error) {
        alert(result.error);
    }
    closeWithdrawModal();
    loadBubbles();
}

async function blowBubble() {
    const result = await api('/api/blow', 'POST');
    if (result.error) {
        alert(result.error);
        return;
    }
    showInvoiceModal(result, 'Blow a new bubble');
}

async function doubleBubble(bubbleId) {
    const result = await api('/api/double', 'POST', { bubble_id: bubbleId });
    if (result.error) {
        alert(result.error);
        return;
    }
    showInvoiceModal(result, 'Double your bubble');
}

async function loadBubbles() {
    const bubbles = await api('/api/bubbles');
    const container = document.getElementById('bubbles');
    container.innerHTML = '';

    if (bubbles.length === 0) {
        container.innerHTML = '<p style="color:#555;margin-top:80px">No bubbles yet — blow one to get started</p>';
        return;
    }

    let totalSats = 0;
    let totalUsd = 0;
    bubbles.forEach(b => {
        totalSats += b.balance_sats;
        totalUsd += b.balance_usd;
        container.appendChild(renderBubble(b));
    });

    document.getElementById('wallet-balance').textContent = `${totalSats.toLocaleString()} sats`;
    document.getElementById('wallet-usd').textContent = `$${totalUsd.toFixed(2)}`;
}

async function checkPendingPayments() {
    await api('/api/check-payments', 'POST');
    loadBubbles();
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('btn-blow').addEventListener('click', blowBubble);
    loadBubbles();
    setInterval(checkPendingPayments, 5000);
});
