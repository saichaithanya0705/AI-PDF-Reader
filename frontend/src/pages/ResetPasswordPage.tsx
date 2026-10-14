import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { KeyRound, Loader2 } from 'lucide-react';
import { useAuth } from '../context/useAuth';
import PasswordInput from '../components/PasswordInput';
import { toAuthErrorMessage } from '../lib/authErrors';
import { FORGOT_PASSWORD_PATH, MIN_PASSWORD_LENGTH } from '../lib/authRoutes';

/**
 * Landing page for the emailed reset link. Supabase exchanges the link's token
 * for a short-lived session (detectSessionInUrl), which authorises updateUser.
 */
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
      // Sign out of the recovery session so the new password is proven on next sign-in.
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
    <div className="relative flex min-h-screen items-center justify-center px-6 py-16">
      <div className="w-full max-w-md rounded-3xl border border-white/10 bg-slate-950/80 p-8 shadow-glow backdrop-blur">
        <div className="flex items-center gap-3">
          <span className="rounded-xl bg-cyan-400/10 p-2 text-cyan-300">
            <KeyRound className="h-5 w-5" />
          </span>
          <h1 className="text-2xl text-white">Choose a new password</h1>
        </div>

        {loading ? (
          <div className="mt-8 flex items-center gap-2 text-sm text-slate-300">
            <Loader2 className="h-4 w-4 animate-spin" />
            Verifying your reset link...
          </div>
        ) : !hasRecoverySession ? (
          <div className="mt-6 space-y-4">
            <div role="alert" className="rounded-2xl border border-aurora/40 bg-aurora/10 px-4 py-3 text-sm text-aurora">
              This reset link is invalid or has expired. Links work once and only on the device that opens them.
            </div>
            <Link
              to={FORGOT_PASSWORD_PATH}
              className="inline-flex rounded-full bg-brand-500 px-6 py-3 text-sm font-semibold text-white shadow-glow transition hover:bg-brand-400"
            >
              Request a new link
            </Link>
          </div>
        ) : (
          <form className="mt-6 flex flex-col gap-5" onSubmit={handleSubmit} noValidate>
            {session?.user?.email && (
              <p className="text-sm text-slate-300">
                Resetting the password for <span className="font-medium text-white">{session.user.email}</span>.
              </p>
            )}
            <div>
              <label className="text-sm font-medium text-white" htmlFor="new-password">
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
              <label className="text-sm font-medium text-white" htmlFor="confirm-new-password">
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
                  Updating password
                </>
              ) : (
                'Update password'
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default ResetPasswordPage;
