// Create context menu on install
chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
      id: 'trackJob',
      title: 'Track this job',
      contexts: ['page']
    });
  });
  
  // Handle context menu click
  chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === 'trackJob') {
      // Open popup
      chrome.action.openPopup();
    }
  });
  
  // Listen for messages from content scripts
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'saveApplication') {
      // Get existing applications
      chrome.storage.local.get(['applications'], (result) => {
        const applications = result.applications || [];
        applications.push(request.data);
        
        chrome.storage.local.set({ applications }, () => {
          sendResponse({ success: true });
        });
      });
      return true; // Will respond asynchronously
    }
  });