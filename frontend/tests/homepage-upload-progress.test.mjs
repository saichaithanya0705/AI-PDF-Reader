import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';

const require = createRequire(import.meta.url);
const homePageSource = readFileSync(new URL('../src/pages/HomePage.tsx', import.meta.url), 'utf8');

const loadTypeScriptModule = (relativePath) => {
  const fileUrl = new URL(relativePath, import.meta.url);
  const moduleSource = readFileSync(fileUrl, 'utf8');
  const output = ts.transpileModule(moduleSource, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
  }).outputText;
  const module = { exports: {} };

  vm.runInNewContext(output, {
    module,
    exports: module.exports,
    require,
  }, { filename: fileUrl.pathname });

  return module.exports;
};

const {
  normalizeUploadSocketMessage,
} = loadTypeScriptModule('../src/lib/uploadProgress.ts');

const asPlainObject = (value) => JSON.parse(JSON.stringify(value));

test('HomePage declares upload progress state before rendering progress indicators', () => {
  assert.match(
    homePageSource,
    /const \[uploadProgress, setUploadProgress\] = useState<UploadProgressState>\(\{\}\);/
  );
  assert.equal(homePageSource.includes('Object.entries(uploadProgress)'), true);
});

test('HomePage consumes the backend upload WebSocket message contract', () => {
  assert.equal(homePageSource.includes("from '../lib/uploadProgress'"), true);
  assert.equal(homePageSource.includes('normalizeUploadSocketMessage(message)'), true);
  assert.equal(homePageSource.includes("type === 'complete' || type === 'processing_complete'"), true);
  assert.equal(homePageSource.includes("type === 'error' && jobId"), true);
  assert.equal(homePageSource.includes('fetchAllDocuments();'), true);
});

test('upload progress parser normalizes progress messages', () => {
  assert.deepEqual(
    asPlainObject(normalizeUploadSocketMessage({
      type: 'progress',
      job_id: 'job-1',
      data: {
        percent: '42.4',
        message: 'Indexing pages',
      },
    })),
    {
      type: 'progress',
      jobId: 'job-1',
      progress: {
        percent: 42,
        message: 'Indexing pages',
        status: 'progress',
      },
    }
  );
});

test('upload progress parser accepts both backend completion event names', () => {
  assert.deepEqual(
    asPlainObject(normalizeUploadSocketMessage({
      type: 'processing_complete',
      job_id: 'job-2',
      data: {},
    })),
    {
      type: 'processing_complete',
      jobId: 'job-2',
      progress: {
        percent: 100,
        message: 'Processing complete',
        status: 'complete',
      },
    }
  );
});

test('upload progress parser rejects unknown events and handles errors safely', () => {
  assert.equal(normalizeUploadSocketMessage({ type: 'heartbeat' }), null);
  assert.deepEqual(
    asPlainObject(normalizeUploadSocketMessage({
      type: 'error',
      job_id: 'job-3',
      data: {
        percent: 'not-a-number',
      },
    })),
    {
      type: 'error',
      jobId: 'job-3',
      progress: {
        percent: 0,
        message: 'Processing failed',
        status: 'error',
      },
    }
  );
});
