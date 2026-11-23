import { FormEvent, useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, Loader2, Mail } from 'lucide-react';
import { useAuth } from '../context/useAuth';
import { toAuthErrorMessage } from '../lib/authErrors';
import { FORGOT_PASSWORD_PATH } from '../lib/authRoutes';
import PasswordInput from '../components/PasswordInput';
import BrandMark from '../components/BrandMark';

type LoginLocationState = {
  from?: {
    pathname?: string;
  };
  message?: string;
};

const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { signIn, resetError, error } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const locationState = location.state as LoginLocationState | null;
  const from = locationState?.from?.pathname || '/library';
  const successMessage = locationState?.message;

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
      navigate(from, { replace: true });
    } catch (err) {
      setFormError(toAuthErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-paper-100">
      <header className="mx-auto flex h-phi-header w-full max-w-phi-container items-center justify-between px-phi-5 lg:px-phi-6">
        <Link
          to="/"
          className="rounded-phi-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <BrandMark />
        </Link>
        <Link
          to="/"
          className="inline-flex items-center gap-phi-2 text-phi-sm text-ink-secondary transition-colors duration-phi-fast hover:text-ink-primary"
        >
          <ArrowLeft className="h-4 w-4" strokeWidth={1.5} />
          Overview
        </Link>
      </header>

      <main className="mx-auto flex w-full max-w-phi-container flex-1 items-center justify-center px-phi-5 py-phi-6 lg:px-phi-6">
        <div className="grid w-full max-w-[56.86rem] overflow-hidden rounded-phi-lg border border-[rgba(25,24,22,0.1)] bg-paper-50 shadow-card md:grid-cols-phi-rev">
          <aside className="flex flex-col justify-between border-b border-[rgba(25,24,22,0.08)] bg-paper-200/55 p-phi-5 sm:p-phi-6 md:border-b-0 md:border-r">
            <div className="space-y-phi-4">
              <p className="font-mono text-phi-2xs text-ink-muted">Workspace access</p>
              <h1 className="font-serif text-phi-xl font-normal leading-phi-tight tracking-[-0.02em] text-ink-primary">
                Sign in to your reading library
              </h1>
              <p className="text-phi-sm leading-phi text-ink-secondary">
                Open your indexed PDFs, cross-document passage links, and page chat history from where you left off.
              </p>
            </div>

            <div className="mt-phi-6 space-y-phi-3 border-t border-[rgba(25,24,22,0.08)] pt-phi-5 text-phi-sm text-ink-secondary">
              <div className="folio-mark pl-phi-4">
                <p className="font-medium text-ink-primary">Page-grounded retrieval</p>
                <p className="mt-phi-1 text-phi-xs text-ink-muted">
                  Every answer links back to the exact PDF and page
                </p>
              </div>
              <div className="pl-phi-4">
                <p className="font-medium text-ink-primary">Role-aware context</p>
                <p className="mt-phi-1 text-phi-xs text-ink-muted">
                  Saved reading persona and research goal stay synced
                </p>
              </div>
            </div>
          </aside>

          <form className="flex flex-col justify-center gap-phi-5 p-phi-5 sm:p-phi-6" onSubmit={handleSubmit}>
            <div>
              <label className="text-phi-sm font-medium text-ink-primary" htmlFor="email">
                Email address
              </label>
              <div className="mt-phi-2 flex h-phi-ctrl items-center gap-phi-3 rounded-phi-md border border-[rgba(25,24,22,0.14)] bg-app-surface px-phi-3 text-ink-primary transition-colors duration-phi-fast focus-within:border-ink-primary focus-within:ring-2 focus-within:ring-accent/15">
                <Mail className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="w-full bg-transparent text-phi-sm text-ink-primary placeholder:text-ink-faint focus:outline-none"
                  placeholder="name@company.com"
                  autoComplete="email"
                  required
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label className="text-phi-sm font-medium text-ink-primary" htmlFor="password">
                  Password
                </label>
                <Link
                  to={FORGOT_PASSWORD_PATH}
                  state={{ email }}
                  className="text-phi-xs text-ink-secondary transition-colors duration-phi-fast hover:text-accent-ink"
                >
                  Forgot password
                </Link>
              </div>
              <PasswordInput
                id="password"
                value={password}
                onValueChange={setPassword}
                placeholder="Enter password"
                autoComplete="current-password"
                required
              />
            </div>

            {successMessage && (
              <div className="rounded-phi-md border border-semantic-positive/25 bg-semantic-positiveBg px-phi-4 py-phi-3 text-phi-sm text-semantic-positive">
                {successMessage}
              </div>
            )}

            {(formError || error) && (
              <div
                role="alert"
                className="rounded-phi-md border border-semantic-negative/25 bg-semantic-negativeBg px-phi-4 py-phi-3 text-phi-sm text-semantic-negative"
              >
                {formError || error?.message}
              </div>
            )}

            <button type="submit" disabled={isSubmitting} className="btn-primary h-phi-ctrl w-full">
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
                  Signing in
                </>
              ) : (
                'Sign in'
              )}
            </button>

            <p className="text-phi-sm text-ink-secondary">
              No account yet?{' '}
              <Link
                to="/signup"
                className="font-medium text-accent-ink transition-colors duration-phi-fast hover:underline"
              >
                Create an account
              </Link>
            </p>
          </form>
        </div>
      </main>
    </div>
  );
};

export default LoginPage;
