// LinkedIn job data extractor

function extractLinkedInJobData() {
    try {
      // Try multiple selectors as LinkedIn's DOM changes frequently
      let company = 
        document.querySelector('.job-details-jobs-unified-top-card__company-name')?.textContent?.trim() ||
        document.querySelector('.jobs-unified-top-card__company-name')?.textContent?.trim() ||
        document.querySelector('[class*="company-name"]')?.textContent?.trim() ||
        '';
      
      let roleTitle = 
        document.querySelector('.job-details-jobs-unified-top-card__job-title')?.textContent?.trim() ||
        document.querySelector('.jobs-unified-top-card__job-title')?.textContent?.trim() ||
        document.querySelector('h1[class*="job-title"]')?.textContent?.trim() ||
        '';
      
      let location = 
        document.querySelector('.job-details-jobs-unified-top-card__primary-description')?.textContent?.trim() ||
        document.querySelector('.jobs-unified-top-card__bullet')?.textContent?.trim() ||
        '';
      
      // Clean up location (remove extra text)
      if (location) {
        location = location.split('·')[0].trim();
      }
      
      return {
        company: company,
        roleTitle: roleTitle,
        location: location,
        source: 'LinkedIn'
      };
    } catch (error) {
      console.error('LinkedIn extraction error:', error);
      return null;
    }
  }
  
  // Listen for requests from popup
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getJobData') {
      const data = extractLinkedInJobData();
      sendResponse({ data: data });
    }
  });