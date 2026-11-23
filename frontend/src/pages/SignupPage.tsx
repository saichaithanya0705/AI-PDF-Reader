import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, Mail, Shield, UserCog } from 'lucide-react';
import { useAuth } from '../context/useAuth';
import PasswordInput from '../components/PasswordInput';
import BrandMark from '../components/BrandMark';
import { toAuthErrorMessage } from '../lib/authErrors';

const SignupPage = () => {
  const navigate = useNavigate();
  const { signUp, resetError, error } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [persona, setPersona] = useState('');
  const [role, setRole] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    resetError();

    if (!email || !password || !confirmPassword) {
      setFormError('Complete all required fields.');
      return;
    }

    if (password !== confirmPassword) {
      setFormError('Passwords do not match.');
      return;
    }

    if (password.length < 6) {
      setFormError('Password must be at least 6 characters.');
      return;
    }

    try {
      setIsSubmitting(true);
      await signUp({ email, password, metadata: { persona, role } });
      navigate('/login', {
        state: {
          message: 'Account created. Sign in to open your library.',
        },
      });
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
              <p className="font-mono text-phi-2xs text-ink-muted">New workspace</p>
              <h1 className="font-serif text-phi-xl font-normal leading-phi-tight tracking-[-0.02em] text-ink-primary">
                Create a document workspace
              </h1>
              <p className="text-phi-sm leading-phi text-ink-secondary">
                Upload PDFs, link passages across your collection, and tailor recommendations to your role.
              </p>
            </div>

            <div className="mt-phi-6 space-y-phi-3 border-t border-[rgba(25,24,22,0.08)] pt-phi-5 text-phi-sm text-ink-secondary">
              <div className="folio-mark pl-phi-4">
                <p className="font-medium text-ink-primary">Single and bulk ingestion</p>
                <p className="mt-phi-1 text-phi-xs text-ink-muted">
                  Validate PDFs on upload and avoid duplicate copies
                </p>
              </div>
              <div className="pl-phi-4">
                <p className="font-medium text-ink-primary">Private by default</p>
                <p className="mt-phi-1 text-phi-xs text-ink-muted">
                  Documents and chat sessions stay scoped to your account
                </p>
              </div>
            </div>
          </aside>

          <form className="flex flex-col gap-phi-4 p-phi-5 sm:p-phi-6" onSubmit={handleSubmit}>
            <div>
              <label className="text-phi-sm font-medium text-ink-primary" htmlFor="signup-email">
                Work email
              </label>
              <div className="mt-phi-2 flex h-phi-ctrl items-center gap-phi-3 rounded-phi-md border border-[rgba(25,24,22,0.14)] bg-app-surface px-phi-3 text-ink-primary transition-colors duration-phi-fast focus-within:border-ink-primary focus-within:ring-2 focus-within:ring-accent/15">
                <Mail className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
                <input
                  id="signup-email"
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

            <div className="grid gap-phi-4 sm:grid-cols-2">
              <div>
                <label className="text-phi-sm font-medium text-ink-primary" htmlFor="persona">
                  Primary persona <span className="font-normal text-ink-muted">(optional)</span>
                </label>
                <div className="mt-phi-2 flex h-phi-ctrl items-center gap-phi-3 rounded-phi-md border border-[rgba(25,24,22,0.14)] bg-app-surface px-phi-3 text-ink-primary transition-colors duration-phi-fast focus-within:border-ink-primary focus-within:ring-2 focus-within:ring-accent/15">
                  <UserCog className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
                  <input
                    id="persona"
                    type="text"
                    value={persona}
                    onChange={(event) => setPersona(event.target.value)}
                    className="w-full bg-transparent text-phi-sm text-ink-primary placeholder:text-ink-faint focus:outline-none"
                    placeholder="Research Analyst"
                  />
                </div>
              </div>
              <div>
                <label className="text-phi-sm font-medium text-ink-primary" htmlFor="role">
                  Team role <span className="font-normal text-ink-muted">(optional)</span>
                </label>
                <div className="mt-phi-2 flex h-phi-ctrl items-center gap-phi-3 rounded-phi-md border border-[rgba(25,24,22,0.14)] bg-app-surface px-phi-3 text-ink-primary transition-colors duration-phi-fast focus-within:border-ink-primary focus-within:ring-2 focus-within:ring-accent/15">
                  <Shield className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
                  <input
                    id="role"
                    type="text"
                    value={role}
                    onChange={(event) => setRole(event.target.value)}
                    className="w-full bg-transparent text-phi-sm text-ink-primary placeholder:text-ink-faint focus:outline-none"
                    placeholder="Policy Review"
                  />
                </div>
              </div>
            </div>

            <div className="grid gap-phi-4 sm:grid-cols-2">
              <div>
                <label className="text-phi-sm font-medium text-ink-primary" htmlFor="signup-password">
                  Password
                </label>
                <PasswordInput
                  id="signup-password"
                  value={password}
                  onValueChange={setPassword}
                  placeholder="Min 6 characters"
                  autoComplete="new-password"
                  required
                />
              </div>
              <div>
                <label
                  className="text-phi-sm font-medium text-ink-primary"
                  htmlFor="signup-password-confirm"
                >
                  Confirm password
                </label>
                <PasswordInput
                  id="signup-password-confirm"
                  value={confirmPassword}
                  onValueChange={setConfirmPassword}
                  placeholder="Repeat password"
                  autoComplete="new-password"
                  required
                />
              </div>
            </div>

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
                  Creating account
                </>
              ) : (
                'Create account'
              )}
            </button>

            <p className="text-phi-sm text-ink-secondary">
              Already have an account?{' '}
              <Link
                to="/login"
                className="font-medium text-accent-ink transition-colors duration-phi-fast hover:underline"
              >
                Sign in
              </Link>
            </p>
          </form>
        </div>
      </main>
    </div>
  );
};

export default SignupPage;
