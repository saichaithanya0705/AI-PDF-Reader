import React, { useState, useEffect, useRef } from 'react';
import { FileText, Calendar, HardDrive, AlertTriangle, CheckCircle, AlertCircle, Lightbulb, Volume2 } from 'lucide-react';
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

const DocumentCard: React.FC<DocumentCardProps> = ({ document, onClick, isSelectMode = false, isSelected = false, onOpen, onSplit, onDelete, onRename, onSelectMode }) => {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // Close menu when clicking outside - simplified and safer approach
  useEffect(() => {
    if (!showMenu) return;

    const handleClickOutside = (event: Event) => {
      try {
        const target = event.target as Element;
        if (!target || !menuRef.current) return;
        
        // If click is outside the menu, close it
        if (!menuRef.current.contains(target)) {
          setShowMenu(false);
        }
      } catch (error) {
        console.warn('Error in click outside handler:', error);
        // Safely close menu on any error
        setShowMenu(false);
      }
    };

    // Use a more robust approach with try-catch
    try {
      document.addEventListener('click', handleClickOutside, true);
      return () => {
        try {
          document.removeEventListener('click', handleClickOutside, true);
        } catch (error) {
          console.warn('Error removing event listener:', error);
        }
      };
    } catch (error) {
      console.warn('Error adding event listener:', error);
      return () => {}; // Return empty cleanup function
    }
  }, [showMenu]);

  // Helper function to safely check if a date is valid
  const isValidDate = (date: Date | string | null | undefined): boolean => {
    try {
      if (!date) return false;
      let dateObj: Date;
      if (date instanceof Date) {
        dateObj = date;
      } else if (typeof date === 'string') {
        dateObj = new Date(date);
      } else {
        return false;
      }
      return !isNaN(dateObj.getTime());
    } catch {
      return false;
    }
  };

  // Debug logging for date issues
  console.log('📄 DocumentCard rendering:', {
    name: document.name,
    uploadDate: document.uploadDate,
    lastUploaded: document.lastUploaded,
    lastOpened: document.lastOpened,
    uploadDateType: typeof document.uploadDate,
    uploadDateValid: isValidDate(document.uploadDate),
    lastUploadedValid: isValidDate(document.lastUploaded),
    lastOpenedValid: isValidDate(document.lastOpened)
  });

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (date: Date | string | null | undefined) => {
    try {
      if (!date) return 'Unknown date';

      let dateObj: Date;
      if (date instanceof Date) {
        dateObj = date;
      } else if (typeof date === 'string') {
        dateObj = new Date(date);
      } else {
        return 'Invalid date';
      }

      // Check if date is valid
      if (isNaN(dateObj.getTime())) {
        return 'Invalid date';
      }

      return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      }).format(dateObj);
    } catch (error) {
      console.error('Error formatting date:', error, date);
      return 'Invalid date';
    }
  };

  // Get validation status
  const validation = document.validation;
  const isValid = validation?.isValid ?? true;
  const severity = validation?.severity ?? 'success';

  // Handle card click - close menu if open, otherwise proceed with onClick
  const handleCardClick = (e: React.MouseEvent) => {
    if (showMenu) {
      setShowMenu(false);
      e.stopPropagation();
      return;
    }
    onClick();
  };

  return (
    <div
      ref={cardRef}
      onClick={handleCardClick}
      className="group relative cursor-pointer"
    >
      {isSelectMode && (
        <div className="absolute top-4 right-4 z-10">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => {}} // Handled by parent onClick
            className="w-5 h-5 rounded border-slate-600 bg-slate-800 text-cyan-400"
          />
        </div>
      )}

      {/* Validation Status Overlay */}
      {validation && !isValid && (
        <div className="absolute inset-0 bg-red-500/10 rounded-xl border-2 border-red-500/50 z-5"></div>
      )}

      <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-400 to-purple-600 rounded-xl blur opacity-0 group-hover:opacity-30 transition-opacity duration-300"></div>
      <div className={`relative backdrop-blur rounded-xl p-6 border transition-all duration-200 h-full ${
        !isValid
          ? 'bg-red-900/20 border-red-500/50'
          : severity === 'warning'
            ? 'bg-yellow-900/10 border-yellow-500/30'
            : 'bg-slate-900/90 border-slate-700 hover:border-slate-600'
      }`}>
        {/* Document Icon with Validation Status */}
        <div className={`flex items-center justify-center w-16 h-16 rounded-lg mb-4 group-hover:scale-105 transition-transform relative ${
          !isValid
            ? 'bg-gradient-to-br from-red-400/20 to-red-600/20'
            : severity === 'warning'
              ? 'bg-gradient-to-br from-yellow-400/20 to-yellow-600/20'
              : 'bg-gradient-to-br from-cyan-400/20 to-purple-600/20'
        }`}>
          <FileText className={`w-8 h-8 ${
            !isValid ? 'text-red-400' :
            severity === 'warning' ? 'text-yellow-400' :
            'text-cyan-400'
          }`} />

          {/* Validation Status Badge */}
          {validation && (
            <div className="absolute -top-1 -right-1">
              {severity === 'error' ? (
                <AlertCircle className="w-5 h-5 text-red-400 bg-slate-900 rounded-full" />
              ) : severity === 'warning' ? (
                <AlertTriangle className="w-5 h-5 text-yellow-400 bg-slate-900 rounded-full" />
              ) : (
                <CheckCircle className="w-5 h-5 text-green-400 bg-slate-900 rounded-full" />
              )}
            </div>
          )}
        </div>

        {/* Document Info */}
        <div className="space-y-3 pb-16"> {/* Added bottom padding for the Open button */}
          <h3 className={`font-semibold text-lg line-clamp-2 transition-colors ${
            !isValid ? 'text-red-300' : 'text-white group-hover:text-cyan-400'
          }`}>
            {document.name}
          </h3>

          {/* Validation Message */}
          {validation && !isValid && (
            <div className="bg-red-900/30 border border-red-500/50 rounded-lg p-2">
              <div className="text-xs text-red-300 font-medium mb-1">
                ⚠️ File Issues Detected
              </div>
              <div className="text-xs text-red-400">
                {validation.summary}
              </div>
              {validation.issues.length > 1 && (
                <div className="text-xs text-red-500 mt-1">
                  +{validation.issues.length - 1} more issues
                </div>
              )}
            </div>
          )}

          {/* Warning Message */}
          {validation && isValid && severity === 'warning' && (
            <div className="bg-yellow-900/30 border border-yellow-500/50 rounded-lg p-2">
              <div className="text-xs text-yellow-300 font-medium mb-1">
                ⚠️ Warnings
              </div>
              <div className="text-xs text-yellow-400">
                {validation.summary}
              </div>
            </div>
          )}

          <div className="space-y-2 text-sm text-slate-400">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              <span>Uploaded: {formatDate(document.lastUploaded || document.uploadDate)}</span>
            </div>

            {document.lastOpened && (
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                <span>Opened: {formatDate(document.lastOpened)}</span>
              </div>
            )}

            <div className="flex items-center gap-2">
              <HardDrive className="w-4 h-4" />
              <span>{formatFileSize(document.size)}</span>
            </div>
          </div>
        </div>

        {/* Three-dot menu */}
        <div className="absolute top-2 right-2" ref={menuRef}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowMenu(!showMenu);
            }}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded transition-colors"
            title="More options"
          >
            <div className="flex flex-col gap-0.5">
              <div className="w-1 h-1 bg-current rounded-full" />
              <div className="w-1 h-1 bg-current rounded-full" />
              <div className="w-1 h-1 bg-current rounded-full" />
            </div>
          </button>

          {showMenu && (
            <div 
              className="absolute right-0 mt-2 w-40 bg-slate-800/95 backdrop-blur rounded-lg shadow-xl border border-slate-600/50 py-2 z-20"
              onClick={(e) => e.stopPropagation()} // Prevent the dropdown from triggering card click
            >
              {/* Rename Option */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRename(document.id);
                  setShowMenu(false);
                }}
                className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-blue-400 hover:bg-slate-700/60 hover:text-blue-300 transition-all duration-200"
                title="Rename this document"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Rename
              </button>

              {/* Split Option */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onSplit(document.id);
                  setShowMenu(false);
                }}
                className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-700/60 hover:text-white transition-all duration-200"
                title="Split this PDF into multiple documents"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
                Split PDF
              </button>

              {/* Divider */}
              <div className="my-1.5 border-t border-slate-600/50"></div>

              {/* Bonus Features Section */}
              <div className="px-3 py-1">
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Bonus Features (+10 pts)</p>
              </div>

              {/* Open with AI Insights */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/reader/${document.id}?insights=true`);
                  setShowMenu(false);
                }}
                className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-yellow-400 hover:bg-yellow-900/20 hover:text-yellow-300 transition-all duration-200"
                title="Open with AI Insights panel (+5 points)"
              >
                <Lightbulb className="w-4 h-4 animate-pulse" />
                <span>Open with Insights</span>
                <span className="ml-auto text-xs bg-yellow-400/20 text-yellow-400 px-1.5 py-0.5 rounded">+5</span>
              </button>

              {/* Generate Podcast */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/reader/${document.id}?podcast=true`);
                  setShowMenu(false);
                }}
                className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-purple-400 hover:bg-purple-900/20 hover:text-purple-300 transition-all duration-200"
                title="Generate podcast overview (+5 points)"
              >
                <Volume2 className="w-4 h-4" />
                <span>Generate Podcast</span>
                <span className="ml-auto text-xs bg-purple-400/20 text-purple-400 px-1.5 py-0.5 rounded">+5</span>
              </button>

              {/* Divider */}
              <div className="my-1.5 border-t border-slate-600/50"></div>

              {/* Delete Option */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(document.id);
                  setShowMenu(false);
                }}
                className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-red-400 hover:bg-red-900/30 hover:text-red-300 transition-all duration-200"
                title="Delete this document permanently"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete
              </button>
            </div>
          )}
        </div>

        {/* Open Document Button - Fixed at bottom */}
        {!isSelectMode && (
          <div className="absolute bottom-0 left-0 right-0 p-4">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onOpen(document.id);
              }}
              className="w-full bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-600 hover:to-purple-700 text-white text-sm font-medium py-2.5 px-4 rounded-lg transition-all duration-200 transform hover:scale-105 shadow-lg"
              title="Open this document for reading"
            >
              <div className="flex items-center justify-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                Open Document
              </div>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentCard;