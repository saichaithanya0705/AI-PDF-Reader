import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';

const require = createRequire(import.meta.url);
const source = readFileSync(new URL('../src/context/PDFContext.tsx', import.meta.url), 'utf8');
const bulkUploadContractSource = readFileSync(new URL('../src/context/bulkUploadContract.ts', import.meta.url), 'utf8');
const pdfJsSource = readFileSync(new URL('../src/utils/pdfJsInitializer.ts', import.meta.url), 'utf8');
const simpleViewerSource = readFileSync(new URL('../src/components/SimplePDFViewer.tsx', import.meta.url), 'utf8');
const readerPageSource = readFileSync(new URL('../src/pages/ReaderPage.tsx', import.meta.url), 'utf8');
const simpleChatbotSource = readFileSync(new URL('../src/components/SimpleChatbot.tsx', import.meta.url), 'utf8');
const chatHistorySource = readFileSync(new URL('../src/components/ChatHistory.tsx', import.meta.url), 'utf8');
const apiSource = readFileSync(new URL('../src/lib/api.ts', import.meta.url), 'utf8');

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
  getBulkUploadedDocumentSeeds,
  normalizeBulkUploadResponse,
} = loadTypeScriptModule('../src/context/bulkUploadContract.ts');

test('PDFContext does not ship mock related-section fallback content', () => {
  assert.equal(source.includes('Fallback to mock data'), false);
  assert.equal(source.includes('Introduction to Machine Learning'), false);
  assert.equal(source.includes('AI Fundamentals.pdf'), false);
});

test('PDFContext does not fabricate GPT answers when the API fails', () => {
  assert.equal(source.includes('This text discusses ${selectedText.slice'), false);
});

test('PDF.js initializer does not load remote or embedded executable scripts', () => {
  assert.equal(pdfJsSource.includes('https://'), false);
  assert.equal(pdfJsSource.includes('data:application/javascript'), false);
  assert.equal(pdfJsSource.includes("document.createElement('script')"), false);
});

test('SimplePDFViewer uses bundled PDF.js worker instead of a CDN worker', () => {
  assert.equal(simpleViewerSource.includes('cdnjs.cloudflare.com'), false);
  assert.equal(simpleViewerSource.includes('pdf.worker.min.js`'), false);
  assert.equal(simpleViewerSource.includes('pdfWorkerSrc'), true);
  assert.equal(simpleViewerSource.includes('?v=20260612-mjs'), true);
});

test('SimplePDFViewer loads protected PDFs through the authenticated API client', () => {
  assert.equal(simpleViewerSource.includes('fetchAuthenticatedBytes(pdfUrl)'), true);
  assert.equal(simpleViewerSource.includes('file={pdfFile}'), true);
  assert.equal(simpleViewerSource.includes('data: authenticatedPdfData'), true);
  assert.equal(simpleViewerSource.includes('httpHeaders: pdfHeaders'), false);
  assert.equal(simpleViewerSource.includes('getAuthHeaders'), false);
});

test('ReaderPage renders only one chatbot variant per viewport', () => {
  assert.equal(readerPageSource.includes('useMediaQuery'), true);
  assert.equal(readerPageSource.includes('showChatbot && isDockedChatViewport'), true);
  assert.equal(readerPageSource.includes('showChatbot && !isDockedChatViewport'), true);
});

test('SimpleChatbot does not use timeout-based focus band-aids', () => {
  assert.equal(simpleChatbotSource.includes('setTimeout(() => inputRef.current?.focus'), false);
  assert.equal(simpleChatbotSource.includes('inputRef.current?.focus();\n      },'), false);
});

test('chat history flow uses centralized authenticated helpers instead of raw session fetch strings', () => {
  assert.equal(chatHistorySource.includes("apiRequest<Record<string, unknown>>('/api/chat/sessions')"), false);
  assert.equal(chatHistorySource.includes('setSessions(nextSessions)'), false);
  assert.equal(chatHistorySource.includes('listChatSessions()'), true);
  assert.equal(chatHistorySource.includes('deleteChatSession(sessionId)'), true);
  assert.equal(simpleChatbotSource.includes("apiRequest<Record<string, unknown>>(`/api/chat/sessions/${sessionIdToLoad}`)"), false);
  assert.equal(simpleChatbotSource.includes('getChatSession(sessionIdToLoad)'), true);
  assert.equal(simpleChatbotSource.includes('sendChatMessage({'), true);
});

