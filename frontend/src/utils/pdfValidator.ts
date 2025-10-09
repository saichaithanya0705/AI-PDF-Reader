/**
 * PDF Validation Utility
 * Flexible validation for PDF files - optimized to accept most valid PDFs while catching major issues
 * Updated to be more permissive and work with various PDF types and generators
 */

export interface PDFValidationResult {
  isValid: boolean;
  issues: string[];
  warnings: string[];
  fileInfo: {
    size: number;
    type: string;
    name: string;
  };
}

export class PDFValidator {
  private static readonly PDF_SIGNATURE = '%PDF-';
  private static readonly MIN_PDF_SIZE = 50; // Reduced from 100 - some minimal PDFs can be smaller
  private static readonly MAX_PDF_SIZE = 200 * 1024 * 1024; // Increased to 200MB for large documents
  private static readonly LARGE_FILE_WARNING = 75 * 1024 * 1024; // 75MB warning threshold
  
  /**
   * Validate a PDF file comprehensively
   */
  static async validatePDF(file: File): Promise<PDFValidationResult> {
    const result: PDFValidationResult = {
      isValid: true,
      issues: [],
      warnings: [],
      fileInfo: {
        size: file.size,
        type: file.type,
        name: file.name
      }
    };

    try {
      // 1. Basic file checks
      this.validateBasicFile(file, result);
      
      // 2. File size checks
      this.validateFileSize(file, result);
      
      // 3. MIME type validation
      this.validateMimeType(file, result);
      
      // 4. File extension validation
      this.validateFileExtension(file, result);
      
      // 5. PDF header validation (read first few bytes)
      await this.validatePDFHeader(file, result);
      
      // 6. PDF structure validation (basic)
      await this.validatePDFStructure(file, result);
      
      // Set overall validity
      result.isValid = result.issues.length === 0;
      
    } catch (error) {
      result.isValid = false;
      result.issues.push(`Validation error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }

    return result;
  }

  /**
   * Basic file validation
   */
  private static validateBasicFile(file: File, result: PDFValidationResult): void {
    if (!file) {
      result.issues.push('No file provided');
      return;
    }

    if (!file.name || file.name.trim() === '') {
      result.issues.push('File has no name');
    }

    if (file.size === 0) {
      result.issues.push('File is empty (0 bytes)');
    }
  }

  /**
   * File size validation - more flexible limits
   */
  private static validateFileSize(file: File, result: PDFValidationResult): void {
    // Only block extremely small files (likely not real PDFs)
    if (file.size < this.MIN_PDF_SIZE) {
      result.issues.push(`File too small (${file.size} bytes). Minimum: ${this.MIN_PDF_SIZE} bytes`);
    }

    // Only block extremely large files (server/memory concerns)
    if (file.size > this.MAX_PDF_SIZE) {
      result.issues.push(`File too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Maximum: ${this.MAX_PDF_SIZE / 1024 / 1024}MB`);
    }

    // Friendly warning for large files (but still allow them)
    if (file.size > this.LARGE_FILE_WARNING) {
      result.warnings.push(`Large file (${(file.size / 1024 / 1024).toFixed(1)}MB) may take longer to process`);
    }
  }

  /**
   * MIME type validation - more permissive approach
   */
  private static validateMimeType(file: File, result: PDFValidationResult): void {
    const validMimeTypes = [
      'application/pdf', 
      'application/x-pdf',
      'application/acrobat',
      'application/vnd.pdf',
      'text/pdf',
      'text/x-pdf'
    ];
    
    if (!validMimeTypes.includes(file.type)) {
      if (file.type === '' || file.type === 'application/octet-stream') {
        // Many browsers don't set MIME type or use generic type - this is common and OK
        result.warnings.push('MIME type not detected - will validate based on file content');
      } else {
        // Don't block uploads for unknown MIME types, just warn
        result.warnings.push(`Unexpected MIME type: ${file.type}. Will validate based on file content`);
      }
    }
  }

  /**
   * File extension validation - flexible approach
   */
  private static validateFileExtension(file: File, result: PDFValidationResult): void {
    const fileName = file.name.toLowerCase();
    
    // Accept various PDF-related extensions
    const validExtensions = ['.pdf', '.PDF'];
    const hasValidExtension = validExtensions.some(ext => fileName.endsWith(ext.toLowerCase()));
    
    if (!hasValidExtension) {
      // Don't block files without .pdf extension - rely on content validation instead
      result.warnings.push('File does not have .pdf extension - will validate based on file content');
    }

    // Only block clearly dangerous extensions
    const dangerousExtensions = ['.exe', '.bat', '.cmd', '.scr', '.com', '.pif', '.vbs', '.js'];
    for (const ext of dangerousExtensions) {
      if (fileName.includes(ext)) {
        result.issues.push(`Potentially dangerous file extension detected: ${ext}`);
      }
    }
  }

  /**
   * PDF header validation - more flexible header checking
   */
  private static async validatePDFHeader(file: File, result: PDFValidationResult): Promise<void> {
    try {
      // Read first 20 bytes to account for potential whitespace or BOM
      const headerBuffer = await this.readFileBytes(file, 0, 20);
      const headerText = new TextDecoder('ascii', { fatal: false }).decode(headerBuffer);
      
      // Look for PDF signature anywhere in the first 20 bytes (some PDFs have BOM or whitespace)
      const pdfSignatureIndex = headerText.indexOf(this.PDF_SIGNATURE);
      
      if (pdfSignatureIndex === -1) {
        // Try reading more bytes in case the signature is further in
        const largerBuffer = await this.readFileBytes(file, 0, 100);
        const largerText = new TextDecoder('ascii', { fatal: false }).decode(largerBuffer);
        
        if (!largerText.includes(this.PDF_SIGNATURE)) {
          result.issues.push('PDF signature not found. File may not be a valid PDF');
        } else {
          result.warnings.push('PDF signature found but not at start of file - unusual but may still work');
        }
      } else {
        // Extract PDF version with more flexible pattern
        const versionMatch = headerText.match(/%PDF-(\d+\.?\d*)/);
        if (versionMatch) {
          const version = parseFloat(versionMatch[1]);
          if (version < 0.9 || version > 3.0) { // Expanded range for future versions
            result.warnings.push(`PDF version ${version} is outside typical range but may still work`);
          }
        } else {
          result.warnings.push('PDF version not detected in header');
        }
      }
    } catch (error) {
      result.warnings.push('Cannot fully read PDF header - will attempt to process anyway');
    }
  }

  /**
   * Basic PDF structure validation - more lenient approach
   */
  private static async validatePDFStructure(file: File, result: PDFValidationResult): Promise<void> {
    try {
      // Read last 2048 bytes to check for EOF marker (some PDFs have extra data at end)
      const endBuffer = await this.readFileBytes(file, Math.max(0, file.size - 2048), Math.min(2048, file.size));
      const endText = new TextDecoder('ascii', { fatal: false }).decode(endBuffer);
      
      // Look for various EOF patterns
      const hasEOF = endText.includes('%%EOF') || 
                    endText.includes('%EOF') || 
                    endText.includes('endstream') ||
                    endText.includes('endobj');
      
      if (!hasEOF) {
        result.warnings.push('Standard PDF end marker not found - file may still be valid');
      }

      // Check for xref table or modern cross-reference streams
      const hasXRef = endText.includes('xref') || 
                     endText.includes('/XRef') || 
                     endText.includes('/Root') ||
                     endText.includes('trailer') ||
                     endText.includes('/Type/Catalog');
      
      if (!hasXRef) {
        result.warnings.push('PDF cross-reference structure not detected - may use non-standard format');
      }

      // Only check for PDF objects in larger files
      if (file.size > 2000) {
        // Sample multiple sections of the file
        const sampleSize = Math.min(1024, Math.floor(file.size / 4));
        const positions = [
          Math.floor(file.size * 0.25),
          Math.floor(file.size * 0.5),
          Math.floor(file.size * 0.75)
        ];
        
        let foundObjects = false;
        for (const pos of positions) {
          try {
            const sampleBuffer = await this.readFileBytes(file, pos, sampleSize);
            const sampleText = new TextDecoder('ascii', { fatal: false }).decode(sampleBuffer);
            
            // Look for PDF objects or streams
            const hasObjects = /\d+\s+\d+\s+obj/.test(sampleText) || 
                              /\/Type\s*\//.test(sampleText) ||
                              /stream\s*$/.test(sampleText) ||
                              /endstream/.test(sampleText);
            
            if (hasObjects) {
              foundObjects = true;
              break;
            }
          } catch (e) {
            // Continue checking other positions
          }
        }
        
        if (!foundObjects) {
          result.warnings.push('PDF objects not found in sampled locations - may use compressed or unusual format');
        }
      }

    } catch (error) {
      result.warnings.push('Cannot validate PDF structure completely - will attempt to process anyway');
    }
  }

  /**
   * Read specific bytes from file
   */
  private static readFileBytes(file: File, start: number, length: number): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = () => {
        if (reader.result instanceof ArrayBuffer) {
          resolve(reader.result);
        } else {
          reject(new Error('Failed to read file as ArrayBuffer'));
        }
      };
      
      reader.onerror = () => reject(new Error('File read error'));
      
      const blob = file.slice(start, start + length);
      reader.readAsArrayBuffer(blob);
    });
  }

  /**
   * Get validation summary for UI display
   */
  static getValidationSummary(result: PDFValidationResult): string {
    if (result.isValid && result.warnings.length === 0) {
      return 'Valid PDF - ready for upload';
    }
    
    if (!result.isValid) {
      return result.issues[0]; // Show first critical issue
    }
    
    if (result.warnings.length > 0) {
      return `Acceptable PDF - ${result.warnings[0]}`;
    }
    
    return 'PDF status unknown';
  }

  /**
   * Get severity level for UI styling
   */
  static getSeverityLevel(result: PDFValidationResult): 'success' | 'warning' | 'error' {
    if (!result.isValid) return 'error';
    if (result.warnings.length > 0) return 'warning';
    return 'success';
  }

  /**
   * Get detailed validation information for debugging
   */
  static getValidationDetails(result: PDFValidationResult): string {
    const details = [];
    
    if (result.isValid) {
      details.push('✅ File passed validation');
    } else {
      details.push('❌ File failed validation');
    }
    
    if (result.issues.length > 0) {
      details.push(`Issues: ${result.issues.join(', ')}`);
    }
    
    if (result.warnings.length > 0) {
      details.push(`Warnings: ${result.warnings.join(', ')}`);
    }
    
    details.push(`Size: ${(result.fileInfo.size / 1024 / 1024).toFixed(2)}MB`);
    details.push(`Type: ${result.fileInfo.type || 'Not detected'}`);
    
    return details.join(' | ');
  }
}
