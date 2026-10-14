import { FormEvent, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowLeft, KeyRound, Loader2, Mail, MailCheck } from 'lucide-react';
import { useAuth } from '../context/useAuth';
import { toAuthErrorMessage } from '../lib/authErrors';

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
    <div className="relative flex min-h-screen items-center justify-center px-6 py-16">
      <div className="w-full max-w-md rounded-3xl border border-white/10 bg-slate-950/80 p-8 shadow-glow backdrop-blur">
        <Link to="/login" className="flex items-center gap-2 text-sm text-slate-300 transition hover:text-white">
          <ArrowLeft className="h-4 w-4" />
          Back to sign in
        </Link>

        <div className="mt-6 flex items-center gap-3">
          <span className="rounded-xl bg-cyan-400/10 p-2 text-cyan-300">
            <KeyRound className="h-5 w-5" />
          </span>
          <h1 className="text-2xl text-white">Reset your password</h1>
        </div>

        {sentTo ? (
          <div className="mt-6 space-y-4">
            <div className="flex gap-3 rounded-2xl border border-cyan-400/40 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-200">
              <MailCheck className="mt-0.5 h-4 w-4 shrink-0" />
              <p>
                If an account exists for <span className="font-medium text-white">{sentTo}</span>, a reset
                link is on its way. Open it on this device to choose a new password.
              </p>
            </div>
            <p className="text-xs leading-relaxed text-slate-400">
              Nothing after a few minutes? Check your spam folder. Reset emails are rate-limited, so wait
              before requesting another.
            </p>
            <button
              type="button"
              onClick={() => setSentTo(null)}
              className="text-sm font-medium text-cyan-300 transition hover:text-cyan-200"
            >
              Use a different email
            </button>
          </div>
        ) : (
          <form className="mt-6 flex flex-col gap-5" onSubmit={handleSubmit} noValidate>
            <p className="text-sm text-slate-300">
              Enter your account email and we'll send you a link to set a new password.
            </p>
            <div>
              <label className="text-sm font-medium text-white" htmlFor="reset-email">
                Email address
              </label>
              <div className="mt-2 flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-slate-200 focus-within:border-brand-400 focus-within:bg-slate-900">
                <Mail className="h-4 w-4 text-slate-400" />
                <input
                  id="reset-email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none"
                  placeholder="you@company.com"
                  autoComplete="email"
                  autoFocus
                  required
                />
              </div>
            </div>

            {formError && (
              <div role="alert" className="rounded-2xl border border-aurora/40 bg-aurora/10 px-4 py-3 text-sm text-aurora">
                {formError}
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
                  Sending link
                </>
              ) : (
                'Send reset link'
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default ForgotPasswordPage;
