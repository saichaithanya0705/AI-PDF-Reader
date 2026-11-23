import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  FileText,
  FolderOpen,
  Layers,
  Menu,
  MessageSquare,
  Play,
  Volume2,
  X,
} from 'lucide-react';
import BrandMark from '../components/BrandMark';

const capabilities = [
  {
    index: '01',
    name: 'Hybrid document retrieval',
    description:
      'Combines dense semantic embeddings with BM25 keyword matching so technical terms, acronyms, and paraphrases all resolve to the right page.',
    icon: Layers,
  },
  {
    index: '02',
    name: 'Page-grounded chat',
    description:
      'Highlight any sentence in a PDF or ask across your entire library. Every answer links directly to the source document and page number.',
    icon: MessageSquare,
  },
  {
    index: '03',
    name: 'Structured library tools',
    description:
      'Validate PDFs on upload, catch duplicates automatically, merge or split files by page range, and tailor recommendations to your role.',
    icon: FolderOpen,
  },
];

const workflowStages = [
  {
    step: '01',
    title: 'Upload and validate',
    description:
      'Drop a single PDF to open it immediately, or queue a collection for bulk ingestion with structural checks.',
  },
  {
    step: '02',
    title: 'Chunk and index',
    description:
      'Pages are segmented, embedded, and indexed for hybrid vector and keyword search alongside your persona profile.',
  },
  {
    step: '03',
    title: 'Read with cross-references',
    description:
      'As you turn pages, related passages from your other PDFs appear beside the sheet with direct page jumps.',
  },
];

const pipelineFacts = [
  { label: 'Retrieval engine', value: 'Hybrid vector + BM25' },
  { label: 'Cross-PDF isolation', value: 'Open file excluded from side panel' },
  { label: 'Audio briefings', value: 'Page voiceover & podcast overview' },
  { label: 'Verification', value: 'Built-in RAG evaluation harness' },
];

