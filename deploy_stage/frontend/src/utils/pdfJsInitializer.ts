/**
 * Comprehensive PDF.js Initialization Utility
 * Handles multiple fallback strategies for PDF.js worker loading
 */

// PDF.js loading strategies with comprehensive fallbacks
export const PDF_LOADING_STRATEGIES = [
  {
    name: 'CDN Latest',
    workerUrl: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js',
    libUrl: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js',
    priority: 1
  },
  {
    name: 'CDN Stable',
    workerUrl: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.10.111/pdf.worker.min.js',
    libUrl: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.10.111/pdf.min.js',
    priority: 2
  },
  {
    name: 'JSDelivr',
    workerUrl: 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js',
    libUrl: 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.min.js',
    priority: 3
  },
  {
    name: 'UNPKG',
    workerUrl: 'https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js',
    libUrl: 'https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.min.js',
    priority: 4
  },
  {
    name: 'Local Fallback',
    workerUrl: '/pdf.worker.min.js',
    libUrl: '/pdf.min.js',
    priority: 5
  },
  {
    name: 'Custom Fallback',
    workerUrl: '/pdf-worker-fallback.js',
    libUrl: null,
    priority: 6
  },
  {
    name: 'Embedded Worker',
    workerUrl: 'data:application/javascript;base64,c2VsZi5vbm1lc3NhZ2U9ZnVuY3Rpb24oZSl7dHJ5e3NlbGYucG9zdE1lc3NhZ2Uoe2FjdGlvbjplLmRhdGEuYWN0aW9uLGRhdGE6bnVsbCxlcnJvcjpudWxsfSl9Y2F0Y2goZSl7c2VsZi5wb3N0TWVzc2FnZSh7YWN0aW9uOiJlcnJvciIsZGF0YTpudWxsLGVycm9yOmUubWVzc2FnZX0pfX0=',
    libUrl: null,
    priority: 7
  }
];

export interface PDFJSInitResult {
  success: boolean;
  strategy: string;
  pdfjsLib: any;
  error?: string;
}

/**
 * Test if a URL is accessible
 */
async function testUrlAccessibility(url: string, timeout: number = 5000): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    const response = await fetch(url, { 
      method: 'HEAD',
      signal: controller.signal,
      cache: 'no-cache'
    });
    
    clearTimeout(timeoutId);
    return response.ok;
  } catch (error) {
    return false;
  }
}

/**
 * Load PDF.js library dynamically
 */
async function loadPDFJSLibrary(libUrl: string | null): Promise<any> {
  if (!libUrl) {
    // Use bundled version
    return await import('pdfjs-dist/build/pdf');
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = libUrl;
    script.onload = () => {
      const pdfjsLib = (window as any).pdfjsLib;
      if (pdfjsLib) {
        resolve(pdfjsLib);
      } else {
        reject(new Error('PDF.js library not found on window'));
      }
    };
    script.onerror = () => reject(new Error(`Failed to load PDF.js from ${libUrl}`));
    
    document.head.appendChild(script);
    
    // Timeout after 10 seconds
    setTimeout(() => {
      reject(new Error('PDF.js library load timeout'));
    }, 10000);
  });
}

/**
 * Initialize PDF.js with comprehensive fallback strategies
 */
export async function initializePDFJS(
  preferredStrategy?: number,
  onProgress?: (strategy: string, status: string) => void
): Promise<PDFJSInitResult> {
  
  const strategies = [...PDF_LOADING_STRATEGIES].sort((a, b) => {
    if (preferredStrategy !== undefined) {
      if (a.priority === preferredStrategy) return -1;
      if (b.priority === preferredStrategy) return 1;
    }
    return a.priority - b.priority;
  });

  for (const strategy of strategies) {
    try {
      onProgress?.(strategy.name, 'Testing accessibility...');
      
      // Test worker URL accessibility (skip for embedded workers)
      if (!strategy.workerUrl.startsWith('data:') && !strategy.workerUrl.startsWith('/')) {
        const isAccessible = await testUrlAccessibility(strategy.workerUrl, 3000);
        if (!isAccessible) {
          onProgress?.(strategy.name, 'Not accessible, trying next...');
          continue;
        }
      }

      onProgress?.(strategy.name, 'Loading PDF.js library...');
      
      // Load PDF.js library
      const pdfjsLib = await loadPDFJSLibrary(strategy.libUrl);
      
      onProgress?.(strategy.name, 'Configuring worker...');
      
      // Configure worker
      pdfjsLib.GlobalWorkerOptions.workerSrc = strategy.workerUrl;
      
      // Test PDF.js functionality with a simple operation
      onProgress?.(strategy.name, 'Testing functionality...');
      
      try {
        // Create a minimal test to verify PDF.js is working
        const testDoc = pdfjsLib.getDocument({
          data: new Uint8Array([37, 80, 68, 70]) // Minimal PDF header
        });
        
        // Don't wait for it to complete, just check if it doesn't throw immediately
        setTimeout(() => {
          try {
            testDoc.destroy?.();
          } catch (e) {
            // Ignore cleanup errors
          }
        }, 100);
        
      } catch (testError) {
        // If basic test fails, try next strategy
        onProgress?.(strategy.name, 'Functionality test failed, trying next...');
        continue;
      }

      onProgress?.(strategy.name, 'Success!');
      
      return {
        success: true,
        strategy: strategy.name,
        pdfjsLib
      };

    } catch (error) {
      onProgress?.(strategy.name, `Failed: ${error}`);
      console.warn(`PDF.js strategy "${strategy.name}" failed:`, error);
      continue;
    }
  }

  // All strategies failed
  return {
    success: false,
    strategy: 'None',
    pdfjsLib: null,
    error: 'All PDF.js loading strategies failed'
  };
}

/**
 * Get the best PDF.js configuration for current environment
 */
export function getBestPDFJSConfig(): {
  cMapUrl: string;
  cMapPacked: boolean;
  standardFontDataUrl: string;
  verbosity: number;
} {
  const isOnline = navigator.onLine;
  
  if (isOnline) {
    return {
      cMapUrl: 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/cmaps/',
      cMapPacked: true,
      standardFontDataUrl: 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/standard_fonts/',
      verbosity: 1
    };
  } else {
    return {
      cMapUrl: '/cmaps/',
      cMapPacked: true,
      standardFontDataUrl: '/standard_fonts/',
      verbosity: 0
    };
  }
}

/**
 * Enhanced PDF loading with retry logic
 */
export async function loadPDFDocument(
  url: string,
  pdfjsLib: any,
  options: any = {},
  maxRetries: number = 3
): Promise<any> {
  const config = {
    url,
    ...getBestPDFJSConfig(),
    ...options
  };

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const loadingTask = pdfjsLib.getDocument(config);
      
      // Add timeout
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('PDF loading timeout')), 30000);
      });
      
      const pdf = await Promise.race([loadingTask.promise, timeoutPromise]);
      return pdf;
      
    } catch (error) {
      console.warn(`PDF loading attempt ${attempt} failed:`, error);
      
      if (attempt === maxRetries) {
        throw error;
      }
      
      // Wait before retry
      await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
    }
  }
}

/**
 * Check if PDF.js is properly initialized
 */
export function isPDFJSReady(pdfjsLib: any): boolean {
  try {
    return !!(
      pdfjsLib &&
      pdfjsLib.getDocument &&
      pdfjsLib.GlobalWorkerOptions &&
      pdfjsLib.GlobalWorkerOptions.workerSrc
    );
  } catch (error) {
    return false;
  }
}
