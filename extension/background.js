// Background Service Worker - WebSocket Client
// Connects to Python WebSocket server and forwards commands to content scripts

const WS_URL = 'ws://192.168.86.247:8765';
let ws = null;
let reconnectInterval = null;
let messageQueue = [];

// Safe WebSocket send with queue
function safeSend(data) {
  const message = typeof data === 'string' ? data : JSON.stringify(data);
  
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(message);
    return true;
  } else {
    // Queue message if not connected
    messageQueue.push(message);
    console.log('[MacroChrome] Message queued (not connected)');
    return false;
  }
}

// Flush queued messages
function flushQueue() {
  while (messageQueue.length > 0 && ws && ws.readyState === WebSocket.OPEN) {
    const message = messageQueue.shift();
    ws.send(message);
  }
}

// Connect to Python WebSocket server
function connectWebSocket() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    return;
  }

  console.log('[MacroChrome] Connecting to Python server...');
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    console.log('[MacroChrome] Connected to Python server');
    if (reconnectInterval) {
      clearInterval(reconnectInterval);
      reconnectInterval = null;
    }
    // Flush any queued messages
    flushQueue();
    // Notify Python that browser is ready
    safeSend({
      type: 'browser_ready',
      data: { userAgent: navigator.userAgent }
    });
  };

  ws.onmessage = async (event) => {
    try {
      const message = JSON.parse(event.data);
      console.log('[MacroChrome] Received from Python:', message);
      
      const result = await handleCommand(message);
      
      safeSend({
        type: 'response',
        id: message.id,
        data: result
      });
    } catch (error) {
      console.error('[MacroChrome] Error handling message:', error);
      safeSend({
        type: 'error',
        id: message.id,
        error: error.message
      });
    }
  };

  ws.onclose = () => {
    console.log('[MacroChrome] Disconnected from Python server');
    ws = null;
    // Auto-reconnect
    if (!reconnectInterval) {
      reconnectInterval = setInterval(connectWebSocket, 3000);
    }
  };
  
  ws.onerror = (error) => {
    console.error('[MacroChrome] WebSocket error:', error);
  };
}

// Handle messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'get_status') {
    sendResponse({ connected: ws && ws.readyState === WebSocket.OPEN });
    return true;
  }
  
  if (request.action === 'reconnect') {
    connectWebSocket();
    sendResponse({ success: true });
    return true;
  }
  
  if (request.action === 'test_message') {
    const sent = safeSend({
      type: 'test',
      data: request.data
    });
    sendResponse({ success: sent });
    return true;
  }
});

// Handle different command types
async function handleCommand(message) {
  const { type, data } = message;

  switch (type) {
    case 'execute_script':
      return await executeInActiveTab(data.script);
    
    case 'get_page_source':
      return await executeInActiveTab(`
        (() => ({
          url: window.location.href,
          title: document.title,
          html: document.documentElement.outerHTML,
          text: document.body.innerText.substring(0, 50000) // Limit text size
        }))()
      `);
    
    case 'get_element_info':
      return await executeInActiveTab(`
        (() => {
          const el = document.querySelector('${data.selector}');
          if (!el) return null;
          const rect = el.getBoundingClientRect();
          return {
            tagName: el.tagName,
            id: el.id,
            className: el.className,
            text: el.innerText?.substring(0, 1000),
            html: el.outerHTML?.substring(0, 2000),
            rect: {
              x: rect.x,
              y: rect.y,
              width: rect.width,
              height: rect.height
            },
            visible: rect.width > 0 && rect.height > 0
          };
        })()
      `);
    
    case 'click_element':
      return await executeInActiveTab(`
        (() => {
          const el = document.querySelector('${data.selector}');
          if (!el) return { success: false, error: 'Element not found' };
          el.click();
          return { success: true, tagName: el.tagName };
        })()
      `);
    
    case 'type_text':
      return await executeInActiveTab(`
        (() => {
          const el = document.querySelector('${data.selector}');
          if (!el) return { success: false, error: 'Element not found' };
          el.focus();
          el.value = '${data.text.replace(/'/g, "\\'")}';
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
          return { success: true, tagName: el.tagName };
        })()
      `);
    
    case 'find_elements':
      return await executeInActiveTab(`
        (() => {
          const elements = document.querySelectorAll('${data.selector}');
          return Array.from(elements).slice(0, ${data.limit || 10}).map((el, i) => ({
            index: i,
            tagName: el.tagName,
            id: el.id,
            className: el.className?.substring(0, 100),
            text: el.innerText?.substring(0, 200),
            href: el.href || null
          }));
        })()
      `);

    default:
      throw new Error(`Unknown command type: ${type}`);
  }
}

// Execute script in the active tab
async function executeInActiveTab(script) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) {
    throw new Error('No active tab found');
  }

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (code) => {
        try {
          return eval(code);
        } catch (e) {
          return { error: e.message };
        }
      },
      args: [script]
    });
    return results[0]?.result;
  } catch (error) {
    throw new Error(`Script execution failed: ${error.message}`);
  }
}

// Initialize connection on startup
connectWebSocket();

// Also connect when extension is installed/updated
chrome.runtime.onInstalled.addListener(connectWebSocket);
