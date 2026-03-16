// Popup script

const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const currentPage = document.getElementById('currentPage');
const reconnectBtn = document.getElementById('reconnectBtn');
const testBtn = document.getElementById('testBtn');

// Update status display
async function updateStatus() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  currentPage.textContent = tab?.url || '-';
  
  // Check connection status via background script
  chrome.runtime.sendMessage({ action: 'get_status' }, (response) => {
    if (response?.connected) {
      statusDot.className = 'status-dot connected';
      statusText.textContent = 'Connected to Python';
    } else {
      statusDot.className = 'status-dot disconnected';
      statusText.textContent = 'Disconnected';
    }
  });
}

// Initialize
updateStatus();

// Reconnect button
reconnectBtn.addEventListener('click', () => {
  chrome.runtime.sendMessage({ action: 'reconnect' });
  setTimeout(updateStatus, 500);
});

// Test button
testBtn.addEventListener('click', async () => {
  testBtn.disabled = true;
  testBtn.textContent = 'Sending...';
  
  chrome.runtime.sendMessage({ 
    action: 'test_message',
    data: { timestamp: Date.now() }
  }, (response) => {
    testBtn.disabled = false;
    testBtn.textContent = 'Send Test Message';
    
    if (response?.success) {
      alert('Test message sent successfully!');
    } else {
      alert('Failed to send: ' + (response?.error || 'Unknown error'));
    }
  });
});
