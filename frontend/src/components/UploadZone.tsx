import React, { useCallback, useState } from 'react';
import { Upload, FileText, X, AlertTriangle, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { PDFValidator, PDFValidationResult } from '../utils/pdfValidator';

interface FileWithValidation extends File {
  validationResult?: PDFValidationResult;
}

interface UploadZoneProps {
  onFileSelect: (files: File | File[], considerPrevious?: boolean) => void;
  multiple?: boolean;
  className?: string;
  compact?: boolean;
}

const UploadZone: React.FC<UploadZoneProps> = ({
  onFileSelect,
  multiple = false,
  className = '',
  compact = false,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileWithValidation[]>([]);
  const [considerPrevious, setConsiderPrevious] = useState(false);
  const [isValidating, setIsValidating] = useState(false);

  const validateFiles = async (files: File[]): Promise<FileWithValidation[]> => {
    setIsValidating(true);
    const validatedFiles: FileWithValidation[] = [];

    for (const file of files) {
      const validationResult = await PDFValidator.validatePDF(file);
      const fileWithValidation = file as FileWithValidation;
      fileWithValidation.validationResult = validationResult;
      validatedFiles.push(fileWithValidation);
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

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);

      const files = Array.from(e.dataTransfer.files).filter(
        (file) => file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
      );

      if (files.length > 0) {
        const validatedFiles = await validateFiles(files);

        if (multiple) {
          setSelectedFiles(validatedFiles);
        } else {
          setSelectedFiles(validatedFiles);
          onFileSelect(validatedFiles[0]);
        }
      }
    },
    [multiple, onFileSelect]
  );

  const handleFileInput = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files ? Array.from(e.target.files) : [];
      e.target.value = '';

      if (files.length > 0) {
        const validatedFiles = await validateFiles(files);

        if (multiple) {
          setSelectedFiles(validatedFiles);
        } else {
          setSelectedFiles(validatedFiles);
          onFileSelect(validatedFiles[0]);
        }
      }
    },
    [multiple, onFileSelect]
  );

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const uploadSelected = () => {
    if (selectedFiles.length > 0) {
      onFileSelect(selectedFiles, considerPrevious);
      setSelectedFiles([]);
    }
  };

  const validCount = selectedFiles.filter((f) => f.validationResult?.isValid !== false).length;
  const warningCount = selectedFiles.filter(
    (f) => f.validationResult && f.validationResult.isValid && f.validationResult.warnings.length > 0
  ).length;
  const errorCount = selectedFiles.filter((f) => f.validationResult?.isValid === false).length;

  return (
    <div className="space-y-phi-4">
      <div
        className={`relative rounded-phi-lg border border-dashed transition-colors duration-phi-fast ${
          compact ? 'px-phi-5 py-phi-4' : 'p-phi-6 text-center'
        } ${
          isDragOver
            ? 'border-accent bg-accent-soft/50'
            : 'border-[rgba(25,24,22,0.2)] bg-paper-50 hover:border-[rgba(25,24,22,0.35)] hover:bg-app-surface'
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
          aria-label={multiple ? 'Choose PDF files to upload' : 'Choose a PDF file to open'}
          className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
        />

        {compact ? (
          <div className="flex flex-wrap items-center justify-between gap-phi-4">
            <div className="flex items-center gap-phi-3">
              <span
                className={`flex h-phi-ctrl w-phi-ctrl shrink-0 items-center justify-center rounded-phi-md border ${
                  isDragOver
                    ? 'border-accent/30 bg-accent-soft text-accent'
                    : 'border-[rgba(25,24,22,0.1)] bg-app-surface text-ink-secondary'
                }`}
              >
                <Upload className="h-4 w-4" strokeWidth={1.5} />
              </span>
              <div>
                <p className="text-phi-sm font-medium text-ink-primary">
                  {isDragOver ? 'Drop PDF to open' : 'Drop a PDF here or browse to open'}
                </p>
                <p className="text-phi-xs text-ink-muted">
                  Validated on upload and opened directly in the reader
                </p>
              </div>
            </div>
            <span className="btn-secondary pointer-events-none h-phi-ctrl-sm px-phi-3 text-phi-xs">
              Select PDF
            </span>
          </div>
        ) : (
          <div className="space-y-phi-3">
            <div className="flex justify-center">
              <span
                className={`flex h-phi-ctrl w-phi-ctrl items-center justify-center rounded-phi-md border ${
                  isDragOver
                    ? 'border-accent/30 bg-accent-soft text-accent'
                    : 'border-[rgba(25,24,22,0.1)] bg-app-surface text-ink-secondary'
                }`}
              >
                <Upload className="h-4 w-4" strokeWidth={1.5} />
              </span>
            </div>

            <div>
              <p className="text-phi-sm font-medium text-ink-primary">
                {isDragOver
                  ? 'Drop PDF files here'
                  : multiple
                    ? 'Drop multiple PDFs or click to browse'
                    : 'Drop a PDF or click to browse'}
              </p>
              <p className="mt-phi-1 text-phi-xs text-ink-muted">
                {multiple
                  ? 'Queue several documents for validation, indexing, and cross-document links'
                  : 'Single files open immediately in the reader'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Selected Files Preview (for bulk upload) */}
      {multiple && selectedFiles.length > 0 && (
        <div className="space-y-phi-4">
          <div className="flex flex-wrap items-center justify-between gap-phi-3 rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-app-surface px-phi-4 py-phi-3">
            <div className="flex items-center gap-phi-3">
              <FileText className="h-4 w-4 text-ink-muted" strokeWidth={1.5} />
              <h3 className="text-phi-sm font-medium text-ink-primary">
                Queued files{' '}
                <span className="font-mono text-phi-xs tabular-nums text-ink-muted">
                  ({selectedFiles.length})
                </span>
              </h3>
            </div>

            <div className="flex items-center gap-phi-4 font-mono text-phi-xs tabular-nums">
              {isValidating ? (
                <span className="inline-flex items-center gap-phi-2 text-ink-secondary">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.5} />
                  Validating
                </span>
              ) : (
                <>
                  <span className="text-semantic-positive">{validCount} valid</span>
                  {warningCount > 0 && (
                    <span className="text-semantic-warning">{warningCount} warnings</span>
                  )}
                  {errorCount > 0 && (
                    <span className="text-semantic-negative">{errorCount} errors</span>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="overflow-hidden rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-app-surface">
            <div className="max-h-72 divide-y divide-[rgba(25,24,22,0.07)] overflow-y-auto scrollbar-thin">
              {selectedFiles.map((file, index) => {
                const validation = file.validationResult;
                const isValid = validation?.isValid ?? true;
                const severity = validation ? PDFValidator.getSeverityLevel(validation) : 'success';
                const summary = validation ? PDFValidator.getValidationSummary(validation) : 'Validating';

                return (
                  <div
                    key={`${file.name}-${index}`}
                    className="group flex items-start gap-phi-3 px-phi-4 py-phi-3 transition-colors duration-phi-fast hover:bg-paper-100/70"
                  >
                    <span className="mt-phi-1 shrink-0">
                      {!validation ? (
                        <Loader2 className="h-4 w-4 animate-spin text-ink-muted" strokeWidth={1.5} />
                      ) : severity === 'error' ? (
                        <AlertCircle className="h-4 w-4 text-semantic-negative" strokeWidth={1.5} />
                      ) : severity === 'warning' ? (
                        <AlertTriangle className="h-4 w-4 text-semantic-warning" strokeWidth={1.5} />
                      ) : (
                        <CheckCircle2 className="h-4 w-4 text-semantic-positive" strokeWidth={1.5} />
                      )}
                    </span>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-phi-2">
                        <p
                          className={`truncate text-phi-sm font-medium ${
                            !isValid ? 'text-semantic-negative' : 'text-ink-primary'
                          }`}
                          title={file.name}
                        >
                          {file.name}
                        </p>
                        <span className="shrink-0 font-mono text-phi-xs tabular-nums text-ink-muted">
                          {(file.size / (1024 * 1024)).toFixed(1)} MB
                        </span>
                      </div>

                      {validation && (
                        <p
                          className={`mt-phi-1 text-phi-xs ${
                            severity === 'error'
                              ? 'text-semantic-negative'
                              : severity === 'warning'
                                ? 'text-semantic-warning'
                                : 'text-ink-muted'
                          }`}
                        >
                          {summary}
                        </p>
                      )}

                      {validation && validation.issues.length > 0 && (
                        <ul className="mt-phi-1 space-y-phi-1 text-phi-xs text-semantic-negative">
                          {validation.issues.slice(0, 2).map((issue, i) => (
                            <li key={i}>• {issue}</li>
                          ))}
                          {validation.issues.length > 2 && (
                            <li className="font-mono text-phi-2xs tabular-nums">
                              +{validation.issues.length - 2} more issues
                            </li>
                          )}
                        </ul>
                      )}

                      {validation && validation.warnings.length > 0 && (
                        <ul className="mt-phi-1 space-y-phi-1 text-phi-xs text-semantic-warning">
                          {validation.warnings.slice(0, 1).map((warning, i) => (
                            <li key={i}>• {warning}</li>
                          ))}
                          {validation.warnings.length > 1 && (
                            <li className="font-mono text-phi-2xs tabular-nums">
                              +{validation.warnings.length - 1} more warnings
                            </li>
                          )}
                        </ul>
                      )}
                    </div>

                    <button
                      type="button"
                      onClick={() => removeFile(index)}
                      className="rounded-phi-sm p-phi-1 text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
                      aria-label={`Remove ${file.name}`}
                    >
                      <X className="h-4 w-4" strokeWidth={1.5} />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          <label className="flex cursor-pointer items-center justify-between gap-phi-4 rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-app-surface px-phi-4 py-phi-3 text-phi-sm text-ink-secondary">
            <span>Include previously opened PDFs when linking recommendations</span>
            <input
              type="checkbox"
              checked={considerPrevious}
              onChange={() => setConsiderPrevious((prev) => !prev)}
              className="h-4 w-4 rounded-phi-xs border-[rgba(25,24,22,0.25)] accent-accent"
            />
          </label>

          <button
            type="button"
            onClick={uploadSelected}
            disabled={selectedFiles.length === 0 || isValidating}
            className="btn-accent h-phi-ctrl w-full"
          >
            {isValidating ? (
              <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
            ) : (
              <Upload className="h-4 w-4" strokeWidth={1.5} />
            )}
            Upload {selectedFiles.length} document{selectedFiles.length !== 1 ? 's' : ''}
          </button>
        </div>
      )}
    </div>
  );
};

export default UploadZone;
