// XING job data extractor

function extractXingJobData() {
    try {
      let company = 
        document.querySelector('[data-testid="company-name"]')?.textContent?.trim() ||
        document.querySelector('.job-details-company-name')?.textContent?.trim() ||
        '';
      
      let roleTitle = 
        document.querySelector('[data-testid="job-title"]')?.textContent?.trim() ||
        document.querySelector('.job-details-title')?.textContent?.trim() ||
        document.querySelector('h1')?.textContent?.trim() ||
        '';
      
      let location = 
        document.querySelector('[data-testid="job-location"]')?.textContent?.trim() ||
        document.querySelector('.job-details-location')?.textContent?.trim() ||
        '';
      
      return {
        company: company,
        roleTitle: roleTitle,
        location: location,
        source: 'XING'
      };
    } catch (error) {
      console.error('XING extraction error:', error);
      return null;
    }
  }
  
  // Listen for requests from popup
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getJobData') {
      const data = extractXingJobData();
      sendResponse({ data: data });
    }
  });