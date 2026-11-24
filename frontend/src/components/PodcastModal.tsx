import React, { useCallback, useEffect, useRef, useState } from 'react';
import { X, Play, Pause, Volume2, Download, Loader2, RotateCcw, Headphones } from 'lucide-react';
import { fetchAuthenticatedBlobUrl, generatePodcast as generatePodcastApi } from '../lib/api';

interface PodcastModalProps {
  isVisible: boolean;
  onClose: () => void;
  documentId: string;
  currentPage: number;
  persona?: string;
  job?: string;
  variant?: 'modal' | 'docked';
  hideHeader?: boolean;
}

const PodcastModal: React.FC<PodcastModalProps> = ({
  isVisible,
  onClose,
  documentId,
  currentPage,
  persona,
  job,
  variant = 'modal',
  hideHeader = false,
}) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioExtension, setAudioExtension] = useState<'mp3' | 'wav'>('mp3');
  const [error, setError] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(1);

  const audioRef = useRef<HTMLAudioElement>(null);
  const audioObjectUrlRef = useRef<string | null>(null);

  const clearCurrentAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    if (audioObjectUrlRef.current) {
      URL.revokeObjectURL(audioObjectUrlRef.current);
      audioObjectUrlRef.current = null;
    }
    setAudioUrl(null);
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    setError(null);
  }, []);

  const generatePodcast = useCallback(async () => {
    if (!documentId) return;
    setIsGenerating(true);
    setError(null);

    try {
      const data = await generatePodcastApi(undefined, documentId, currentPage, persona, job);
      const audioPath =
        data && typeof data === 'object'
          ? (data as { audioUrl?: unknown; audio_url?: unknown }).audioUrl ??
            (data as { audio_url?: unknown }).audio_url
          : undefined;

      if (typeof audioPath !== 'string' || !audioPath.trim()) {
        throw new Error('Audio overview did not return a playable URL');
      }

      if (audioObjectUrlRef.current) {
        URL.revokeObjectURL(audioObjectUrlRef.current);
        audioObjectUrlRef.current = null;
      }

      const detectedExtension = audioPath.toLowerCase().endsWith('.wav') ? 'wav' : 'mp3';
      setAudioExtension(detectedExtension);

      const objectUrl = await fetchAuthenticatedBlobUrl(audioPath);
      audioObjectUrlRef.current = objectUrl;
      setAudioUrl(objectUrl);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate audio overview');
    } finally {
      setIsGenerating(false);
    }
  }, [currentPage, documentId, job, persona]);

  const togglePlayPause = useCallback(() => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
      return;
    }

    audioRef.current.play().then(
      () => setIsPlaying(true),
      (err) => {
        setIsPlaying(false);
        setError(err instanceof Error ? err.message : 'Unable to play generated audio');
      }
    );
  }, [isPlaying]);

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (audioRef.current) {
      const newTime = parseFloat(e.target.value);
      audioRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
  };

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const downloadAudio = () => {
    if (audioUrl) {
      const link = document.createElement('a');
      link.href = audioUrl;
      link.download = `audio_overview_page_${currentPage}.${audioExtension}`;
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  useEffect(() => {
    if (!isVisible) {
      clearCurrentAudio();
    }
  }, [clearCurrentAudio, isVisible]);

  useEffect(() => {
    clearCurrentAudio();
  }, [clearCurrentAudio, currentPage, documentId]);

  useEffect(() => {
    if (isVisible && documentId && !audioUrl && !isGenerating && !error) {
      generatePodcast();
    }
  }, [audioUrl, documentId, error, generatePodcast, isGenerating, isVisible]);

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (!isVisible || !audioUrl) return;
      const target = e.target;
      if (
        target instanceof HTMLElement &&
        (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable)
      ) {
        return;
      }

      switch (e.code) {
        case 'Space':
          e.preventDefault();
          togglePlayPause();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          if (audioRef.current) {
            audioRef.current.currentTime = Math.max(0, audioRef.current.currentTime - 10);
          }
          break;
        case 'ArrowRight':
          e.preventDefault();
          if (audioRef.current) {
            audioRef.current.currentTime = Math.min(duration, audioRef.current.currentTime + 10);
          }
          break;
      }
    };

    document.addEventListener('keydown', handleKeyPress);
    return () => document.removeEventListener('keydown', handleKeyPress);
  }, [isVisible, audioUrl, duration, togglePlayPause]);

  useEffect(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.volume = volume;
      const handlePlay = () => setIsPlaying(true);
      const handlePause = () => setIsPlaying(false);
      const handleEnded = () => setIsPlaying(false);
      audio.addEventListener('timeupdate', handleTimeUpdate);
      audio.addEventListener('loadedmetadata', handleLoadedMetadata);
      audio.addEventListener('play', handlePlay);
      audio.addEventListener('pause', handlePause);
      audio.addEventListener('ended', handleEnded);

      return () => {
        audio.removeEventListener('timeupdate', handleTimeUpdate);
        audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
        audio.removeEventListener('play', handlePlay);
        audio.removeEventListener('pause', handlePause);
        audio.removeEventListener('ended', handleEnded);
      };
    }
  }, [audioUrl, volume]);

  useEffect(
    () => () => {
      if (audioObjectUrlRef.current) {
        URL.revokeObjectURL(audioObjectUrlRef.current);
        audioObjectUrlRef.current = null;
      }
    },
    []
  );

  if (!isVisible) return null;

  const contentBody = (
    <>
      {(persona || job) && (
        <div className="folio-mark rounded-phi-md border border-[rgba(25,24,22,0.08)] bg-paper-50 py-phi-3 pl-phi-4 pr-phi-3 text-phi-xs">
          <p className="text-ink-muted">Tailored context</p>
          {persona && <p className="mt-phi-1 font-medium text-ink-primary">{persona}</p>}
          {job && <p className="mt-phi-1 text-ink-secondary">{job}</p>}
        </div>
      )}

      {isGenerating ? (
        <div className="py-phi-5 text-center">
          <Loader2 className="mx-auto h-5 w-5 animate-spin text-accent" strokeWidth={1.5} />
          <p className="mt-phi-3 text-phi-sm font-medium text-ink-primary">
            Generating audio overview
          </p>
          <p className="mt-phi-1 text-phi-xs text-ink-muted">
            Synthesizing narration for page {currentPage}
          </p>
        </div>
      ) : error ? (
        <div className="rounded-phi-md border border-semantic-negative/25 bg-semantic-negativeBg p-phi-4 text-center">
          <p className="text-phi-sm font-medium text-semantic-negative">Generation failed</p>
          <p className="mt-phi-1 text-phi-xs text-ink-secondary">{error}</p>
          <button
            type="button"
            onClick={generatePodcast}
            className="btn-secondary mt-phi-4 h-phi-ctrl-sm text-phi-xs"
          >
            Try again
          </button>
        </div>
      ) : audioUrl ? (
        <div className="space-y-phi-4">
          <audio ref={audioRef} src={audioUrl} preload="metadata" />

          {/* Main Player Card */}
          <div className="rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-paper-50 p-phi-4">
            <div className="flex items-center gap-phi-3">
              <button
                type="button"
                onClick={togglePlayPause}
                className="flex h-phi-6 w-phi-6 shrink-0 items-center justify-center rounded-full bg-ink-primary text-paper-50 transition-colors duration-phi-fast hover:bg-[#2c2a26] active:scale-[0.98]"
                aria-label={isPlaying ? 'Pause' : 'Play'}
              >
                {isPlaying ? (
                  <Pause className="h-4 w-4" strokeWidth={1.5} />
                ) : (
                  <Play className="ml-0.5 h-4 w-4" strokeWidth={1.5} />
                )}
              </button>

              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between text-phi-xs">
                  <span className="font-medium text-ink-primary">
                    {isPlaying ? 'Playing' : 'Ready to play'}
                  </span>
                  <span className="font-mono text-phi-2xs tabular-nums text-ink-muted">
                    {formatTime(currentTime)} / {formatTime(duration)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max={duration || 0}
                  value={currentTime}
                  onChange={handleSeek}
                  aria-label="Audio playback position"
                  className="editorial-slider mt-phi-3 w-full"
                />
              </div>
            </div>

            {/* Volume */}
            <div className="mt-phi-4 flex items-center gap-phi-3 border-t border-[rgba(25,24,22,0.08)] pt-phi-3">
              <Volume2 className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={volume}
                onChange={handleVolumeChange}
                aria-label="Volume"
                className="editorial-slider flex-1"
              />
              <span className="w-phi-6 text-right font-mono text-phi-2xs tabular-nums text-ink-muted">
                {Math.round(volume * 100)}%
              </span>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-phi-3">
            <button
              type="button"
              onClick={downloadAudio}
              className="btn-secondary h-phi-ctrl-sm flex-1 text-phi-xs"
            >
              <Download className="h-4 w-4 text-ink-muted" strokeWidth={1.5} />
              Download {audioExtension.toUpperCase()}
            </button>
            <button
              type="button"
              onClick={() => {
                if (audioRef.current) {
                  audioRef.current.currentTime = 0;
                  setCurrentTime(0);
                  if (isPlaying) {
                    audioRef.current.play();
                  }
                }
              }}
              className="btn-secondary h-phi-ctrl-sm w-phi-ctrl-sm p-0"
              title="Restart"
              aria-label="Restart audio"
            >
              <RotateCcw className="h-4 w-4 text-ink-muted" strokeWidth={1.5} />
            </button>
          </div>

          {/* Shortcuts */}
          <div className="flex flex-wrap items-center justify-center gap-phi-4 border-t border-[rgba(25,24,22,0.08)] pt-phi-3 text-phi-xs text-ink-muted">
            <span className="inline-flex items-center gap-phi-2">
              <kbd className="keycap">Space</kbd> Play/pause
            </span>
            <span className="inline-flex items-center gap-phi-2">
              <kbd className="keycap">←</kbd> -10s
            </span>
            <span className="inline-flex items-center gap-phi-2">
              <kbd className="keycap">→</kbd> +10s
            </span>
          </div>
        </div>
      ) : null}
    </>
  );

  if (variant === 'docked') {
    return (
      <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-app-surface">
        {!hideHeader && (
          <div className="flex h-phi-bar shrink-0 items-center justify-between border-b border-[rgba(25,24,22,0.08)] bg-paper-50 px-phi-4">
            <div className="flex items-center gap-phi-2">
              <Headphones className="h-4 w-4 text-accent" strokeWidth={1.5} />
              <h3 className="text-phi-sm font-medium text-ink-primary">Audio overview</h3>
              <span className="font-mono text-phi-2xs tabular-nums text-ink-muted">
                p. {currentPage}
              </span>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
              aria-label="Close audio overview"
            >
              <X className="h-4 w-4" strokeWidth={1.5} />
            </button>
          </div>
        )}
        <div className="min-h-0 flex-1 space-y-phi-4 overflow-y-auto p-phi-4 scrollbar-thin">
          {contentBody}
        </div>
      </div>
    );
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Audio overview"
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-primary/35 p-phi-4 backdrop-blur-[2px]"
    >
      <div className="w-full max-w-phi-modal-sm overflow-hidden rounded-phi-lg border border-[rgba(25,24,22,0.12)] bg-app-surface shadow-float">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[rgba(25,24,22,0.08)] px-phi-5 py-phi-4">
          <div className="flex items-center gap-phi-3">
            <Headphones className="h-4 w-4 text-accent" strokeWidth={1.5} />
            <div>
              <h2 className="font-serif text-phi-lg font-normal text-ink-primary">Audio overview</h2>
              <p className="font-mono text-phi-2xs tabular-nums text-ink-muted">
                Page {currentPage} briefing
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-phi-sm p-phi-2 text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
            aria-label="Close audio overview"
          >
            <X className="h-4 w-4" strokeWidth={1.5} />
          </button>
        </div>

        <div className="space-y-phi-5 p-phi-5">
          {contentBody}
        </div>
      </div>
    </div>
  );
};

export default PodcastModal;
