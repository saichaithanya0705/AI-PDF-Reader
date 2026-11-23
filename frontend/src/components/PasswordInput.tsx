import { useState } from 'react';
import type { InputHTMLAttributes } from 'react';
import { Eye, EyeOff, Lock } from 'lucide-react';

type PasswordInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'onChange'> & {
  value: string;
  onValueChange: (value: string) => void;
};

/** Password field with a show/hide toggle, styled on the golden-ratio token scale. */
const PasswordInput = ({ value, onValueChange, className, ...inputProps }: PasswordInputProps) => {
  const [visible, setVisible] = useState(false);

  return (
    <div className="mt-phi-2 flex h-phi-ctrl items-center gap-phi-3 rounded-phi-md border border-[rgba(25,24,22,0.14)] bg-app-surface px-phi-3 text-ink-primary transition-colors duration-phi-fast focus-within:border-ink-primary focus-within:ring-2 focus-within:ring-accent/15">
      <Lock className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
      <input
        {...inputProps}
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={(event) => onValueChange(event.target.value)}
        className={
          className ??
          'w-full bg-transparent text-phi-sm text-ink-primary placeholder:text-ink-faint focus:outline-none'
        }
      />
      <button
        type="button"
        onClick={() => setVisible((current) => !current)}
        className="shrink-0 rounded-phi-xs p-phi-1 text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        aria-label={visible ? 'Hide password' : 'Show password'}
        aria-pressed={visible}
        aria-controls={inputProps.id}
      >
        {visible ? <EyeOff className="h-4 w-4" strokeWidth={1.5} /> : <Eye className="h-4 w-4" strokeWidth={1.5} />}
      </button>
    </div>
  );
};

export default PasswordInput;
