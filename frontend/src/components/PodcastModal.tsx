import React, { useState, useRef, useEffect } from 'react';
import { X, Play, Pause, Volume2, Download, Loader2 } from 'lucide-react';
import { API_URL } from '../config';

interface PodcastModalProps {
  isVisible: boolean;
  onClose: () => void;
  documentId: string;
  currentPage: number;
  persona?: string;
  job?: string;
}

const PodcastModal: React.FC<PodcastModalProps> = ({
  isVisible,
  onClose,
  documentId,
  currentPage,
  persona,
  job
}) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(1);

  const audioRef = useRef<HTMLAudioElement>(null);

  const generatePodcast = async () => {
    setIsGenerating(true);
    setError(null);

    try {
  const response = await fetch(`${API_URL}/api/generate-podcast`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_id: documentId,
          page: currentPage,
          persona: persona,
          job: job
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to generate podcast: ${response.statusText}`);
      }

  const data = await response.json();
  setAudioUrl(`${API_URL}${data.audioUrl}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate podcast');
    } finally {
      setIsGenerating(false);
    }
  };

  const togglePlayPause = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

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
      link.download = `podcast_page_${currentPage}.wav`;
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  useEffect(() => {
    if (isVisible && !audioUrl && !isGenerating) {
      generatePodcast();
    }
  }, [isVisible]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (!isVisible || !audioUrl) return;

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
      audio.addEventListener('timeupdate', handleTimeUpdate);
      audio.addEventListener('loadedmetadata', handleLoadedMetadata);
      audio.addEventListener('ended', () => setIsPlaying(false));

      return () => {
        audio.removeEventListener('timeupdate', handleTimeUpdate);
        audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
        audio.removeEventListener('ended', () => setIsPlaying(false));
      };
    }
  }, [audioUrl, volume]);

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 rounded-xl border border-slate-700 max-w-md w-full">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-r from-purple-400 to-pink-600 rounded-lg flex items-center justify-center">
                <Volume2 className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Podcast Mode</h2>
                <p className="text-slate-400 text-sm">Page {currentPage} Overview</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="space-y-6">
            {/* Persona/Job Info */}
            {(persona || job) && (
              <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                <p className="text-sm text-slate-400 mb-2">Tailored for:</p>
                {persona && (
                  <p className="text-sm text-cyan-400">👤 {persona}</p>
                )}
                {job && (
                  <p className="text-sm text-purple-400">🎯 {job}</p>
                )}
              </div>
            )}

            {/* Audio Player */}
            {isGenerating ? (
              <div className="text-center py-8">
                <Loader2 className="w-12 h-12 text-purple-400 animate-spin mx-auto mb-4" />
                <p className="text-white font-medium">Generating your podcast...</p>
                <p className="text-slate-400 text-sm mt-1">This may take a few moments</p>
              </div>
            ) : error ? (
              <div className="text-center py-8">
                <div className="w-12 h-12 bg-red-400/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <X className="w-6 h-6 text-red-400" />
                </div>
                <p className="text-red-400 font-medium mb-2">Generation Failed</p>
                <p className="text-slate-400 text-sm mb-4">{error}</p>
                <button
                  onClick={generatePodcast}
                  className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
                >
                  Try Again
                </button>
              </div>
            ) : audioUrl ? (
              <div className="space-y-6">
                {/* Audio Element */}
                <audio ref={audioRef} src={audioUrl} preload="metadata" />

                {/* Audio Player Header */}
                <div className="text-center">
                  <h3 className="text-lg font-semibold text-white mb-2">🎧 Your Podcast is Ready!</h3>
                  <p className="text-sm text-slate-400">Listen directly or download for later</p>
                </div>

                {/* Main Audio Player */}
                <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700">
                  {/* Play/Pause Button */}
                  <div className="flex items-center justify-center mb-6">
                    <button
                      onClick={togglePlayPause}
                      className="w-20 h-20 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 rounded-full flex items-center justify-center transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105"
                    >
                      {isPlaying ? (
                        <Pause className="w-10 h-10 text-white" />
                      ) : (
                        <Play className="w-10 h-10 text-white ml-1" />
                      )}
                    </button>
                  </div>

                  {/* Progress Bar */}
                  <div className="space-y-3">
                    <input
                      type="range"
                      min="0"
                      max={duration || 0}
                      value={currentTime}
                      onChange={handleSeek}
                      className="w-full h-3 bg-slate-700 rounded-lg appearance-none cursor-pointer slider"
                    />
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-slate-400">{formatTime(currentTime)}</span>
                      <div className="flex items-center gap-2">
                        <Volume2 className="w-4 h-4 text-purple-400" />
                        <span className="text-slate-300 font-medium">
                          {isPlaying ? 'Playing...' : 'Paused'}
                        </span>
                      </div>
                      <span className="text-slate-400">{formatTime(duration)}</span>
                    </div>

                    {/* Volume Control */}
                    <div className="flex items-center gap-3 mt-3 pt-3 border-t border-slate-700">
                      <Volume2 className="w-4 h-4 text-slate-400" />
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={volume}
                        onChange={handleVolumeChange}
                        className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer slider"
                      />
                      <span className="text-xs text-slate-400 w-8">{Math.round(volume * 100)}%</span>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3">
                  <button
                    onClick={downloadAudio}
                    className="flex-1 flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white px-4 py-3 rounded-lg transition-all duration-200 border border-slate-600 hover:border-slate-500"
                  >
                    <Download className="w-4 h-4" />
                    Download Audio
                  </button>
                  <button
                    onClick={() => {
                      if (audioRef.current) {
                        audioRef.current.currentTime = 0;
                        setCurrentTime(0);
                        if (isPlaying) {
                          audioRef.current.play();
                        }
                      }
                    }}
                    className="px-4 py-3 bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 hover:text-purple-300 rounded-lg transition-all duration-200 border border-purple-600/30"
                    title="Restart from beginning"
                  >
                    ⏮️
                  </button>
                </div>

                {/* Audio Info & Keyboard Shortcuts */}
                <div className="space-y-3">
                  <div className="text-center text-xs text-slate-500 bg-slate-800/30 rounded-lg p-3">
                    <div className="flex items-center justify-center gap-4 text-xs">
                      <div className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                        <span>High-quality AI audio</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
                        <span>Listen in browser</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-purple-400 rounded-full"></span>
                        <span>Download available</span>
                      </div>
                    </div>
                  </div>

                  {/* Keyboard Shortcuts */}
                  <div className="text-center text-xs text-slate-500 bg-slate-800/20 rounded-lg p-2">
                    <div className="flex items-center justify-center gap-4">
                      <span>⌨️ <kbd className="bg-slate-700 px-1 rounded">Space</kbd> Play/Pause</span>
                      <span><kbd className="bg-slate-700 px-1 rounded">←</kbd> -10s</span>
                      <span><kbd className="bg-slate-700 px-1 rounded">→</kbd> +10s</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <style>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          height: 20px;
          width: 20px;
          border-radius: 50%;
          background: linear-gradient(45deg, #a855f7, #ec4899);
          cursor: pointer;
          box-shadow: 0 2px 8px rgba(168, 85, 247, 0.4);
          transition: all 0.2s ease;
        }

        .slider::-webkit-slider-thumb:hover {
          transform: scale(1.1);
          box-shadow: 0 4px 12px rgba(168, 85, 247, 0.6);
        }

        .slider::-moz-range-thumb {
          height: 20px;
          width: 20px;
          border-radius: 50%;
          background: linear-gradient(45deg, #a855f7, #ec4899);
          cursor: pointer;
          border: none;
          box-shadow: 0 2px 8px rgba(168, 85, 247, 0.4);
        }

        .slider::-webkit-slider-track {
          background: #374151;
          border-radius: 6px;
          height: 12px;
        }

        .slider::-moz-range-track {
          background: #374151;
          border-radius: 6px;
          height: 12px;
          border: none;
        }
      `}</style>
    </div>
  );
};

export default PodcastModal;
