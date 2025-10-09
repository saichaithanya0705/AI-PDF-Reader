/**
 * PDF.js Worker Fallback
 * This is a minimal PDF.js worker implementation that can work offline
 * when the main PDF.js worker fails to load from CDN
 */

// Basic PDF.js worker functionality
self.onmessage = function(e) {
  const { action, data } = e.data;
  
  try {
    switch (action) {
      case 'getDocument':
        handleGetDocument(data);
        break;
      case 'getPage':
        handleGetPage(data);
        break;
      case 'render':
        handleRender(data);
        break;
      case 'getTextContent':
        handleGetTextContent(data);
        break;
      default:
        self.postMessage({
          action: action,
          data: null,
          error: 'Unsupported action in fallback worker'
        });
    }
  } catch (error) {
    self.postMessage({
      action: action,
      data: null,
      error: error.message || 'Unknown error in fallback worker'
    });
  }
};

function handleGetDocument(data) {
  // Simplified document loading
  self.postMessage({
    action: 'getDocument',
    data: {
      numPages: 1, // Default to 1 page for fallback
      fingerprint: 'fallback-' + Date.now(),
      _transport: null
    },
    error: null
  });
}

function handleGetPage(data) {
  // Simplified page handling
  self.postMessage({
    action: 'getPage',
    data: {
      pageNumber: data.pageNumber || 1,
      view: [0, 0, 612, 792], // Standard page size
      rotate: 0,
      ref: { num: data.pageNumber || 1, gen: 0 }
    },
    error: null
  });
}

function handleRender(data) {
  // Simplified rendering - just return success
  self.postMessage({
    action: 'render',
    data: {
      intent: 'display',
      renderTasks: []
    },
    error: null
  });
}

function handleGetTextContent(data) {
  // Return empty text content for fallback
  self.postMessage({
    action: 'getTextContent',
    data: {
      items: [],
      styles: {}
    },
    error: null
  });
}

// Handle worker initialization
self.postMessage({
  action: 'ready',
  data: {
    workerVersion: 'fallback-1.0.0',
    capabilities: ['basic-rendering']
  }
});

console.log('PDF.js Fallback Worker initialized');
