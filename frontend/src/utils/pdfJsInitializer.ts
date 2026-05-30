/**
 * PDF.js Initialization Utility
 * Uses bundled PDF.js code and local worker assets only.
 */

export const PDF_LOADING_STRATEGIES = [
  {
    name: 'Bundled PDF.js',
    workerUrl: '/pdf.worker.min.js',
    libUrl: null,
    priority: 1
  }
];

interface PDFLoadingTask {
  promise: Promise<unknown>;
  destroy?: () => void;
}

interface PDFJSLibrary {
  GlobalWorkerOptions: {
    workerSrc: string;
  };
  getDocument: (config: unknown) => PDFLoadingTask;
}

export interface PDFJSInitResult {
  success: boolean;
  strategy: string;
  pdfjsLib: PDFJSLibrary | null;
  error?: string;
}

/**
 * Load PDF.js from the bundled dependency.
 */
async function loadPDFJSLibrary(libUrl: string | null): Promise<PDFJSLibrary> {
  if (libUrl) {
    throw new Error('Remote PDF.js library loading is disabled');
  }
  return await import('pdfjs-dist/build/pdf') as PDFJSLibrary;
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
          } catch {
            // Ignore cleanup errors
          }
        }, 100);
        
      } catch {
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
  return {
    cMapUrl: '/cmaps/',
    cMapPacked: true,
    standardFontDataUrl: '/standard_fonts/',
    verbosity: 0
  };
}

/**
 * Enhanced PDF loading with retry logic
 */
export async function loadPDFDocument(
  url: string,
  pdfjsLib: PDFJSLibrary,
  options: Record<string, unknown> = {},
  maxRetries: number = 3
): Promise<unknown> {
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
export function isPDFJSReady(pdfjsLib: unknown): boolean {
  try {
    const candidate = pdfjsLib as Partial<PDFJSLibrary> | null;
    return !!(
      candidate &&
      candidate.getDocument &&
      candidate.GlobalWorkerOptions &&
      candidate.GlobalWorkerOptions.workerSrc
    );
  } catch {
    return false;
  }
}
