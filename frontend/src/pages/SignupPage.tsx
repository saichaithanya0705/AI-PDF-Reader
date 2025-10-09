import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, BadgeCheck, Loader2, Mail, Shield, UserCog } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

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
      setFormError('Please complete all required fields.');
      return;
    }

    if (password !== confirmPassword) {
      setFormError('Passwords do not match.');
      return;
    }

    if (password.length < 6) {
      setFormError('Password must be at least 6 characters long.');
      return;
    }

    try {
      setIsSubmitting(true);
      await signUp({ email, password, metadata: { persona, role } });
      // Redirect to login with success state
      navigate('/login', { 
        state: { 
          message: 'Account created successfully! Please sign in to continue.' 
        } 
      });
    } catch (err) {
      if (err instanceof Error) {
        setFormError(err.message);
      } else {
        setFormError('Unable to create account. Try again later.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center px-6 py-16">
      <div className="absolute inset-0 -z-10 opacity-60">
        <div className="mx-auto h-full w-full max-w-4xl rounded-full bg-gradient-to-r from-cyan-500/20 via-brand-500/20 to-fuchsia-500/20 blur-3xl" />
      </div>

      <div className="w-full max-w-5xl rounded-3xl border border-white/10 bg-slate-950/80 p-8 shadow-glow backdrop-blur">
        <div className="flex flex-col gap-6 md:flex-row md:items-stretch md:gap-12">
          <div className="flex flex-1 flex-col justify-between gap-6 rounded-2xl border border-white/5 bg-white/5 p-6">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="flex items-center gap-2 text-sm text-slate-300 transition hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
            <div className="flex flex-col gap-4">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.3em] text-slate-300">
                <BadgeCheck className="h-3.5 w-3.5" />
                Create your workspace
              </span>
              <h1 className="text-3xl sm:text-4xl">Launch a secure AI workspace for your documents.</h1>
              <p className="text-sm leading-relaxed text-slate-300">
                Personalise your experience with custom personas and jobs to keep recommendations relevant across your team.
              </p>
            </div>
            <div className="space-y-3 text-xs text-slate-400">
              <p>• Unlimited PDF uploads with smart deduplication</p>
              <p>• Persona-aware insights synced to the Reader</p>
              <p>• Invite teammates and manage roles in-app</p>
            </div>
          </div>

          <form className="flex flex-1 flex-col gap-6" onSubmit={handleSubmit}>
            <div>
              <label className="text-sm font-medium text-white" htmlFor="signup-email">
                Work email
              </label>
              <div className="mt-2 flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-slate-200 focus-within:border-brand-400 focus-within:bg-slate-900">
                <Mail className="h-4 w-4 text-slate-400" />
                <input
                  id="signup-email"
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

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-white" htmlFor="persona">
                  Primary persona (optional)
                </label>
                <div className="mt-2 flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-slate-200 focus-within:border-brand-400 focus-within:bg-slate-900">
                  <UserCog className="h-4 w-4 text-slate-400" />
                  <input
                    id="persona"
                    type="text"
                    value={persona}
                    onChange={(event) => setPersona(event.target.value)}
                    className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none"
                    placeholder="Product Designer"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-white" htmlFor="role">
                  Team role (optional)
                </label>
                <div className="mt-2 flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-slate-200 focus-within:border-brand-400 focus-within:bg-slate-900">
                  <Shield className="h-4 w-4 text-slate-400" />
                  <input
                    id="role"
                    type="text"
                    value={role}
                    onChange={(event) => setRole(event.target.value)}
                    className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none"
                    placeholder="Head of Compliance"
                  />
                </div>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-white" htmlFor="signup-password">
                  Password
                </label>
                <input
                  id="signup-password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="mt-2 w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-brand-400 focus:bg-slate-900 focus:outline-none"
                  placeholder="Create a strong password"
                  autoComplete="new-password"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-medium text-white" htmlFor="signup-password-confirm">
                  Confirm password
                </label>
                <input
                  id="signup-password-confirm"
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  className="mt-2 w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-brand-400 focus:bg-slate-900 focus:outline-none"
                  placeholder="Re-enter your password"
                  autoComplete="new-password"
                  required
                />
              </div>
            </div>

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
                  Creating account
                </>
              ) : (
                'Create account'
              )}
            </button>

            <p className="text-sm text-slate-300">
              Already have an account?{' '}
              <Link to="/login" className="font-medium text-cyan-300 transition hover:text-cyan-200">
                Sign in
              </Link>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
};

export default SignupPage;
