import React from 'react';

interface BrandMarkProps {
  compact?: boolean;
  subtitle?: string;
}

/** Flat editorial folio mark sized to 1.618rem (phi-5) with a vermilion margin rule. */
export const BrandMark: React.FC<BrandMarkProps> = ({ compact = false, subtitle }) => (
  <span className="inline-flex items-center gap-phi-3 text-ink-primary">
    <svg
      width="26"
      height="26"
      viewBox="0 0 26 26"
      fill="none"
      aria-hidden="true"
      className="h-phi-5 w-phi-5 shrink-0"
    >
      <rect
        x="2"
        y="2"
        width="22"
        height="22"
        rx="5"
        fill="#fcfbf8"
        stroke="#191816"
        strokeWidth="1.5"
      />
      <rect x="7" y="6.5" width="2.2" height="13" rx="1" fill="#c23b22" />
      <line x1="12" y1="9" x2="19" y2="9" stroke="#191816" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="12" y1="13" x2="17.5" y2="13" stroke="#57534e" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="12" y1="17" x2="15.5" y2="17" stroke="#76716a" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
    {!compact && (
      <span className="flex flex-col">
        <span className="font-sans text-phi-sm font-medium leading-none tracking-[-0.01em] text-ink-primary">
          Document Intelligence Studio
        </span>
        {subtitle && (
          <span className="mt-phi-1 font-mono text-phi-2xs leading-none text-ink-muted">
            {subtitle}
          </span>
        )}
      </span>
    )}
  </span>
);

export default BrandMark;
