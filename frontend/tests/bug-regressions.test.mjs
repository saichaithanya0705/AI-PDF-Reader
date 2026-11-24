import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';

const require = createRequire(import.meta.url);

const loadTypeScriptModule = (relativePath) => {
  const fileUrl = new URL(relativePath, import.meta.url);
  assert.equal(existsSync(fileUrl), true, `Missing module: ${relativePath}`);
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

const readSrc = (relativePath) => readFileSync(new URL(relativePath, import.meta.url), 'utf8');

test('buildSplitRanges distributes 3 pages cleanly into 2 or 3 non-overlapping parts and clamps bounds', () => {
  const { buildSplitRanges } = loadTypeScriptModule('../src/lib/splitRanges.ts');

  const twoParts = buildSplitRanges(3, 2, ['Alpha', 'Beta']);
  assert.deepEqual(JSON.parse(JSON.stringify(twoParts)), [
    { name: 'Alpha', startPage: 1, endPage: 2 },
    { name: 'Beta', startPage: 3, endPage: 3 },
  ]);

  const threeParts = buildSplitRanges(3, 3, ['Alpha', 'Beta']);
  assert.deepEqual(JSON.parse(JSON.stringify(threeParts)), [
    { name: 'Alpha', startPage: 1, endPage: 1 },
    { name: 'Beta', startPage: 2, endPage: 2 },
    { name: '', startPage: 3, endPage: 3 },
  ]);

  const clampedParts = buildSplitRanges(3, 8, []);
  assert.equal(clampedParts.length, 3);
  assert.equal(clampedParts[2].endPage, 3);
});

test('extractChatCitations handles empty related_documents, page vs page_number, and deduplication', () => {
  const { extractChatCitations } = loadTypeScriptModule('../src/lib/chatCitations.ts');

  const citations = extractChatCitations(
    {
      related_documents: [],
      sources: [
        { document_id: 'doc-1', document_name: 'Helios.pdf', page: 2, text: 'Loss < 0.03 dB' },
        { document_id: 'doc-1', document_name: 'Helios.pdf', page: 2, text: 'Duplicate page' },
      ],
    },
    {}
  );

  assert.equal(citations.length, 1);
  assert.equal(citations[0].document_id, 'doc-1');
  assert.equal(citations[0].page_number, 2);

  const combined = extractChatCitations(
    {
      related_documents: [
        { document_id: 'doc-2', document_name: 'Cryo.pdf', page_number: 4, text: '4.2 K' },
      ],
      sources: [
        { document_id: 'doc-1', document_name: 'Helios.pdf', page: 3, text: 'Section 3' },
      ],
    },
    {}
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(combined.map((item) => `${item.document_id}:${item.page_number}`))),
    ['doc-1:3', 'doc-2:4']
  );
});

test('frontend defaults to port 8080 and /api/health without blocking Adobe Embed script', () => {
  const configSource = readSrc('../src/config.ts');
  const apiSource = readSrc('../src/lib/api.ts');
  const indexHtmlSource = readSrc('../index.html');
  const cssSource = readSrc('../src/index.css');

  assert.equal(configSource.includes('localhost:8000'), false);
  assert.equal(configSource.includes('http://localhost:8080'), true);
  assert.equal(configSource.includes('ws://localhost:8080'), true);
  assert.equal(apiSource.includes("publicApiRequest('/api/health')"), true);
  assert.equal(indexHtmlSource.includes('documentcloud.adobe.com/view-sdk/main.js'), false);

  const utilitiesIndex = cssSource.indexOf('@layer utilities');
  const componentsIndex = cssSource.indexOf('@layer components');
  const btnSecondaryIndex = cssSource.indexOf('.btn-secondary');
  assert.equal(componentsIndex !== -1, true);
  assert.equal(btnSecondaryIndex > componentsIndex && btnSecondaryIndex < utilitiesIndex, true);
});

