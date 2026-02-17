import { Link } from 'react-router-dom';
import {
  ArrowRight,
  ChevronDown,
  CloudLightning,
  FileText,
  Layers,
  LineChart,
  Mic,
  Sparkles,
  Wand2,
} from 'lucide-react';

const featureHighlights = [
  {
    name: 'Vector-Powered Intelligence',
    description: 'Retrieve precise insights from any page with our hybrid RAG engine tuned for document comprehension.',
    icon: Layers,
  },
  {
    name: 'AI Co-Pilot Chat',
    description: 'Ask complex questions and receive contextual answers with cited references in milliseconds.',
    icon: Sparkles,
  },
  {
    name: 'Collaboration at Scale',
    description: 'Bulk upload, clean duplicates, and orchestrate document workflows for teams of any size.',
    icon: CloudLightning,
  },
];

const workflow = [
  {
    title: 'Upload',
    description: 'Drag-and-drop or connect cloud drives. Automatic validation keeps your library pristine.',
  },
  {
    title: 'Enrich',
    description: 'Chunking, embeddings, and metadata enrichment happen instantly — no scripts required.',
  },
  {
    title: 'Engage',
    description: 'Dive into the adaptive reader, highlight insights, and open contextual chat without losing focus.',
  },
];

const stats = [
  { label: 'Documents processed', value: '12K+' },
  { label: 'Embeddings generated', value: '4.8M' },
  { label: 'Avg. response time', value: '320ms' },
];

