// Indeed job data extractor

function extractIndeedJobData() {
    try {
      let company = 
        document.querySelector('[data-testid="inlineHeader-companyName"]')?.textContent?.trim() ||
        document.querySelector('.jobsearch-InlineCompanyRating-companyHeader')?.textContent?.trim() ||
        document.querySelector('[class*="companyName"]')?.textContent?.trim() ||
        '';
      
      let roleTitle = 
        document.querySelector('[data-testid="jobsearch-JobInfoHeader-title"]')?.textContent?.trim() ||
        document.querySelector('.jobsearch-JobInfoHeader-title')?.textContent?.trim() ||
        document.querySelector('h1[class*="jobTitle"]')?.textContent?.trim() ||
        '';
      
      let location = 
        document.querySelector('[data-testid="inlineHeader-companyLocation"]')?.textContent?.trim() ||
        document.querySelector('.jobsearch-InlineCompanyRating-companyLocation')?.textContent?.trim() ||
        '';
      
      return {
        company: company,
        roleTitle: roleTitle,
        location: location,
        source: 'Indeed'
      };
    } catch (error) {
      console.error('Indeed extraction error:', error);
      return null;
    }
  }
  
  // Listen for requests from popup
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getJobData') {
      const data = extractIndeedJobData();
      sendResponse({ data: data });
    }
  });