test('PodcastModal guards against infinite retries and HomePage drops stale localStorage resurrection', () => {
  const podcastSource = readSrc('../src/components/PodcastModal.tsx');
  const homeSource = readSrc('../src/pages/HomePage.tsx');
  const viewerSource = readSrc('../src/components/SimplePDFViewer.tsx');

  assert.match(podcastSource, /isVisible\s*&&[\s\S]*!audioUrl\s*&&\s*!isGenerating\s*&&\s*!error/);
  assert.equal(podcastSource.includes('role="dialog"'), true);

  assert.equal(homeSource.includes("localStorage.getItem('documents')"), false);
  assert.equal(homeSource.includes('role="dialog"'), true);

  assert.equal(viewerSource.includes('authenticatedPdfData.slice()'), true);
  assert.match(
    viewerSource,
    /useEffect\(\(\)\s*=>\s*\(\)\s*=>\s*\{\s*currentAudio\?\.pause\(\);\s*\},\s*\[currentAudio\]\)/
  );
});

test('ReaderPage integrates Insights and Audio into a golden-ratio split sidebar without floating overlays', () => {
  const { getReaderSidebarLayout } = loadTypeScriptModule('../src/lib/readerSidebarLayout.ts');
  const readerSource = readSrc('../src/pages/ReaderPage.tsx');
  const podcastSource = readSrc('../src/components/PodcastModal.tsx');
  const viewerSource = readSrc('../src/components/SimplePDFViewer.tsx');

  const chatPrimary = getReaderSidebarLayout(true, true, 'chat-primary');
  assert.deepEqual(JSON.parse(JSON.stringify(chatPrimary)), {
    isOpen: true,
    isSplit: true,
    gridTemplateRows: '1fr auto 1.618fr',
    upperSharePercent: 38.2,
    lowerSharePercent: 61.8,
  });

  const studioPrimary = getReaderSidebarLayout(true, true, 'studio-primary');
  assert.deepEqual(JSON.parse(JSON.stringify(studioPrimary)), {
    isOpen: true,
    isSplit: true,
    gridTemplateRows: '1.618fr auto 1fr',
    upperSharePercent: 61.8,
    lowerSharePercent: 38.2,
  });

  assert.deepEqual(JSON.parse(JSON.stringify(getReaderSidebarLayout(true, false, 'chat-primary'))), {
    isOpen: true,
    isSplit: false,
    gridTemplateRows: '1fr',
    upperSharePercent: 100,
    lowerSharePercent: 0,
  });
  assert.deepEqual(JSON.parse(JSON.stringify(getReaderSidebarLayout(false, true, 'studio-primary'))), {
    isOpen: true,
    isSplit: false,
    gridTemplateRows: '1fr',
    upperSharePercent: 0,
    lowerSharePercent: 100,
  });
  assert.deepEqual(JSON.parse(JSON.stringify(getReaderSidebarLayout(false, false, 'chat-primary'))), {
    isOpen: false,
    isSplit: false,
    gridTemplateRows: 'none',
    upperSharePercent: 0,
    lowerSharePercent: 0,
  });

  assert.equal(readerSource.includes('getReaderSidebarLayout'), true);
  assert.equal(readerSource.includes('<InsightsNotification'), false);
  assert.equal(readerSource.includes('fixed bottom-0 right-0'), false);
  assert.equal(readerSource.includes('flex-[1.618]'), true);
  assert.equal(readerSource.includes('variant="docked"'), true);
  assert.equal(readerSource.includes('useMediaQuery'), true);
  assert.equal(readerSource.includes('showChatbot && isDockedChatViewport'), true);
  assert.equal(readerSource.includes('showChatbot && !isDockedChatViewport'), true);

  assert.equal(podcastSource.includes("variant = 'modal'"), true);
  assert.equal(podcastSource.includes('isContentEditable'), true);

  assert.equal(viewerSource.includes('ResizeObserver'), true);
  assert.equal(viewerSource.includes('width={fittedPageWidth}'), true);
});
