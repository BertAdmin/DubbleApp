document.addEventListener('DOMContentLoaded', () => {
    showAccounts();
});

// Define minimum and maximum sizes for bubbles
const MIN_SIZE = 50; // Minimum size in pixels
const MAX_SIZE = 500; // Maximum size in pixels
const MIN_BALANCE = 0.01; // Minimum balance
const MAX_BALANCE = 1000000; // Maximum balance

// Function to calculate bubble size based on balance
function calculateBubbleSize(balance) {
    return MIN_SIZE + ((balance - MIN_BALANCE) / (MAX_BALANCE - MIN_BALANCE)) * (MAX_SIZE - MIN_SIZE);
}

// Function to blow a new bubble
async function blowNewBubble() {
    const response = await fetch('/api/blow_new_bubble', {
        method: 'POST',
    });
    const data = await response.json();
    addBubble(data.id, data.balance);
}

// Function to add a bubble to the accounts section
function addBubble(id, balance) {
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    const size = calculateBubbleSize(balance);
    bubble.style.width = `${size}px`;
    bubble.style.height = `${size}px`;
    bubble.style.lineHeight = `${size}px`; // Ensure text is vertically centered
    bubble.textContent = `$${balance.toFixed(2)}`; // Display balance with two decimal places
    bubble.dataset.accountId = id; // Store account ID in dataset for later use
    bubble.onclick = () => doubleBubble(bubble); // Attach click event handler
    document.getElementById('accounts').appendChild(bubble);
}

// Function to show the double bubble modal
function showDoubleBubbleModal() {
    document.getElementById('doubleBubbleModal').style.display = 'block';
}

// Function to close a modal
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Function to double a bubble from the modal
async function doubleBubbleFromModal() {
    const accountId = document.getElementById('accountNumber').value;
    if (!accountId) {
        alert('Please enter an account ID.');
        return;
    }
    const response = await fetch('/api/double_bubble', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ account_id: parseInt(accountId) }),
    });
    const data = await response.json();
    if (data.balance !== null) {
        const bubble = document.querySelector(`.bubble[data-account-id="${accountId}"]`);
        if (bubble) {
            const size = calculateBubbleSize(data.balance);
            bubble.style.width = `${size}px`;
            bubble.style.height = `${size}px`;
            bubble.style.lineHeight = `${size}px`; // Ensure text is vertically centered
            bubble.textContent = `$${data.balance.toFixed(2)}`;
        }
    } else {
        alert('Account does not exist.');
    }
    closeModal('doubleBubbleModal');
}

// Function to double a bubble when clicked
async function doubleBubble(bubble) {
    const accountId = bubble.dataset.accountId;
    if (!accountId) {
        alert('Account ID not found.');
        return;
    }
    const response = await fetch('/api/double_bubble', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ account_id: parseInt(accountId) }),
    });
    const data = await response.json();
    if (data.balance !== null) {
        const size = calculateBubbleSize(data.balance);
        bubble.style.width = `${size}px`;
        bubble.style.height = `${size}px`;
        bubble.style.lineHeight = `${size}px`; // Ensure text is vertically centered
        bubble.textContent = `$${data.balance.toFixed(2)}`;
    } else {
        alert('Account does not exist.');
    }
}

// Function to show accounts
async function showAccounts() {
    const response = await fetch('/api/save_and_show_savings_report');
    const data = await response.json();
    const accountsDiv = document.getElementById('accounts');
    accountsDiv.innerHTML = '';
    data.forEach(account => {
        addBubble(account.ACCOUNT, account.AMOUNT);
    });
}

// Function to show the combine accounts modal
function showCombineAccountsModal() {
    document.getElementById('combineAccountsModal').style.display = 'block';
}

// Function to combine accounts
async function combineAccounts() {
    const accountId1 = document.getElementById('accountNumber1').value;
    const accountId2 = document.getElementById('accountNumber2').value;
    if (!accountId1 || !accountId2) {
        alert('Please enter both account IDs.');
        return;
    }
    const response = await fetch('/api/combine_accounts', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            account_id1: parseInt(accountId1),
            account_id2: parseInt(accountId2)
        }),
    });
    const data = await response.json();
    if (data.balance !== null) {
        showAccounts(); // Refresh accounts to reflect changes
    } else {
        alert('One or both accounts do not exist.');
    }
    closeModal('combineAccountsModal');
}

// Function to logout
function logout() {
    window.location.href = '/logout';
}