test('chat api validates session payloads centrally and drops stale document_context transport', () => {
  assert.equal(apiSource.includes('parseChatSessionListResponse'), true);
  assert.equal(apiSource.includes('parseChatSessionDetailResponse'), true);
  assert.equal(apiSource.includes('parseSendChatMessageResponse'), true);
  assert.equal(apiSource.includes('document_context:'), false);
  assert.equal(apiSource.includes('inputOrMessage: SendChatMessageInput | string'), false);
});

test('PDFContext validates upload response shape before storing documents', () => {
  assert.equal(source.includes('parseActiveUploadResult'), true);
  assert.equal(source.includes('normalizeBulkUploadResponse'), true);
  assert.equal(source.includes('getBulkUploadedDocumentSeeds(uploadResult, files)'), true);
  assert.equal(source.includes('mergeAndPersistDocuments(newDocuments)'), true);
  assert.equal(source.includes('documents: newDocuments'), true);
  assert.equal(source.includes('Upload response did not include a valid document id'), true);
});

test('PDFContext bulk upload flow does not depend on legacy parallel arrays', () => {
  assert.equal(source.includes('data.job_ids'), false);
  assert.equal(source.includes('data.file_urls'), false);
  assert.equal(bulkUploadContractSource.includes('collection_job_id'), true);
  assert.equal(bulkUploadContractSource.includes('entry.job_id'), true);
  assert.equal(bulkUploadContractSource.includes('entry.file_url'), true);
});

test('bulk upload contract maps backend files into library document seeds', () => {
  const sourceFiles = [
    { name: 'alpha.pdf', size: 100 },
    { name: 'beta.pdf', size: 200 },
  ];
  const result = normalizeBulkUploadResponse({
    detail: 'Accepted 2 new file(s) for multi-PDF ingestion',
    collection_job_id: 'collection-1',
    files: [
      {
        job_id: 'doc-alpha',
        filename: 'alpha.pdf',
        status: 'queued',
        file_url: '/api/files/doc-alpha_alpha.pdf',
        is_duplicate: false,
      },
      {
        job_id: 'doc-beta',
        filename: 'beta.pdf',
        status: 'duplicate',
        file_url: '/api/files/doc-beta_beta.pdf',
        is_duplicate: true,
      },
    ],
  }, sourceFiles);

  assert.equal(result.collectionJobId, 'collection-1');
  assert.deepEqual(result.files.map((file) => file.jobId), ['doc-alpha', 'doc-beta']);
  assert.deepEqual(result.files.map((file) => file.fileUrl), [
    '/api/files/doc-alpha_alpha.pdf',
    '/api/files/doc-beta_beta.pdf',
  ]);
  assert.deepEqual(result.files.map((file) => file.isDuplicate), [false, true]);

  assert.deepEqual(JSON.parse(JSON.stringify(getBulkUploadedDocumentSeeds(result, sourceFiles))), [
    {
      id: 'doc-alpha',
      name: 'alpha.pdf',
      fileUrl: '/api/files/doc-alpha_alpha.pdf',
      sourceFile: sourceFiles[0],
      size: 100,
    },
    {
      id: 'doc-beta',
      name: 'beta.pdf',
      fileUrl: '/api/files/doc-beta_beta.pdf',
      sourceFile: sourceFiles[1],
      size: 200,
    },
  ]);
});

test('bulk upload contract keeps failed files out of library document seeds', () => {
  const sourceFiles = [
    { name: 'alpha.pdf', size: 100 },
    { name: 'broken.pdf', size: 20 },
    { name: 'gamma.pdf', size: 300 },
  ];
  const result = normalizeBulkUploadResponse({
    files: [
      {
        job_id: 'doc-alpha',
        filename: 'alpha.pdf',
        status: 'queued',
        file_url: '/api/files/doc-alpha_alpha.pdf',
      },
      {
        job_id: 'doc-broken',
        filename: 'broken.pdf',
        status: 'FAILED',
        error: 'Invalid PDF file',
      },
      {
        job_id: 'doc-gamma',
        filename: 'gamma.pdf',
        status: 'queued',
        file_url: '/api/files/doc-gamma_gamma.pdf',
      },
    ],
  }, sourceFiles);

  assert.equal(result.files.length, 3);
  assert.equal(result.files[1].error, 'Invalid PDF file');
  assert.equal(result.files[1].status, 'failed');
  assert.deepEqual(getBulkUploadedDocumentSeeds(result, sourceFiles).map((seed) => seed.id), [
    'doc-alpha',
    'doc-gamma',
  ]);
});
