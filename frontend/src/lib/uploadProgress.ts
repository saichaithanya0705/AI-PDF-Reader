export type UploadProgressStatus = 'progress' | 'complete' | 'error';

export type UploadProgressEntry = {
  percent: number;
  message: string;
  status: UploadProgressStatus;
};

export type UploadProgressState = Record<string, UploadProgressEntry>;

type UploadSocketMessageType = 'progress' | 'complete' | 'processing_complete' | 'error';

export type UploadSocketMessage = {
  type: UploadSocketMessageType;
  jobId?: string;
  progress: UploadProgressEntry;
};

const isRecord = (value: unknown): value is Record<string, unknown> => (
  typeof value === 'object' && value !== null
);

const clampProgressPercent = (value: unknown, fallback: number): number => {
  const parsed = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(100, Math.max(0, Math.round(parsed)));
};

const getFallbackPercent = (type: UploadSocketMessageType): number => (
  type === 'complete' || type === 'processing_complete' ? 100 : 0
);

const getUploadProgressMessage = (type: UploadSocketMessageType, data: Record<string, unknown>): string => {
  const message = data.message;
  if (typeof message === 'string' && message.trim()) {
    return message;
  }

  if (type === 'error') return 'Processing failed';
  if (type === 'complete' || type === 'processing_complete') return 'Processing complete';
  return 'Processing...';
};

export const normalizeUploadSocketMessage = (message: unknown): UploadSocketMessage | null => {
  if (!isRecord(message)) return null;
  const type = message.type;
  if (type !== 'progress' && type !== 'complete' && type !== 'processing_complete' && type !== 'error') {
    return null;
  }

  const data = isRecord(message.data) ? message.data : {};
  const jobId = typeof message.job_id === 'string' && message.job_id.trim()
    ? message.job_id
    : undefined;
  const status: UploadProgressStatus = type === 'error'
    ? 'error'
    : type === 'progress'
      ? 'progress'
      : 'complete';

  return {
    type,
    jobId,
    progress: {
      percent: clampProgressPercent(data.percent, getFallbackPercent(type)),
      message: getUploadProgressMessage(type, data),
      status,
    },
  };
};
