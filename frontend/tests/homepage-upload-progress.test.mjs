import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const homePageSource = readFileSync(new URL('../src/pages/HomePage.tsx', import.meta.url), 'utf8');

test('HomePage declares upload progress state before rendering progress indicators', () => {
  assert.match(
    homePageSource,
    /const \[uploadProgress, setUploadProgress\] = useState<UploadProgressState>\(\{\}\);/
  );
  assert.equal(homePageSource.includes('Object.entries(uploadProgress)'), true);
});

test('HomePage consumes the backend upload WebSocket message contract', () => {
  assert.equal(homePageSource.includes('normalizeUploadSocketMessage(message)'), true);
  assert.equal(homePageSource.includes("type !== 'progress'"), true);
  assert.equal(homePageSource.includes("type === 'complete' || type === 'processing_complete'"), true);
  assert.equal(homePageSource.includes("type === 'error' && jobId"), true);
  assert.equal(homePageSource.includes('fetchAllDocuments();'), true);
});
