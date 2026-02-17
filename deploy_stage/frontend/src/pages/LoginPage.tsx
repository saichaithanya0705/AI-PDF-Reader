import { FormEvent, useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, Loader2, Lock, Mail, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { signIn, resetError, error } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Get the page user was trying to access before being redirected to login
  const from = (location.state as any)?.from?.pathname || '/library';
  const successMessage = (location.state as any)?.message;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    resetError();

    if (!email || !password) {
      setFormError('Enter both email and password to continue.');
      return;
    }

    try {
      setIsSubmitting(true);
      await signIn({ email, password });
      // Redirect to the page they were trying to access, or library by default
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof Error) {
        setFormError(err.message);
      } else {
        setFormError('Unable to sign in. Try again shortly.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center px-6 py-16">
      <div className="absolute inset-0 -z-10 opacity-60">
        <div className="mx-auto h-full w-full max-w-4xl rounded-full bg-gradient-to-r from-brand-500/20 via-cyan-500/20 to-fuchsia-500/20 blur-3xl" />
      </div>

      <div className="w-full max-w-4xl rounded-3xl border border-white/10 bg-slate-950/80 p-8 shadow-glow backdrop-blur">
        <div className="flex flex-col gap-6 md:flex-row md:items-stretch md:gap-12">
          <div className="flex flex-1 flex-col justify-between gap-6 rounded-2xl border border-white/5 bg-white/5 p-6">
            <button
              type="button"
              onClick={() => navigate('/')}
              className="flex items-center gap-2 text-sm text-slate-300 transition hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
            <div className="flex flex-col gap-4">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.3em] text-slate-300">
                <ShieldCheck className="h-3.5 w-3.5" />
                Secure Workspace Access
              </span>
              <h1 className="text-3xl sm:text-4xl">Welcome back to the Document Intelligence Studio.</h1>
              <p className="text-sm leading-relaxed text-slate-300">
                Pick up where you left off. Your personalised libraries, AI highlights, and collaborative insights are waiting for you.
              </p>
            </div>
            <div className="space-y-3 text-xs text-slate-400">
              <p>• RAG-powered conversations grounded in your private data</p>
              <p>• Enterprise-grade encryption with automatic session rotation</p>
              <p>• Seamless handoff to Reader with preloaded personas and jobs</p>
            </div>
          </div>

          <form className="flex flex-1 flex-col gap-6" onSubmit={handleSubmit}>
            <div>
              <label className="text-sm font-medium text-white" htmlFor="email">
                Email address
              </label>
              <div className="mt-2 flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-slate-200 focus-within:border-brand-400 focus-within:bg-slate-900">
                <Mail className="h-4 w-4 text-slate-400" />
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none"
                  placeholder="you@company.com"
                  autoComplete="email"
                  required
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-white" htmlFor="password">
                  Password
                </label>
                <Link to="#" className="text-xs text-cyan-300 transition hover:text-cyan-200">
                  Forgot password?
                </Link>
              </div>
              <div className="mt-2 flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-slate-200 focus-within:border-brand-400 focus-within:bg-slate-900">
                <Lock className="h-4 w-4 text-slate-400" />
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                />
              </div>
            </div>

            {successMessage && (
              <div className="rounded-2xl border border-cyan-400/40 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-300">
                {successMessage}
              </div>
            )}

            {(formError || error) && (
              <div className="rounded-2xl border border-aurora/40 bg-aurora/10 px-4 py-3 text-sm text-aurora">
                {formError || error?.message}
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center justify-center gap-2 rounded-full bg-brand-500 px-6 py-3 text-sm font-semibold text-white shadow-glow transition hover:bg-brand-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Signing in
                </>
              ) : (
                'Sign in'
              )}
            </button>

            <p className="text-sm text-slate-300">
              New to the studio?{' '}
              <Link to="/signup" className="font-medium text-cyan-300 transition hover:text-cyan-200">
                Create an account
              </Link>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
