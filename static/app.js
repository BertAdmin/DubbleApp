const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ||
    document.querySelector('input[name="csrf_token"]')?.value || '';

async function api(url, method = 'GET', body = null) {
    const opts = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
    };
    if (body) opts.body = JSON.stringify(body);
    const resp = await fetch(url, opts);
    return resp.json();
}

let currentPaymentHash = null;

function closeModal() {
    document.getElementById('invoice-modal').style.display = 'none';
    currentPaymentHash = null;
}

function closeEditModal() {
    document.getElementById('edit-modal').style.display = 'none';
}

function closeWithdrawModal() {
    document.getElementById('withdraw-modal').style.display = 'none';
}

function copyInvoice() {
    const invoice = document.getElementById('modal-invoice').textContent;
    navigator.clipboard.writeText(invoice).then(() => {
        document.getElementById('modal-copy').textContent = 'Copied!';
        setTimeout(() => {
            document.getElementById('modal-copy').textContent = 'Copy Invoice';
        }, 2000);
    });
}

async function checkPayment() {
    if (!currentPaymentHash) return;
    const btn = document.getElementById('modal-check');
    btn.textContent = 'Checking...';
    btn.disabled = true;

    const result = await api(`/api/confirm/${currentPaymentHash}`, 'POST');
    if (result.error) {
        btn.textContent = 'Not yet — try again';
        setTimeout(() => {
            btn.textContent = 'I\'ve Paid';
            btn.disabled = false;
        }, 2000);
    } else {
        closeModal();
        loadBubbles();
    }
}

async function showInvoiceModal(data, title) {
    currentPaymentHash = data.payment_hash;
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-amount').textContent =
        `${data.amount_sats.toLocaleString()} sats ($${data.amount_usd.toFixed(2)})`;
    document.getElementById('modal-invoice').textContent = data.payment_request;
    document.getElementById('modal-check').textContent = 'I\'ve Paid';
    document.getElementById('modal-check').disabled = false;

    const qrContainer = document.getElementById('modal-qr');
    qrContainer.innerHTML = '';
    generateQR(data.payment_request, qrContainer);

    document.getElementById('invoice-modal').style.display = 'flex';
}

function generateQR(text, container) {
    new QRCode(container, {
        text: text,
        width: 200,
        height: 200,
        colorDark: '#000000',
        colorLight: '#ffffff',
        correctLevel: QRCode.CorrectLevel.M,
    });
}
