import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from '../context/useAuth';
import PasswordInput from '../components/PasswordInput';
import BrandMark from '../components/BrandMark';
import { toAuthErrorMessage } from '../lib/authErrors';
import { FORGOT_PASSWORD_PATH, MIN_PASSWORD_LENGTH } from '../lib/authRoutes';

const ResetPasswordPage = () => {
  const navigate = useNavigate();
  const { session, loading, isPasswordRecovery, updatePassword, signOut } = useAuth();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);

    if (password.length < MIN_PASSWORD_LENGTH) {
      setFormError(`Use at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    if (password !== confirmPassword) {
      setFormError('The two passwords do not match.');
      return;
    }

    try {
      setIsSubmitting(true);
      await updatePassword(password);
      await signOut().catch(() => undefined);
      navigate('/login', {
        replace: true,
        state: { message: 'Password updated. Sign in with your new password.' },
      });
    } catch (err) {
      setFormError(toAuthErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const hasRecoverySession = Boolean(session) || isPasswordRecovery;

  return (
    <div className="flex min-h-screen flex-col bg-paper-100">
      <header className="mx-auto flex h-phi-header w-full max-w-phi-container items-center justify-between px-phi-5 lg:px-phi-6">
        <Link
          to="/"
          className="rounded-phi-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <BrandMark />
        </Link>
      </header>

      <main className="mx-auto flex w-full max-w-phi-modal-sm flex-1 items-center justify-center px-phi-5 py-phi-6">
        <div className="w-full rounded-phi-lg border border-[rgba(25,24,22,0.1)] bg-paper-50 p-phi-5 shadow-card sm:p-phi-6">
          <p className="font-mono text-phi-2xs text-ink-muted">Account recovery</p>
          <h1 className="mt-phi-2 font-serif text-phi-xl font-normal leading-phi-tight tracking-[-0.02em] text-ink-primary">
            Choose a new password
          </h1>

          {loading ? (
            <div className="mt-phi-5 flex items-center gap-phi-2 text-phi-sm text-ink-secondary">
              <Loader2 className="h-4 w-4 animate-spin text-ink-muted" strokeWidth={1.5} />
              Verifying your reset link
            </div>
          ) : !hasRecoverySession ? (
            <div className="mt-phi-5 space-y-phi-4">
              <div
                role="alert"
                className="rounded-phi-md border border-semantic-negative/25 bg-semantic-negativeBg px-phi-4 py-phi-3 text-phi-sm text-semantic-negative"
              >
                This reset link is invalid or has expired. Links work once and only on the device that opens them.
              </div>
              <Link to={FORGOT_PASSWORD_PATH} className="btn-primary h-phi-ctrl">
                Request a new link
              </Link>
            </div>
          ) : (
            <form className="mt-phi-5 flex flex-col gap-phi-5" onSubmit={handleSubmit} noValidate>
              {session?.user?.email && (
                <p className="text-phi-sm text-ink-secondary">
                  Resetting the password for{' '}
                  <span className="font-medium text-ink-primary">{session.user.email}</span>.
                </p>
              )}
              <div>
                <label className="text-phi-sm font-medium text-ink-primary" htmlFor="new-password">
                  New password
                </label>
                <PasswordInput
                  id="new-password"
                  value={password}
                  onValueChange={setPassword}
                  placeholder={`At least ${MIN_PASSWORD_LENGTH} characters`}
                  autoComplete="new-password"
                  autoFocus
                  required
                />
              </div>
              <div>
                <label
                  className="text-phi-sm font-medium text-ink-primary"
                  htmlFor="confirm-new-password"
                >
                  Confirm new password
                </label>
                <PasswordInput
                  id="confirm-new-password"
                  value={confirmPassword}
                  onValueChange={setConfirmPassword}
                  placeholder="Repeat the new password"
                  autoComplete="new-password"
                  required
                />
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
                    Updating password
                  </>
                ) : (
                  'Update password'
                )}
              </button>
            </form>
          )}
        </div>
      </main>
    </div>
  );
};

export default ResetPasswordPage;
