type UnknownRecord = Record<string, unknown>;

export interface BulkUploadSourceFile {
  name: string;
  size: number;
}

export interface BulkUploadFileResult {
  jobId?: string;
  filename: string;
  fileUrl?: string;
  status: string;
  isDuplicate: boolean;
  error?: string;
}

export interface BulkUploadResult {
  detail?: string;
  collectionJobId?: string;
  files: BulkUploadFileResult[];
}

export interface BulkUploadedDocumentSeed {
  id: string;
  name: string;
  fileUrl?: string;
  sourceFile?: BulkUploadSourceFile;
  size: number;
}

const isRecord = (value: unknown): value is UnknownRecord => (
  typeof value === 'object' && value !== null
);

const asString = (value: unknown): string | undefined => (
  typeof value === 'string' && value.trim().length > 0 ? value : undefined
);

const asBoolean = (value: unknown, fallback = false): boolean => (
  typeof value === 'boolean' ? value : fallback
);

const normalizeStatus = (value: unknown, fallback: string): string => (
  asString(value)?.toLowerCase() || fallback
);

const isFailedUploadResult = (result: BulkUploadFileResult): boolean => (
  result.status === 'failed' || result.status === 'error' || Boolean(result.error)
);

export const normalizeBulkUploadResponse = (
  data: unknown,
  sourceFiles: BulkUploadSourceFile[],
): BulkUploadResult => {
  if (!isRecord(data)) {
    throw new Error('Bulk upload response was not a valid object');
  }

  if (!Array.isArray(data.files)) {
    throw new Error('Bulk upload response did not include uploaded file records');
  }

  return {
    detail: asString(data.detail),
    collectionJobId: asString(data.collection_job_id),
    files: data.files.map((entry, index) => {
      const sourceFile = sourceFiles[index];

      if (!isRecord(entry)) {
        return {
          filename: sourceFile?.name || 'Document',
          status: 'failed',
          isDuplicate: false,
          error: 'Upload response included an invalid file record',
        };
      }

      const error = asString(entry.error);

      return {
        jobId: asString(entry.job_id),
        filename: asString(entry.filename) || sourceFile?.name || 'Document',
        fileUrl: asString(entry.file_url),
        status: normalizeStatus(entry.status, error ? 'failed' : 'queued'),
        isDuplicate: asBoolean(entry.is_duplicate),
        error,
      };
    }),
  };
};

export const getBulkUploadedDocumentSeeds = (
  uploadResult: BulkUploadResult,
  sourceFiles: BulkUploadSourceFile[],
): BulkUploadedDocumentSeed[] => (
  uploadResult.files
    .map((result, index): BulkUploadedDocumentSeed | null => {
      if (!result.jobId || isFailedUploadResult(result)) return null;

      const sourceFile = sourceFiles[index];
      const seed: BulkUploadedDocumentSeed = {
        id: result.jobId,
        name: result.filename || sourceFile?.name || 'Document',
        size: sourceFile?.size || 0,
      };

      if (result.fileUrl) seed.fileUrl = result.fileUrl;
      if (sourceFile) seed.sourceFile = sourceFile;

      return seed;
    })
    .filter((seed): seed is BulkUploadedDocumentSeed => Boolean(seed))
);
