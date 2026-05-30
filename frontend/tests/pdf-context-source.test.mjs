import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const source = readFileSync(new URL('../src/context/PDFContext.tsx', import.meta.url), 'utf8');
const pdfJsSource = readFileSync(new URL('../src/utils/pdfJsInitializer.ts', import.meta.url), 'utf8');
const simpleViewerSource = readFileSync(new URL('../src/components/SimplePDFViewer.tsx', import.meta.url), 'utf8');
const readerPageSource = readFileSync(new URL('../src/pages/ReaderPage.tsx', import.meta.url), 'utf8');
const simpleChatbotSource = readFileSync(new URL('../src/components/SimpleChatbot.tsx', import.meta.url), 'utf8');

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

test('PDFContext validates upload response shape before storing documents', () => {
  assert.equal(source.includes('parseActiveUploadResult'), true);
  assert.equal(source.includes('normalizeBulkUploadResults'), true);
  assert.equal(source.includes('Upload response did not include a valid document id'), true);
});
