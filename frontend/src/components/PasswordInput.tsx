import { useState } from 'react';
import type { InputHTMLAttributes } from 'react';
import { Eye, EyeOff, Lock } from 'lucide-react';

type PasswordInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'onChange'> & {
  value: string;
  onValueChange: (value: string) => void;
};

/** Password field with a show/hide toggle, styled to match the auth pages. */
const PasswordInput = ({ value, onValueChange, className, ...inputProps }: PasswordInputProps) => {
  const [visible, setVisible] = useState(false);

  return (
    <div className="mt-2 flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-slate-200 focus-within:border-brand-400 focus-within:bg-slate-900">
      <Lock className="h-4 w-4 shrink-0 text-slate-400" />
      <input
        {...inputProps}
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={(event) => onValueChange(event.target.value)}
        className={className ?? 'w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none'}
      />
      <button
        type="button"
        onClick={() => setVisible((current) => !current)}
        className="shrink-0 rounded-md p-1 text-slate-400 transition hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
        aria-label={visible ? 'Hide password' : 'Show password'}
        aria-pressed={visible}
        aria-controls={inputProps.id}
      >
        {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
};

export default PasswordInput;
