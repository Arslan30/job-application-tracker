// StepStone job data extractor

function extractStepStoneJobData() {
    try {
      let company = 
        document.querySelector('[data-at="header-company-name"]')?.textContent?.trim() ||
        document.querySelector('.listing-header__company')?.textContent?.trim() ||
        '';
      
      let roleTitle = 
        document.querySelector('[data-at="header-job-title"]')?.textContent?.trim() ||
        document.querySelector('.listing-header__title')?.textContent?.trim() ||
        document.querySelector('h1')?.textContent?.trim() ||
        '';
      
      let location = 
        document.querySelector('[data-at="header-location"]')?.textContent?.trim() ||
        document.querySelector('.listing-header__location')?.textContent?.trim() ||
        '';
      
      return {
        company: company,
        roleTitle: roleTitle,
        location: location,
        source: 'StepStone'
      };
    } catch (error) {
      console.error('StepStone extraction error:', error);
      return null;
    }
  }
  
  // Listen for requests from popup
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getJobData') {
      const data = extractStepStoneJobData();
      sendResponse({ data: data });
    }
  });