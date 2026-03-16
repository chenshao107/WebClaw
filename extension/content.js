// Content Script - Injected into all pages
// Provides additional capabilities and communication bridge

console.log('[MacroChrome] Content script loaded on', window.location.href);

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'ping') {
    sendResponse({ status: 'ok', url: window.location.href });
    return true;
  }
  
  if (request.action === 'get_full_html') {
    sendResponse({
      url: window.location.href,
      title: document.title,
      html: document.documentElement.outerHTML
    });
    return true;
  }
  
  if (request.action === 'execute_custom') {
    try {
      const result = eval(request.script);
      sendResponse({ success: true, result });
    } catch (error) {
      sendResponse({ success: false, error: error.message });
    }
    return true;
  }
});

// Expose a global object for debugging
window.MacroChromeBridge = {
  version: '0.1.0',
  ping: () => 'pong'
};
