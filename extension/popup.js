// Get current date in YYYY-MM-DD format
function getTodayDate() {
    const today = new Date();
    return today.toISOString().split('T')[0];
  }
  
  // Set default applied date to today
  document.getElementById('appliedDate').value = getTodayDate();
  
  // Try to prefill job URL from current tab
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      const url = tabs[0].url;
      document.getElementById('jobUrl').value = url;
      
      // Try to get extracted data from content script
      chrome.tabs.sendMessage(tabs[0].id, { action: 'getJobData' }, (response) => {
        if (response && response.data) {
          if (response.data.company) {
            document.getElementById('company').value = response.data.company;
          }
          if (response.data.roleTitle) {
            document.getElementById('roleTitle').value = response.data.roleTitle;
          }
          if (response.data.location) {
            document.getElementById('location').value = response.data.location;
          }
        }
      });
    }
  });
  
  // Show message
  function showMessage(text, type) {
    const messageEl = document.getElementById('message');
    messageEl.textContent = text;
    messageEl.className = `message ${type}`;
    messageEl.style.display = 'block';
    
    setTimeout(() => {
      messageEl.style.display = 'none';
    }, 3000);
  }
  
  // Get form data
  function getFormData() {
    return {
      company: document.getElementById('company').value.trim(),
      role_title: document.getElementById('roleTitle').value.trim(),
      location: document.getElementById('location').value.trim(),
      source: document.getElementById('source').value,
      status: document.getElementById('status').value,
      applied_date: document.getElementById('appliedDate').value,
      job_url: document.getElementById('jobUrl').value.trim(),
      notes: document.getElementById('notes').value.trim(),
      captured_at: new Date().toISOString()
    };
  }
  
  // Validate form
  function validateForm(data) {
    if (!data.company) {
      showMessage('Company is required', 'error');
      return false;
    }
    if (!data.role_title) {
      showMessage('Role Title is required', 'error');
      return false;
    }
    return true;
  }
  
  // Save application
  document.getElementById('saveBtn').addEventListener('click', () => {
    const data = getFormData();
    
    if (!validateForm(data)) {
      return;
    }
    
    // Get existing entries
    chrome.storage.local.get(['applications'], (result) => {
      const applications = result.applications || [];
      applications.push(data);
      
      chrome.storage.local.set({ applications }, () => {
        showMessage('Application saved!', 'success');
        
        // Clear form except source and status
        document.getElementById('company').value = '';
        document.getElementById('roleTitle').value = '';
        document.getElementById('location').value = '';
        document.getElementById('appliedDate').value = getTodayDate();
        document.getElementById('jobUrl').value = '';
        document.getElementById('notes').value = '';
      });
    });
  });
  
  // Download CSV
  document.getElementById('downloadCsvBtn').addEventListener('click', () => {
    chrome.storage.local.get(['applications'], (result) => {
      const applications = result.applications || [];
      
      if (applications.length === 0) {
        showMessage('No applications to export', 'error');
        return;
      }
      
      // Create CSV
      const headers = ['company', 'role_title', 'location', 'source', 'status', 'applied_date', 'job_url', 'notes'];
      const csvRows = [headers.join(',')];
      
      applications.forEach(app => {
        const row = headers.map(header => {
          const value = app[header] || '';
          // Escape quotes and wrap in quotes if contains comma
          return value.includes(',') || value.includes('"') 
            ? `"${value.replace(/"/g, '""')}"` 
            : value;
        });
        csvRows.push(row.join(','));
      });
      
      const csv = csvRows.join('\n');
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.href = url;
      a.download = `job_applications_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      
      showMessage(`Exported ${applications.length} applications as CSV`, 'success');
    });
  });
  
  // Download JSON
  document.getElementById('downloadJsonBtn').addEventListener('click', () => {
    chrome.storage.local.get(['applications'], (result) => {
      const applications = result.applications || [];
      
      if (applications.length === 0) {
        showMessage('No applications to export', 'error');
        return;
      }
      
      const json = JSON.stringify(applications, null, 2);
      const blob = new Blob([json], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.href = url;
      a.download = `job_applications_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      
      showMessage(`Exported ${applications.length} applications as JSON`, 'success');
    });
  });