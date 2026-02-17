import React, { useCallback, useState } from 'react';
import { Upload, FileText, X, AlertTriangle, CheckCircle, AlertCircle } from 'lucide-react';
import { PDFValidator, PDFValidationResult } from '../utils/pdfValidator';

interface FileWithValidation extends File {
  validationResult?: PDFValidationResult;
}

interface UploadZoneProps {
  onFileSelect: (files: File | File[], considerPrevious?: boolean) => void;
  multiple?: boolean;
  className?: string;
}

const UploadZone: React.FC<UploadZoneProps> = ({ onFileSelect, multiple = false, className = '' }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileWithValidation[]>([]);
  const [considerPrevious, setConsiderPrevious] = useState(false);
  const [isValidating, setIsValidating] = useState(false);

  // Validate files and add validation results
  const validateFiles = async (files: File[]): Promise<FileWithValidation[]> => {
    setIsValidating(true);
    console.log('🔍 Validating', files.length, 'files...');

    const validatedFiles: FileWithValidation[] = [];

    for (const file of files) {
      console.log('🔍 Validating:', file.name);
      const validationResult = await PDFValidator.validatePDF(file);

      const fileWithValidation = file as FileWithValidation;
      fileWithValidation.validationResult = validationResult;

      validatedFiles.push(fileWithValidation);

      console.log(`📋 ${file.name}:`,
        validationResult.isValid ? '✅ Valid' : '❌ Invalid',
        validationResult.issues.length > 0 ? `Issues: ${validationResult.issues.join(', ')}` : '',
        validationResult.warnings.length > 0 ? `Warnings: ${validationResult.warnings.join(', ')}` : ''
      );
    }

    setIsValidating(false);
    return validatedFiles;
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files).filter(
      file => file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
    );
    console.log('Files dropped:', files.length, files.map(f => f.name));

    if (files.length > 0) {
      const validatedFiles = await validateFiles(files);

      if (multiple) {
        setSelectedFiles(validatedFiles);
      } else {
        // For single file, still validate but proceed
        setSelectedFiles(validatedFiles);
        onFileSelect(validatedFiles[0]);
      }
    }
  }, [multiple, onFileSelect]);

  const handleFileInput = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : [];
    console.log('Files selected via input:', files.length, files.map(f => f.name));

    if (files.length > 0) {
      const validatedFiles = await validateFiles(files);

      if (multiple) {
        setSelectedFiles(validatedFiles);
      } else {
        // For single file, still validate but proceed
        setSelectedFiles(validatedFiles);
        onFileSelect(validatedFiles[0]);
      }
    }
  }, [multiple, onFileSelect]);

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const uploadSelected = () => {
    if (selectedFiles.length > 0) {
      console.log('Uploading selected files:', selectedFiles.map(f => f.name));
      console.log('Consider previous PDFs:', considerPrevious);
      
      // Pass files along with the considerPrevious setting
      onFileSelect(selectedFiles, considerPrevious);
      setSelectedFiles([]);
    }
  };

  return (
    <div className="space-y-4">
      <div
        className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 ${
          isDragOver
            ? 'border-cyan-400 bg-cyan-400/5 scale-105'
            : 'border-slate-600 hover:border-slate-500'
        } ${className}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileInput}
          multiple={multiple}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        
        <div className="space-y-4">
          <div className="flex justify-center">
            <div className={`p-4 rounded-full transition-all duration-200 ${
              isDragOver 
                ? 'bg-cyan-400/20 text-cyan-400 scale-110' 
                : 'bg-slate-800 text-slate-400'
            }`}>
              <Upload className="w-8 h-8" />
            </div>
          </div>
          
          <div>
            <p className="text-lg font-semibold text-white mb-2">
              {isDragOver ? 'Drop your PDFs here' : 'Upload PDF Documents'}
            </p>
            <p className="text-sm text-slate-400">
              Drag and drop your PDF files or click to browse
              {multiple && <span className="block mt-1">Upload multiple files at once</span>}
            </p>
          </div>
        </div>
      </div>

      {/* Selected Files Preview (for bulk upload) */}
      {multiple && selectedFiles.length > 0 && (
        <div className="space-y-4">
          {/* Header with file count and validation status */}
          <div className="flex items-center justify-between bg-slate-800/50 rounded-lg p-4 border border-slate-600">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-cyan-400" />
              <h3 className="text-lg font-semibold text-white">
                Selected Files ({selectedFiles.length})
              </h3>
            </div>
            
            {isValidating && (
              <div className="flex items-center gap-2 text-cyan-400 text-sm">
                <div className="animate-spin w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full"></div>
                Validating...
              </div>
            )}
          </div>

          {/* Scrollable file list */}
          <div className="border border-slate-600 rounded-lg overflow-hidden">
            <div className="max-h-80 overflow-y-auto">
              <div className="space-y-1 p-2">
                {selectedFiles.map((file, index) => {
                  const validation = file.validationResult;
                  const isValid = validation?.isValid ?? true;
                  const severity = validation ? PDFValidator.getSeverityLevel(validation) : 'success';
                  const summary = validation ? PDFValidator.getValidationSummary(validation) : 'Validating...';

                  return (
                    <div
                      key={index}
                      className={`relative flex items-start gap-3 rounded-lg p-3 group border-l-4 transition-all duration-200 hover:bg-slate-700/30 ${
                        !isValid
                          ? 'bg-red-900/10 border-l-red-500'
                          : severity === 'warning'
                            ? 'bg-yellow-900/10 border-l-yellow-500'
                            : 'bg-slate-800/30 border-l-green-500'
                      }`}
                    >
                      {/* PDF Icon and Status */}
                      <div className="flex-shrink-0 flex flex-col items-center gap-1">
                        <div className={`p-2 rounded-lg ${
                          !isValid
                            ? 'bg-red-500/20'
                            : severity === 'warning'
                              ? 'bg-yellow-500/20'
                              : 'bg-green-500/20'
                        }`}>
                          <FileText className={`w-4 h-4 ${
                            !isValid ? 'text-red-400' :
                            severity === 'warning' ? 'text-yellow-400' :
                            'text-green-400'
                          }`} />
                        </div>
                        
                        {/* Validation Status Icon */}
                        <div className="flex-shrink-0">
                          {!validation ? (
                            <div className="animate-spin w-3 h-3 border border-cyan-400 border-t-transparent rounded-full"></div>
                          ) : severity === 'error' ? (
                            <AlertCircle className="w-3 h-3 text-red-400" />
                          ) : severity === 'warning' ? (
                            <AlertTriangle className="w-3 h-3 text-yellow-400" />
                          ) : (
                            <CheckCircle className="w-3 h-3 text-green-400" />
                          )}
                        </div>
                      </div>

                      <div className="flex-1 min-w-0">
                        {/* File name and size */}
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <p className={`text-sm font-medium ${
                            !isValid ? 'text-red-300' : 'text-white'
                          }`} title={file.name}>
                            {file.name}
                          </p>
                          <span className="text-xs text-slate-400 whitespace-nowrap">
                            {(file.size / (1024 * 1024)).toFixed(1)} MB
                          </span>
                        </div>

                        {/* Validation Status */}
                        {validation && (
                          <div className={`text-xs mb-1 font-medium ${
                            severity === 'error' ? 'text-red-400' :
                            severity === 'warning' ? 'text-yellow-400' :
                            'text-green-400'
                          }`}>
                            {severity === 'error' ? '❌' : severity === 'warning' ? '⚠️' : '✅'} {summary}
                          </div>
                        )}

                        {/* Issues and Warnings */}
                        {validation && (validation.issues.length > 0 || validation.warnings.length > 0) && (
                          <div className="space-y-1">
                            {/* Issues */}
                            {validation.issues.length > 0 && (
                              <div className="text-xs text-red-300 space-y-1">
                                {validation.issues.slice(0, 2).map((issue, i) => (
                                  <div key={i} className="flex items-start gap-1">
                                    <span className="text-red-400 mt-0.5">•</span>
                                    <span className="leading-tight">{issue}</span>
                                  </div>
                                ))}
                                {validation.issues.length > 2 && (
                                  <div className="text-red-400 text-xs italic">
                                    +{validation.issues.length - 2} more issues
                                  </div>
                                )}
                              </div>
                            )}
                            
                            {/* Warnings */}
                            {validation.warnings.length > 0 && (
                              <div className="text-xs text-yellow-300 space-y-1">
                                {validation.warnings.slice(0, 1).map((warning, i) => (
                                  <div key={i} className="flex items-start gap-1">
                                    <span className="text-yellow-400 mt-0.5">⚠</span>
                                    <span className="leading-tight">{warning}</span>
                                  </div>
                                ))}
                                {validation.warnings.length > 1 && (
                                  <div className="text-yellow-400 text-xs italic">
                                    +{validation.warnings.length - 1} more warnings
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Remove button */}
                      <button
                        onClick={() => removeFile(index)}
                        className="absolute top-2 right-2 p-1.5 hover:bg-slate-600 rounded-full text-slate-400 hover:text-white transition-all duration-200 opacity-0 group-hover:opacity-100"
                        title="Remove file"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Scroll indicator */}
            {selectedFiles.length > 5 && (
              <div className="bg-slate-700/50 px-3 py-2 text-xs text-slate-400 text-center border-t border-slate-600">
                Scroll to see all {selectedFiles.length} files
              </div>
            )}
          </div>

          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-4 bg-slate-800/30 rounded-lg p-4 border border-slate-600">
            <div className="text-center">
              <div className="text-lg font-bold text-green-400">
                {selectedFiles.filter(f => f.validationResult?.isValid !== false).length}
              </div>
              <div className="text-xs text-slate-400">Valid</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-yellow-400">
                {selectedFiles.filter(f => f.validationResult && f.validationResult.isValid && f.validationResult.warnings.length > 0).length}
              </div>
              <div className="text-xs text-slate-400">Warnings</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-red-400">
                {selectedFiles.filter(f => f.validationResult?.isValid === false).length}
              </div>
              <div className="text-xs text-slate-400">Errors</div>
            </div>
          </div>
          
          {/* Options */}
          <div className="flex items-center justify-between bg-slate-800/50 rounded-lg p-4 border border-slate-600">
            <span className="text-sm text-slate-300">Consider previously opened PDFs for recommendations</span>
            <div className="relative inline-flex cursor-pointer items-center">
              <input
                type="checkbox"
                className="peer sr-only"
                checked={considerPrevious}
                onChange={() => setConsiderPrevious(!considerPrevious)}
              />
              <div className="peer h-5 w-9 rounded-full bg-slate-600 after:absolute after:left-[2px] after:top-[2px] after:h-4 after:w-4 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-cyan-500 peer-checked:after:translate-x-4 peer-checked:after:border-white"></div>
              <span className="ml-3 text-sm font-medium">{considerPrevious ? 'Yes' : 'No'}</span>
            </div>
          </div>

          {/* Upload button */}
          <button
            onClick={uploadSelected}
            disabled={selectedFiles.length === 0 || isValidating}
            className="w-full bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-600 hover:to-purple-700 disabled:from-slate-600 disabled:to-slate-600 disabled:cursor-not-allowed text-white font-medium py-3 px-6 rounded-lg transition-all duration-200 flex items-center justify-center gap-2"
          >
            <Upload className="w-4 h-4" />
            Upload {selectedFiles.length} Document{selectedFiles.length !== 1 ? 's' : ''}
            {isValidating && (
              <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full ml-2"></div>
            )}
          </button>
        </div>
      )}
    </div>
  );
};

export default UploadZone;