const LandingPage = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-paper-100 text-ink-primary">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-[rgba(25,24,22,0.08)] bg-paper-100/90 backdrop-blur-sm">
        <div className="mx-auto flex h-phi-header w-full max-w-phi-container items-center justify-between px-phi-5 lg:px-phi-6">
          <Link
            to="/"
            className="rounded-phi-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            <BrandMark />
          </Link>

          <nav className="hidden items-center gap-phi-5 text-phi-sm text-ink-secondary md:flex">
            <a
              href="#features"
              className="transition-colors duration-phi-fast hover:text-ink-primary"
            >
              Capabilities
            </a>
            <a
              href="#workflow"
              className="transition-colors duration-phi-fast hover:text-ink-primary"
            >
              Workflow
            </a>
            <a
              href="#insights"
              className="transition-colors duration-phi-fast hover:text-ink-primary"
            >
              Citations
            </a>
          </nav>

          <div className="hidden items-center gap-phi-5 md:flex">
            <Link
              to="/login"
              className="text-phi-sm font-medium text-ink-secondary transition-colors duration-phi-fast hover:text-ink-primary"
            >
              Sign in
            </Link>
            <Link to="/library" className="btn-primary h-phi-ctrl-sm px-phi-4 text-phi-xs">
              Open library
            </Link>
          </div>

          <button
            type="button"
            onClick={() => setMobileMenuOpen((open) => !open)}
            className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-md border border-[rgba(25,24,22,0.12)] text-ink-primary md:hidden"
            aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          >
            {mobileMenuOpen ? (
              <X className="h-4 w-4" strokeWidth={1.5} />
            ) : (
              <Menu className="h-4 w-4" strokeWidth={1.5} />
            )}
          </button>
        </div>

        {mobileMenuOpen && (
          <div className="border-t border-[rgba(25,24,22,0.08)] bg-paper-50 px-phi-5 py-phi-4 md:hidden">
            <div className="flex flex-col gap-phi-3 text-phi-sm">
              <a
                href="#features"
                onClick={() => setMobileMenuOpen(false)}
                className="py-phi-1 text-ink-secondary hover:text-ink-primary"
              >
                Capabilities
              </a>
              <a
                href="#workflow"
                onClick={() => setMobileMenuOpen(false)}
                className="py-phi-1 text-ink-secondary hover:text-ink-primary"
              >
                Workflow
              </a>
              <a
                href="#insights"
                onClick={() => setMobileMenuOpen(false)}
                className="py-phi-1 text-ink-secondary hover:text-ink-primary"
              >
                Citations
              </a>
              <div className="mt-phi-2 flex items-center gap-phi-3 border-t border-[rgba(25,24,22,0.08)] pt-phi-4">
                <Link to="/login" className="btn-secondary h-phi-ctrl flex-1">
                  Sign in
                </Link>
                <Link to="/library" className="btn-primary h-phi-ctrl flex-1">
                  Open library
                </Link>
              </div>
            </div>
          </div>
        )}
      </header>

      {/* Hero with editorial still-life scene and rising Reader preview */}
      <section className="relative overflow-hidden border-b border-[rgba(25,24,22,0.08)]">
        {/* Background scene positioned on the right on desktop/tablet, masked softly into paper-100 */}
        <div
          className="pointer-events-none absolute inset-x-0 top-0 hidden h-[36.932rem] md:block lg:h-[42.36rem]"
          aria-hidden="true"
        >
          <img
            src="/hero-folios.jpg"
            alt=""
            loading="eager"
            width={1600}
            height={900}
            className="h-full w-full object-cover object-right opacity-90"
          />
          <div
            className="absolute inset-0"
            style={{
              background:
                'linear-gradient(90deg, #f6f4ef 0%, #f6f4ef 38.2%, rgba(246,244,239,0.92) 50%, rgba(246,244,239,0.28) 68%, rgba(246,244,239,0) 85%)',
            }}
          />
          <div
            className="absolute inset-x-0 bottom-0 h-phi-9"
            style={{
              background: 'linear-gradient(180deg, rgba(246,244,239,0) 0%, #f6f4ef 92%)',
            }}
          />
        </div>

        <div className="relative mx-auto w-full max-w-phi-container px-phi-5 pt-phi-7 lg:px-phi-6 lg:pt-phi-8">
          <div className="max-w-[36.93rem]">
            <h1 className="animate-rise font-serif text-phi-2xl font-normal leading-phi-display tracking-[-0.025em] text-ink-primary sm:text-[3.29rem] lg:text-phi-3xl">
              Read dense PDFs with every citation in reach
            </h1>
            <p className="animate-rise-delay-1 mt-phi-5 max-w-phi-modal-sm text-phi-md leading-phi text-ink-secondary">
              Index your document library, surface matching passages from other files as you turn pages, and question any excerpt with exact page references.
            </p>

            <div className="animate-rise-delay-2 mt-phi-6 flex flex-wrap items-center gap-phi-3">
              <Link to="/library" className="btn-accent h-phi-ctrl-lg px-phi-5 text-phi-sm">
                Open library
                <ArrowRight className="h-4 w-4" strokeWidth={1.5} />
              </Link>
              <Link to="/signup" className="btn-secondary h-phi-ctrl-lg px-phi-5 text-phi-sm">
                Create workspace
              </Link>
            </div>
          </div>

          {/* Product Preview rising from bottom edge */}
          <div className="animate-rise-delay-3 mt-phi-7 lg:mt-phi-8">
            <div className="overflow-hidden rounded-t-phi-lg border border-b-0 border-[rgba(25,24,22,0.12)] bg-app-surface shadow-sheet">
              {/* Mock app top bar */}
              <div className="flex h-phi-bar items-center justify-between border-b border-[rgba(25,24,22,0.08)] bg-paper-50 px-phi-4">
                <div className="flex min-w-0 items-center gap-phi-3">
                  <div className="flex items-center gap-phi-2" aria-hidden="true">
                    <span className="h-2.5 w-2.5 rounded-full bg-paper-300" />
                    <span className="h-2.5 w-2.5 rounded-full bg-paper-300" />
                    <span className="h-2.5 w-2.5 rounded-full bg-paper-300" />
                  </div>
                  <span className="h-phi-4 w-px bg-[rgba(25,24,22,0.1)]" />
                  <span className="truncate text-phi-sm font-medium text-ink-primary">
                    Q3_Compliance_Review.pdf
                  </span>
                  <span className="hidden font-mono text-phi-xs tabular-nums text-ink-muted sm:inline">
                    p. 18 / 42
                  </span>
                </div>
                <div className="flex items-center gap-phi-2">
                  <span className="hidden items-center gap-phi-2 rounded-phi-sm border border-[rgba(25,24,22,0.1)] bg-app-surface px-phi-3 py-phi-1 text-phi-xs text-ink-secondary sm:inline-flex">
                    <Volume2 className="h-3.5 w-3.5 text-ink-muted" strokeWidth={1.5} />
                    Voiceover
                  </span>
                  <span className="inline-flex items-center gap-phi-2 rounded-phi-sm bg-paper-200 px-phi-3 py-phi-1 text-phi-xs font-medium text-ink-primary">
                    <MessageSquare className="h-3.5 w-3.5 text-accent" strokeWidth={1.5} />
                    Chat
                  </span>
                </div>
              </div>

              {/* Three-column reader preview (14.1rem rail : 1.618fr sheet : 1fr chat) */}
              <div className="grid grid-cols-1 lg:grid-cols-[14.1rem_1.618fr_1fr]">
                {/* Left library + cross-doc rail */}
                <div className="hidden border-r border-[rgba(25,24,22,0.08)] bg-app-bg p-phi-4 lg:block">
                  <p className="text-phi-xs font-medium text-ink-muted">Workspace files</p>
                  <div className="mt-phi-3 space-y-phi-1">
                    <div className="folio-mark rounded-phi-md bg-app-surface py-phi-2 pl-phi-3 pr-phi-3 shadow-subtle ring-1 ring-[rgba(25,24,22,0.08)]">
                      <p className="truncate text-phi-xs font-medium text-ink-primary">
                        Q3_Compliance_Review.pdf
                      </p>
                      <p className="mt-phi-1 font-mono text-phi-2xs tabular-nums text-ink-muted">
                        42 pages · 2.4 MB
                      </p>
                    </div>
                    <div className="rounded-phi-md px-phi-3 py-phi-2 text-ink-secondary">
                      <p className="truncate text-phi-xs font-medium">Board_Audit_2025.pdf</p>
                      <p className="mt-phi-1 font-mono text-phi-2xs tabular-nums text-ink-muted">
                        28 pages · 1.8 MB
                      </p>
                    </div>
                    <div className="rounded-phi-md px-phi-3 py-phi-2 text-ink-secondary">
                      <p className="truncate text-phi-xs font-medium">Supplier_Policy_v4.pdf</p>
                      <p className="mt-phi-1 font-mono text-phi-2xs tabular-nums text-ink-muted">
                        19 pages · 940 KB
                      </p>
                    </div>
                  </div>

                  <div className="mt-phi-5 border-t border-[rgba(25,24,22,0.08)] pt-phi-4">
                    <p className="text-phi-xs font-medium text-ink-muted">Related passages</p>
                    <div className="mt-phi-3 rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-app-surface p-phi-3">
                      <div className="flex items-center justify-between gap-phi-2">
                        <span className="truncate text-phi-xs font-medium text-ink-primary">
                          Board_Audit_2025.pdf
                        </span>
                        <span className="shrink-0 font-mono text-phi-2xs tabular-nums text-accent-ink">
                          p. 11
                        </span>
                      </div>
                      <p className="mt-phi-2 line-clamp-3 text-phi-2xs leading-phi text-ink-secondary">
                        Dual sign-off between treasury and legal shortened review handoffs from 14 business days to 9.5.
                      </p>
                      <p className="mt-phi-2 font-mono text-phi-2xs tabular-nums text-ink-muted">
                        score 0.89
                      </p>
                    </div>
                  </div>
                </div>

                {/* Center PDF page canvas */}
                <div className="bg-app-canvas p-phi-5 sm:p-phi-6">
                  <div className="mx-auto max-w-phi-modal-sm rounded-phi-sm border border-[rgba(25,24,22,0.1)] bg-white p-phi-5 shadow-card sm:p-phi-6">
                    <div className="flex items-center justify-between border-b border-[rgba(25,24,22,0.08)] pb-phi-3 font-mono text-phi-2xs text-ink-muted">
                      <span>Section 4.2 · Internal Controls</span>
                      <span className="tabular-nums">18</span>
                    </div>
                    <h2 className="mt-phi-5 font-serif text-phi-md font-medium text-ink-primary">
                      Dual-control sign-off schedule
                    </h2>
                    <p className="mt-phi-3 text-phi-xs leading-phi text-ink-secondary">
                      All quarterly vendor contracts exceeding the threshold defined in Annex B require concurrent review by finance and legal before execution.
                    </p>
                    <div className="folio-mark mt-phi-4 rounded-r-phi-sm bg-accent-soft/75 py-phi-3 pl-phi-4 pr-phi-3">
                      <p className="text-phi-xs leading-phi text-ink-primary">
                        Consolidating pre-approval checklists into a single audit packet reduces total cycle time by 32% while preserving full signatory traceability across departments.
                      </p>
                    </div>
                    <p className="mt-phi-4 text-phi-xs leading-phi text-ink-secondary">
                      Exception logs are archived with the quarterly filing and cross-referenced against the annual board audit register.
                    </p>
                  </div>
                </div>

                {/* Right grounded chat rail */}
                <div className="border-t border-[rgba(25,24,22,0.08)] bg-app-surface p-phi-4 lg:border-l lg:border-t-0">
                  <div className="flex items-center justify-between border-b border-[rgba(25,24,22,0.08)] pb-phi-3">
                    <span className="text-phi-xs font-medium text-ink-primary">Document chat</span>
                    <span className="font-mono text-phi-2xs tabular-nums text-ink-muted">
                      p. 18 context
                    </span>
                  </div>

                  <div className="mt-phi-4 space-y-phi-3">
                    <div className="ml-phi-5 rounded-phi-md bg-paper-200 px-phi-3 py-phi-2 text-phi-xs leading-phi text-ink-primary">
                      How does section 4.2 change the audit cycle compared to last year?
                    </div>

                    <div className="rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-paper-50 p-phi-3 text-phi-xs leading-phi text-ink-secondary">
                      <p className="text-ink-primary">
                        Section 4.2 replaces sequential finance and legal sign-off with concurrent review, cutting total audit cycle time by 32%.
                      </p>
                      <div className="mt-phi-3 flex flex-wrap items-center gap-phi-2 border-t border-[rgba(25,24,22,0.08)] pt-phi-2 font-mono text-phi-2xs tabular-nums">
                        <span className="text-accent-ink">Q3_Compliance · p. 18</span>
                        <span className="text-ink-faint">/</span>
                        <span className="text-ink-muted">Board_Audit · p. 11</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <main className="mx-auto w-full max-w-phi-container px-phi-5 lg:px-phi-6">
        {/* Capabilities */}
        <section id="features" className="py-phi-7 lg:py-phi-8">
          <div className="max-w-[36.93rem]">
            <p className="font-mono text-phi-xs text-ink-muted">Capabilities</p>
            <h2 className="mt-phi-3 font-serif text-phi-xl font-normal leading-phi-tight tracking-[-0.02em] text-ink-primary sm:text-phi-2xl">
              Built for reading across dozens of files at once
            </h2>
          </div>

          <div className="mt-phi-6 grid gap-phi-5 border-t border-[rgba(25,24,22,0.1)] pt-phi-6 md:grid-cols-3 md:gap-phi-6">
            {capabilities.map((feature) => (
              <article key={feature.name} className="flex flex-col">
                <div className="flex items-center justify-between">
                  <feature.icon className="h-4 w-4 text-ink-secondary" strokeWidth={1.5} />
                  <span className="font-mono text-phi-xs tabular-nums text-ink-muted">
                    {feature.index}
                  </span>
                </div>
                <h3 className="mt-phi-5 text-phi-md font-medium text-ink-primary">
                  {feature.name}
                </h3>
                <p className="mt-phi-3 text-phi-sm leading-phi text-ink-secondary">
                  {feature.description}
                </p>
              </article>
            ))}
          </div>
        </section>

        {/* Workflow (61.8% / 38.2% golden split) */}
        <section id="workflow" className="border-t border-[rgba(25,24,22,0.1)] py-phi-7 lg:py-phi-8">
          <div className="grid items-start gap-phi-6 lg:grid-cols-phi lg:gap-phi-7">
            <div>
              <p className="font-mono text-phi-xs text-ink-muted">Workflow</p>
              <h2 className="mt-phi-3 font-serif text-phi-xl font-normal leading-phi-tight tracking-[-0.02em] text-ink-primary sm:text-phi-2xl">
                From upload to cited reading in three steps
              </h2>
              <p className="mt-phi-4 max-w-phi-modal-lg text-phi-sm leading-phi text-ink-secondary">
                Drop in policy manuals, research papers, or technical specifications. The studio validates each PDF, builds a searchable index, and links related sections across your library.
              </p>

              <div className="mt-phi-6 divide-y divide-[rgba(25,24,22,0.09)] border-y border-[rgba(25,24,22,0.09)]">
                {workflowStages.map((stage) => (
                  <div key={stage.title} className="grid grid-cols-[2.618rem_1fr] gap-phi-4 py-phi-4">
                    <span className="pt-phi-1 font-mono text-phi-xs tabular-nums text-accent-ink">
                      {stage.step}
                    </span>
                    <div>
                      <h3 className="text-phi-base font-medium text-ink-primary">{stage.title}</h3>
                      <p className="mt-phi-1 text-phi-sm leading-phi text-ink-secondary">
                        {stage.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-phi-lg border border-[rgba(25,24,22,0.1)] bg-paper-50 p-phi-5 shadow-card sm:p-phi-6">
              <div className="flex items-center gap-phi-3 text-phi-sm font-medium text-ink-primary">
                <FileText className="h-4 w-4 text-ink-muted" strokeWidth={1.5} />
                Document pipeline
              </div>
              <p className="mt-phi-2 text-phi-sm leading-phi text-ink-secondary">
                Every file follows the same validation, indexing, and evaluation path so search quality stays measurable.
              </p>

              <dl className="mt-phi-5 divide-y divide-[rgba(25,24,22,0.08)] border-t border-[rgba(25,24,22,0.08)]">
                {pipelineFacts.map((fact) => (
                  <div
                    key={fact.label}
                    className="flex flex-col gap-phi-1 py-phi-3 sm:flex-row sm:items-baseline sm:justify-between sm:gap-phi-4"
                  >
                    <dt className="text-phi-xs text-ink-muted">{fact.label}</dt>
                    <dd className="text-phi-sm font-medium text-ink-primary sm:text-right">
                      {fact.value}
                    </dd>
                  </div>
                ))}
              </dl>

              <div className="mt-phi-5 pt-phi-2">
                <Link to="/library" className="btn-secondary h-phi-ctrl w-full justify-between px-phi-4">
                  <span>Open document library</span>
                  <ArrowRight className="h-4 w-4 text-ink-muted" strokeWidth={1.5} />
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Citations & Audio (38.2% / 61.8% alternating golden split) */}
        <section id="insights" className="border-t border-[rgba(25,24,22,0.1)] py-phi-7 lg:py-phi-8">
          <div className="grid items-center gap-phi-6 lg:grid-cols-phi-rev lg:gap-phi-7">
            <div>
              <p className="font-mono text-phi-xs text-ink-muted">Citations and audio</p>
              <h2 className="mt-phi-3 font-serif text-phi-xl font-normal leading-phi-tight tracking-[-0.02em] text-ink-primary sm:text-phi-2xl">
                Answers tied to the exact page, ready to read or listen
              </h2>
              <p className="mt-phi-4 text-phi-sm leading-phi text-ink-secondary">
                Inspect page-level insights alongside the open PDF, verify every source passage in the side panel, or generate a tailored audio overview for the section you are reviewing.
              </p>
              <div className="mt-phi-6 flex flex-wrap items-center gap-phi-3">
                <Link to="/library" className="btn-primary h-phi-ctrl px-phi-4">
                  Start reading
                  <ArrowRight className="h-4 w-4" strokeWidth={1.5} />
                </Link>
                <Link to="/login" className="btn-ghost h-phi-ctrl">
                  Sign in to workspace
                </Link>
              </div>
            </div>

            <div className="space-y-phi-4">
              <div className="rounded-phi-lg border border-[rgba(25,24,22,0.1)] bg-paper-50 p-phi-5 shadow-card">
                <div className="flex items-center justify-between text-phi-xs text-ink-muted">
                  <span>Contextual summary</span>
                  <span className="font-mono tabular-nums text-accent-ink">pp. 18–21</span>
                </div>
                <blockquote className="folio-mark mt-phi-4 pl-phi-4 text-phi-base leading-phi text-ink-primary">
                  “Key regulatory changes introduced in section 4.2 reduce the compliance audit cycle by 32% while mandating dual approval workflows across finance and legal.”
                </blockquote>
                <div className="mt-phi-4 flex items-center justify-between border-t border-[rgba(25,24,22,0.08)] pt-phi-3 text-phi-xs text-ink-muted">
                  <span>Q3_Compliance_Review.pdf</span>
                  <span className="font-mono tabular-nums">Hybrid retrieval</span>
                </div>
              </div>

              <div className="rounded-phi-lg border border-[rgba(25,24,22,0.1)] bg-paper-50 p-phi-4 shadow-subtle">
                <div className="flex items-center gap-phi-4">
                  <span className="flex h-phi-ctrl w-phi-ctrl shrink-0 items-center justify-center rounded-phi-md bg-ink-primary text-paper-50">
                    <Play className="ml-0.5 h-4 w-4" strokeWidth={1.5} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-phi-2">
                      <p className="truncate text-phi-sm font-medium text-ink-primary">
                        Page 18 audio briefing
                      </p>
                      <span className="font-mono text-phi-xs tabular-nums text-ink-muted">02:14</span>
                    </div>
                    <div className="mt-phi-2 h-1.5 w-full overflow-hidden rounded-full bg-paper-200">
                      <div className="h-full w-[38.2%] rounded-full bg-accent" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-[rgba(25,24,22,0.09)] bg-paper-100">
        <div className="mx-auto flex w-full max-w-phi-container flex-col gap-phi-4 px-phi-5 py-phi-5 sm:flex-row sm:items-center sm:justify-between lg:px-phi-6">
          <div className="flex items-center gap-phi-3">
            <BrandMark compact />
            <span className="text-phi-sm text-ink-secondary">Document Intelligence Studio</span>
          </div>
          <div className="flex flex-wrap items-center gap-phi-5 text-phi-sm text-ink-muted">
            <Link to="/library" className="transition-colors duration-phi-fast hover:text-ink-primary">
              Library
            </Link>
            <Link to="/evals" className="transition-colors duration-phi-fast hover:text-ink-primary">
              RAG evals
            </Link>
            <Link to="/login" className="transition-colors duration-phi-fast hover:text-ink-primary">
              Sign in
            </Link>
            <Link to="/signup" className="transition-colors duration-phi-fast hover:text-ink-primary">
              Create workspace
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