const LandingPage = () => {
  return (
    <div className="relative isolate overflow-hidden">
      <div className="absolute inset-x-0 top-0 -z-10 overflow-hidden">
        <div className="mx-auto max-w-5xl px-6">
          <div className="relative mt-24 h-72 rounded-full bg-gradient-to-r from-fuchsia-500/20 via-brand-500/25 to-cyan-400/20 blur-3xl" />
        </div>
      </div>

      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 pt-8 md:px-10">
        <Link to="/" className="flex items-center gap-3 text-white">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500/80 shadow-glow-sm">
            <Wand2 className="h-5 w-5" />
          </div>
          <div>
            <p className="font-display text-lg leading-none">Document Intelligence Studio</p>
            <p className="mt-0.5 text-xs uppercase tracking-[0.3em] text-slate-400">Adobe Hackathon 2025</p>
          </div>
        </Link>

        <nav className="hidden items-center gap-8 text-sm text-slate-200 md:flex">
          <a className="transition hover:text-white" href="#features">
            Features
          </a>
          <a className="transition hover:text-white" href="#workflow">
            Workflow
          </a>
          <a className="transition hover:text-white" href="#insights">
            Insights
          </a>
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <Link
            to="/login"
            className="rounded-full border border-white/10 px-4 py-2 text-sm text-slate-200 transition hover:border-white/30 hover:text-white"
          >
            Login
          </Link>
        </div>

        <div className="flex items-center gap-2 md:hidden">
          <Link
            to="/login"
            className="rounded-full border border-white/10 px-4 py-2 text-sm text-slate-200 transition hover:border-white/30 hover:text-white"
          >
            Login
          </Link>
          <Link
            to="/signup"
            className="rounded-full bg-brand-500 px-4 py-2 text-sm font-semibold text-white shadow-glow transition hover:bg-brand-400"
          >
            Join free
          </Link>
          <Link
            to="/library"
            className="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-sm font-medium text-white backdrop-blur-xs transition hover:bg-white/20"
          >
            Launch
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-col gap-24 px-6 pb-32 pt-20 md:px-10 md:pt-28">
        <section className="flex flex-col items-center text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1 text-sm text-slate-200">
            <Mic className="h-4 w-4 text-cyan-300" />
            AI-powered reading companion for every document
          </span>
          <h1 className="mt-6 max-w-4xl text-balance text-4xl md:text-6xl">
            Reimagine enterprise PDFs with a real-time, context-aware intelligence layer.
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-slate-300 md:text-xl">
            Upload, explore, and converse with complex documents in seconds. Built with a production-ready Retrieval-Augmented Generation engine, multimodal insights, and advanced automation tools.
          </p>
          <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row">
            <Link
              to="/library"
              className="flex items-center gap-2 rounded-full bg-brand-500 px-6 py-3 text-base font-semibold text-white shadow-glow transition hover:-translate-y-1 hover:bg-brand-400"
            >
              Launch Reader
              <ArrowRight className="h-5 w-5" />
            </Link>
            <Link
              to="/signup"
              className="flex items-center gap-2 rounded-full border border-white/10 px-6 py-3 text-base font-medium text-slate-200 transition hover:border-white/30 hover:text-white"
            >
              Create team workspace
            </Link>
          </div>
          <button
            type="button"
            className="mt-12 flex items-center gap-2 text-sm text-slate-400 transition hover:text-slate-200"
            onClick={() => {
              const element = document.getElementById('features');
              element?.scrollIntoView({ behavior: 'smooth' });
            }}
          >
            Discover the platform
            <ChevronDown className="h-4 w-4" />
          </button>
        </section>

        <section
          id="features"
          className="grid gap-6 rounded-3xl border border-white/10 bg-white/5 p-8 backdrop-blur md:grid-cols-3"
        >
          {featureHighlights.map((feature) => (
            <article
              key={feature.name}
              className="group flex flex-col gap-4 rounded-2xl border border-transparent bg-slate-950/40 p-6 transition hover:border-brand-500/40 hover:bg-slate-900/50"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-500/20 text-brand-200 transition group-hover:bg-brand-500/30">
                <feature.icon className="h-6 w-6" />
              </div>
              <h3 className="text-xl font-semibold text-white">{feature.name}</h3>
              <p className="text-sm leading-relaxed text-slate-300">{feature.description}</p>
              <div className="mt-auto text-sm font-medium text-cyan-300 opacity-0 transition group-hover:opacity-100">
                Optimised for scale →
              </div>
            </article>
          ))}
        </section>

        <section
          id="workflow"
          className="grid gap-10 rounded-3xl border border-white/5 bg-slate-950/60 p-8 md:grid-cols-[1.2fr_1fr]"
        >
          <div className="flex flex-col gap-6">
            <p className="text-sm uppercase tracking-[0.4em] text-cyan-200/70">workflow</p>
            <h2 className="text-3xl md:text-4xl">From import to insight in under three steps.</h2>
            <p className="text-base text-slate-300">
              Our adaptive pipeline is tuned for enterprise PDFs, policy manuals, research archives, and creative briefs. Every document is enriched, deduplicated, and ready for conversational exploration instantly.
            </p>
            <div className="grid gap-6 md:grid-cols-3">
              {workflow.map((stage, index) => (
                <div key={stage.title} className="relative flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-5">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-500/30 text-lg font-semibold text-white">
                    {index + 1}
                  </span>
                  <h3 className="text-lg font-semibold text-white">{stage.title}</h3>
                  <p className="text-sm leading-relaxed text-slate-300">{stage.description}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-6 rounded-3xl border border-brand-500/20 bg-gradient-to-br from-brand-500/20 via-fuchsia-500/10 to-cyan-400/20 p-6 shadow-glow">
            <div className="flex items-center gap-3 text-sm text-white">
              <FileText className="h-5 w-5" />
              Real-time document telemetry
            </div>
            <ul className="flex flex-col gap-4 text-sm text-white/80">
              <li className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-cyan-300" />
                Processed with PDF structural integrity checks and layout heuristics.
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-aurora" />
                Smart persona tagging and job profiling for personalised recommendations.
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-brand-300" />
                Automatic RAG ingestion pushes clean embeddings to FAISS instantly.
              </li>
            </ul>
            <Link
              to="/library"
              className="mt-auto inline-flex items-center gap-2 rounded-full border border-white/30 px-4 py-2 text-sm font-medium text-white transition hover:border-white hover:bg-white/10"
            >
              Explore the intelligent library
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </section>

        <section
          id="insights"
          className="grid gap-12 rounded-3xl border border-white/10 bg-white/5 p-8 md:grid-cols-[1.1fr_1fr]"
        >
          <div className="flex flex-col gap-6">
            <p className="text-sm uppercase tracking-[0.4em] text-aurora/80">insights</p>
            <h2 className="text-3xl md:text-4xl">Grounded, auditable answers for mission-critical teams.</h2>
            <p className="text-base text-slate-300">
              Every response is grounded in verifiable segments of your document. Toggle contextual highlights, generate audio briefings, and export structured notes with a single tap.
            </p>
            <div className="grid gap-4">
              {stats.map((stat) => (
                <div key={stat.label} className="flex items-center justify-between rounded-2xl border border-white/5 bg-slate-950/40 px-5 py-4">
                  <p className="text-sm uppercase tracking-[0.3em] text-slate-400">{stat.label}</p>
                  <p className="text-2xl font-semibold text-white">{stat.value}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/70 p-6">
            <div className="absolute inset-x-0 -top-32 h-64 rounded-full bg-gradient-to-br from-brand-500/40 via-cyan-400/30 to-fuchsia-500/40 blur-3xl" />
            <div className="relative flex flex-col gap-4">
              <div className="flex items-center gap-3 text-sm text-slate-200">
                <LineChart className="h-4 w-4" />
                Insight layers preview
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                <p className="text-xs uppercase tracking-[0.3em] text-cyan-200">Contextual summary</p>
                <p className="mt-2 text-base text-white">
                  “Key regulatory changes introduced in section 4.2 reduce the compliance audit cycle by 32% while mandating dual approval workflows across finance and legal.”
                </p>
                <div className="mt-4 flex items-center gap-3 text-xs text-slate-400">
                  <div className="h-2 w-2 rounded-full bg-cyan-300" />
                  Auto-sourced from pages 18-21
                </div>
              </div>
              <div className="rounded-2xl border border-brand-500/40 bg-brand-500/15 p-4 text-sm text-slate-200 shadow-glow">
                <p className="text-xs uppercase tracking-[0.3em] text-white/70">Voiceover Ready</p>
                <p className="mt-2 text-base text-white">
                  Spin up instant voice briefings tailored for executives, analysts, or design leads to share across teams.
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 pb-10 md:px-10 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3 text-sm text-slate-400">
          <Wand2 className="h-5 w-5" />
          Built for Adobe Hackathon Finale · 2025
        </div>
        <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
          <Link to="/library" className="transition hover:text-slate-200">
            Library
          </Link>
          <Link to="/login" className="transition hover:text-slate-200">
            Login
          </Link>
          <Link to="/signup" className="transition hover:text-slate-200">
            Sign up
          </Link>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
