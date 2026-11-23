import { FormEvent, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowLeft, Loader2, Mail, MailCheck } from 'lucide-react';
import { useAuth } from '../context/useAuth';
import { toAuthErrorMessage } from '../lib/authErrors';
import BrandMark from '../components/BrandMark';

const ForgotPasswordPage = () => {
  const location = useLocation();
  const { requestPasswordReset } = useAuth();
  const prefilledEmail = (location.state as { email?: string } | null)?.email ?? '';
  const [email, setEmail] = useState(prefilledEmail);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    const trimmed = email.trim();
    if (!trimmed) {
      setFormError('Enter the email address you signed up with.');
      return;
    }

    try {
      setIsSubmitting(true);
      await requestPasswordReset(trimmed);
      setSentTo(trimmed);
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
          to="/login"
          className="inline-flex items-center gap-phi-2 text-phi-sm text-ink-secondary transition-colors duration-phi-fast hover:text-ink-primary"
        >
          <ArrowLeft className="h-4 w-4" strokeWidth={1.5} />
          Back to sign in
        </Link>
      </header>

      <main className="mx-auto flex w-full max-w-phi-modal-sm flex-1 items-center justify-center px-phi-5 py-phi-6">
        <div className="w-full rounded-phi-lg border border-[rgba(25,24,22,0.1)] bg-paper-50 p-phi-5 shadow-card sm:p-phi-6">
          <p className="font-mono text-phi-2xs text-ink-muted">Account recovery</p>
          <h1 className="mt-phi-2 font-serif text-phi-xl font-normal leading-phi-tight tracking-[-0.02em] text-ink-primary">
            Reset password
          </h1>

          {sentTo ? (
            <div className="mt-phi-5 space-y-phi-4">
              <div className="flex gap-phi-3 rounded-phi-md border border-semantic-positive/25 bg-semantic-positiveBg px-phi-4 py-phi-3 text-phi-sm text-semantic-positive">
                <MailCheck className="mt-phi-1 h-4 w-4 shrink-0" strokeWidth={1.5} />
                <p>
                  If an account exists for{' '}
                  <span className="font-medium text-ink-primary">{sentTo}</span>, a reset link is on its way. Open it on this device to choose a new password.
                </p>
              </div>
              <p className="text-phi-xs leading-phi text-ink-muted">
                Nothing after a few minutes? Check your spam folder. Reset emails are rate-limited, so wait before requesting another.
              </p>
              <button
                type="button"
                onClick={() => setSentTo(null)}
                className="text-phi-sm font-medium text-accent-ink transition-colors duration-phi-fast hover:underline"
              >
                Use a different email
              </button>
            </div>
          ) : (
            <form className="mt-phi-5 flex flex-col gap-phi-5" onSubmit={handleSubmit} noValidate>
              <p className="text-phi-sm leading-phi text-ink-secondary">
                Enter your account email and we will send a link to choose a new password.
              </p>
              <div>
                <label className="text-phi-sm font-medium text-ink-primary" htmlFor="reset-email">
                  Email address
                </label>
                <div className="mt-phi-2 flex h-phi-ctrl items-center gap-phi-3 rounded-phi-md border border-[rgba(25,24,22,0.14)] bg-app-surface px-phi-3 text-ink-primary transition-colors duration-phi-fast focus-within:border-ink-primary focus-within:ring-2 focus-within:ring-accent/15">
                  <Mail className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
                  <input
                    id="reset-email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="w-full bg-transparent text-phi-sm text-ink-primary placeholder:text-ink-faint focus:outline-none"
                    placeholder="name@company.com"
                    autoComplete="email"
                    autoFocus
                    required
                  />
                </div>
              </div>

              {formError && (
                <div
                  role="alert"
                  className="rounded-phi-md border border-semantic-negative/25 bg-semantic-negativeBg px-phi-4 py-phi-3 text-phi-sm text-semantic-negative"
                >
                  {formError}
                </div>
              )}

              <button type="submit" disabled={isSubmitting} className="btn-primary h-phi-ctrl w-full">
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
                    Sending link
                  </>
                ) : (
                  'Send reset link'
                )}
              </button>
            </form>
          )}
        </div>
      </main>
    </div>
  );
};

export default ForgotPasswordPage;
