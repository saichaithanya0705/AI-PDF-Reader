import React, { useState, useEffect, useRef } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  CheckSquare,
  FileText,
  Lightbulb,
  MoreHorizontal,
  Pencil,
  Scissors,
  Trash2,
  Volume2,
} from 'lucide-react';
import { PDFDocument } from '../context/PDFContext';
import { useNavigate } from 'react-router-dom';

interface DocumentCardProps {
  document: PDFDocument;
  onClick: () => void;
  isSelectMode?: boolean;
  isSelected?: boolean;
  onOpen: (id: string) => void;
  onSplit: (id: string) => void;
  onDelete: (id: string) => void;
  onRename: (id: string) => void;
  onSelectMode: () => void;
}

const DocumentCard: React.FC<DocumentCardProps> = ({
  document,
  onClick,
  isSelectMode = false,
  isSelected = false,
  onOpen,
  onSplit,
  onDelete,
  onRename,
  onSelectMode,
}) => {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!showMenu) return;

    const handleClickOutside = (event: Event) => {
      const target = event.target as Element | null;
      if (!target || !menuRef.current) return;
      if (!menuRef.current.contains(target)) {
        setShowMenu(false);
      }
    };

    window.document.addEventListener('click', handleClickOutside, true);
    return () => {
      window.document.removeEventListener('click', handleClickOutside, true);
    };
  }, [showMenu]);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (date: Date | string | null | undefined) => {
    try {
      if (!date) return 'Unknown date';
      const dateObj = date instanceof Date ? date : new Date(date);
      if (Number.isNaN(dateObj.getTime())) return 'Unknown date';

      return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }).format(dateObj);
    } catch {
      return 'Unknown date';
    }
  };

  const validation = document.validation;
  const isValid = validation?.isValid ?? true;
  const severity = validation?.severity ?? 'success';

  const handleCardClick = (e: React.MouseEvent) => {
    if (showMenu) {
      setShowMenu(false);
      e.stopPropagation();
      return;
    }
    onClick();
  };

  const cardTone = !isValid
    ? 'border-semantic-negative/35 bg-semantic-negativeBg/40'
    : severity === 'warning'
      ? 'border-semantic-warning/35 bg-semantic-warningBg/40'
      : isSelected
        ? 'border-accent bg-accent-soft/35'
        : 'border-[rgba(25,24,22,0.09)] bg-app-surface hover:border-[rgba(25,24,22,0.2)]';

  return (
    <article
      ref={cardRef}
      onClick={handleCardClick}
      className={`group relative flex h-full cursor-pointer flex-col rounded-phi-lg border p-phi-5 shadow-subtle transition-colors duration-phi-fast ${cardTone}`}
    >
      {/* Top Row: Document mark + selection/menu */}
      <div className="flex items-start justify-between gap-phi-3">
        <div
          className={`relative flex h-phi-6 w-phi-6 shrink-0 items-center justify-center rounded-phi-md border ${
            !isValid
              ? 'border-semantic-negative/25 bg-semantic-negativeBg text-semantic-negative'
              : severity === 'warning'
                ? 'border-semantic-warning/25 bg-semantic-warningBg text-semantic-warning'
                : 'border-[rgba(25,24,22,0.09)] bg-paper-100 text-ink-secondary'
          }`}
        >
          <FileText className="h-4 w-4" strokeWidth={1.5} />
          {validation && (
            <span
              className="absolute -bottom-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-app-surface"
              title={validation.summary}
            >
              {severity === 'error' ? (
                <AlertCircle className="h-3.5 w-3.5 text-semantic-negative" strokeWidth={1.75} />
              ) : severity === 'warning' ? (
                <AlertTriangle className="h-3.5 w-3.5 text-semantic-warning" strokeWidth={1.75} />
              ) : (
                <CheckCircle2 className="h-3.5 w-3.5 text-semantic-positive" strokeWidth={1.75} />
              )}
            </span>
          )}
        </div>

        <div className="flex items-center gap-phi-2">
          {isSelectMode && (
            <input
              type="checkbox"
              checked={isSelected}
              onChange={() => {}}
              aria-label={`Select ${document.name}`}
              className="h-4 w-4 rounded-phi-xs border-[rgba(25,24,22,0.25)] accent-accent"
            />
          )}

          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setShowMenu((prev) => !prev);
              }}
              className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              aria-label={`Actions for ${document.name}`}
            >
              <MoreHorizontal className="h-4 w-4" strokeWidth={1.5} />
            </button>

            {showMenu && (
              <div
                className="absolute right-0 z-30 mt-phi-1 w-52 rounded-phi-md border border-[rgba(25,24,22,0.12)] bg-app-surface py-phi-1 shadow-float"
                onClick={(e) => e.stopPropagation()}
              >
                {!isSelectMode && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectMode();
                      setShowMenu(false);
                    }}
                    className="flex w-full items-center gap-phi-3 px-phi-3 py-phi-2 text-left text-phi-sm text-ink-primary transition-colors duration-phi-fast hover:bg-paper-200/70"
                  >
                    <CheckSquare className="h-4 w-4 text-ink-muted" strokeWidth={1.5} />
                    Select
                  </button>
                )}

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRename(document.id);
                    setShowMenu(false);
                  }}
                  className="flex w-full items-center gap-phi-3 px-phi-3 py-phi-2 text-left text-phi-sm text-ink-primary transition-colors duration-phi-fast hover:bg-paper-200/70"
                >
                  <Pencil className="h-4 w-4 text-ink-muted" strokeWidth={1.5} />
                  Rename
                </button>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSplit(document.id);
                    setShowMenu(false);
                  }}
                  className="flex w-full items-center gap-phi-3 px-phi-3 py-phi-2 text-left text-phi-sm text-ink-primary transition-colors duration-phi-fast hover:bg-paper-200/70"
                >
                  <Scissors className="h-4 w-4 text-ink-muted" strokeWidth={1.5} />
                  Split PDF
                </button>

                <div className="my-phi-1 border-t border-[rgba(25,24,22,0.08)]" />

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/reader/${document.id}?insights=true`);
                    setShowMenu(false);
                  }}
                  className="flex w-full items-center gap-phi-3 px-phi-3 py-phi-2 text-left text-phi-sm text-ink-primary transition-colors duration-phi-fast hover:bg-paper-200/70"
                >
                  <Lightbulb className="h-4 w-4 text-ink-muted" strokeWidth={1.5} />
                  Open with insights
                </button>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/reader/${document.id}?podcast=true`);
                    setShowMenu(false);
                  }}
                  className="flex w-full items-center gap-phi-3 px-phi-3 py-phi-2 text-left text-phi-sm text-ink-primary transition-colors duration-phi-fast hover:bg-paper-200/70"
                >
                  <Volume2 className="h-4 w-4 text-ink-muted" strokeWidth={1.5} />
                  Audio overview
                </button>

                <div className="my-phi-1 border-t border-[rgba(25,24,22,0.08)]" />

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(document.id);
                    setShowMenu(false);
                  }}
                  className="flex w-full items-center gap-phi-3 px-phi-3 py-phi-2 text-left text-phi-sm text-semantic-negative transition-colors duration-phi-fast hover:bg-semantic-negativeBg"
                >
                  <Trash2 className="h-4 w-4" strokeWidth={1.5} />
                  Delete
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Document Title & Validation */}
      <div className="mt-phi-4 flex-1">
        <h3
          className={`line-clamp-2 text-phi-base font-medium leading-phi-snug transition-colors duration-phi-fast ${
            !isValid
              ? 'text-semantic-negative'
              : 'text-ink-primary group-hover:text-accent-ink'
          }`}
          title={document.name}
        >
          {document.name}
        </h3>

        {validation && !isValid && (
          <div className="mt-phi-3 rounded-phi-md border border-semantic-negative/25 bg-semantic-negativeBg p-phi-3 text-phi-xs text-semantic-negative">
            <p className="font-medium">File issue detected</p>
            <p className="mt-phi-1 text-ink-secondary">{validation.summary}</p>
            {validation.issues.length > 1 && (
              <p className="mt-phi-1 font-mono text-phi-2xs tabular-nums">
                +{validation.issues.length - 1} more
              </p>
            )}
          </div>
        )}

        {validation && isValid && severity === 'warning' && (
          <div className="mt-phi-3 rounded-phi-md border border-semantic-warning/25 bg-semantic-warningBg p-phi-3 text-phi-xs text-semantic-warning">
            <p className="font-medium">Validation notice</p>
            <p className="mt-phi-1 text-ink-secondary">{validation.summary}</p>
          </div>
        )}
      </div>

      {/* Metadata & Primary Action */}
      <div className="mt-phi-5 border-t border-[rgba(25,24,22,0.07)] pt-phi-3">
        <div className="flex items-center justify-between gap-phi-2 font-mono text-phi-2xs tabular-nums text-ink-muted">
          <span>{formatDate(document.lastOpened || document.lastUploaded || document.uploadDate)}</span>
          <span>{formatFileSize(document.size)}</span>
        </div>

        {!isSelectMode && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onOpen(document.id);
            }}
            className="btn-secondary mt-phi-3 h-phi-ctrl-sm w-full text-phi-xs"
          >
            Open reader
          </button>
        )}
      </div>
    </article>
  );
};

export default DocumentCard;
