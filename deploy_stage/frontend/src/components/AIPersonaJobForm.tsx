import React, { useState, useEffect } from 'react';
import { User, Target, Save, X, Sparkles, Loader2, Brain, Lightbulb, CheckCircle, AlertTriangle } from 'lucide-react';
import { usePDF } from '../context/PDFContext';

interface AIPersonaJobFormProps {
  onSubmit: (persona: string, job: string) => void;
  onCancel?: () => void;
  initialPersona?: string;
  initialJob?: string;
  isVisible: boolean;
}

interface ClassificationResult {
  persona: {
    name: string;
    confidence: number;
    reasoning: string;
  };
  job: {
    name: string;
    confidence: number;
    reasoning: string;
  };
  combined_confidence: number;
  suggestions: string[];
  alternatives?: {
    personas: Array<{name: string; confidence: number}>;
    jobs: Array<{name: string; confidence: number}>;
  };
}

const AIPersonaJobForm: React.FC<AIPersonaJobFormProps> = ({
  onSubmit,
  onCancel,
  initialPersona = '',
  initialJob = '',
  isVisible
}) => {
  const { classifyUserIntent } = usePDF();
  
  // State for user intent input
  const [userIntent, setUserIntent] = useState('');
  const [isClassifying, setIsClassifying] = useState(false);
  const [classificationResult, setClassificationResult] = useState<ClassificationResult | null>(null);
  
  // State for manual selection (fallback)
  const [selectedPersona, setSelectedPersona] = useState(initialPersona);
  const [selectedJob, setSelectedJob] = useState(initialJob);
  const [useManualSelection, setUseManualSelection] = useState(false);
  
  // Predefined options for manual selection
  const PREDEFINED_PERSONAS = [
    'Undergraduate Chemistry Student',
    'Graduate Research Student', 
    'Travel Planner',
    'HR Professional',
    'Food Contractor',
    'Legal Professional',
    'Medical Professional',
    'Business Analyst',
    'Technical Writer',
    'Financial Analyst',
    'Software Engineer',
    'Data Scientist',
    'Marketing Professional',
    'Project Manager',
    'General Reader'
  ];

  const SAMPLE_JOBS = [
    'Identify key concepts and mechanisms for exam preparation',
    'Extract research methodologies and findings',
    'Plan trip itineraries and budget allocation',
    'Review compliance requirements and procedures',
    'Analyze dietary requirements and menu planning',
    'Review contract terms and legal obligations',
    'Understand diagnosis and treatment protocols',
    'Identify business requirements and processes',
    'Create documentation and user guides',
    'Analyze financial data and trends',
    'Understand technical specifications and APIs',
    'Extract insights from data and research',
    'Develop marketing strategies and campaigns',
    'Track project milestones and deliverables',
    'General understanding and learning'
  ];

  useEffect(() => {
    setSelectedPersona(initialPersona);
    setSelectedJob(initialJob);
  }, [initialPersona, initialJob]);

  const handleClassifyIntent = async () => {
    if (!userIntent.trim()) return;

    setIsClassifying(true);
    try {
      const result = await classifyUserIntent(userIntent);
      
      if (result.status === 'success') {
        setClassificationResult(result.classification);
        setSelectedPersona(result.classification.persona.name);
        setSelectedJob(result.classification.job.name);
      }
    } catch (error) {
      console.error('❌ Classification failed:', error);
      // Fallback to manual selection
      setUseManualSelection(true);
    } finally {
      setIsClassifying(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (selectedPersona.trim() && selectedJob.trim()) {
      onSubmit(selectedPersona.trim(), selectedJob.trim());
      
      // Save to localStorage for future use
      localStorage.setItem('lastPersona', selectedPersona);
      localStorage.setItem('lastJob', selectedJob);
      localStorage.setItem('lastUserIntent', userIntent);
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-400';
    if (confidence >= 0.6) return 'text-yellow-400';
    return 'text-orange-400';
  };

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 0.8) return <CheckCircle className="w-4 h-4" />;
    if (confidence >= 0.6) return <AlertTriangle className="w-4 h-4" />;
    return <AlertTriangle className="w-4 h-4" />;
  };

  const loadSavedData = () => {
    const savedIntent = localStorage.getItem('lastUserIntent');
    const savedPersona = localStorage.getItem('lastPersona');
    const savedJob = localStorage.getItem('lastJob');
    
    if (savedIntent) setUserIntent(savedIntent);
    if (savedPersona) setSelectedPersona(savedPersona);
    if (savedJob) setSelectedJob(savedJob);
  };

  useEffect(() => {
    if (isVisible && !initialPersona && !initialJob) {
      loadSavedData();
    }
  }, [isVisible, initialPersona, initialJob]);

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto border border-slate-700">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-r from-cyan-500 to-purple-600 rounded-lg">
                <Brain className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">AI-Powered Persona & Job Selection</h2>
                <p className="text-sm text-slate-400">Describe your role and what you want to accomplish</p>
              </div>
            </div>
            {onCancel && (
              <button
                onClick={onCancel}
                className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* AI Intent Classification Section */}
            {!useManualSelection && (
              <div className="space-y-4">
                <div className="bg-gradient-to-r from-cyan-500/10 to-purple-600/10 rounded-lg p-4 border border-cyan-500/20">
                  <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="w-5 h-5 text-cyan-400" />
                    <h3 className="text-lg font-semibold text-white">Describe Your Intent</h3>
                  </div>
                  
                  <div className="space-y-3">
                    <textarea
                      value={userIntent}
                      onChange={(e) => setUserIntent(e.target.value)}
                      placeholder="Example: I'm a chemistry student preparing for my organic chemistry exam and need to understand reaction mechanisms..."
                      className="w-full h-24 px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent resize-none"
                    />
                    
                    <div className="flex gap-3">
                      <button
                        type="button"
                        onClick={handleClassifyIntent}
                        disabled={!userIntent.trim() || isClassifying}
                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-600 hover:to-purple-700 disabled:from-slate-600 disabled:to-slate-600 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-all duration-200"
                      >
                        {isClassifying ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Analyzing...
                          </>
                        ) : (
                          <>
                            <Brain className="w-4 h-4" />
                            Analyze Intent
                          </>
                        )}
                      </button>
                      
                      <button
                        type="button"
                        onClick={() => setUseManualSelection(true)}
                        className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                      >
                        Manual Selection
                      </button>
                    </div>
                  </div>
                </div>

                {/* AI Classification Results */}
                {classificationResult && (
                  <div className="space-y-4">
                    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                      <h4 className="flex items-center gap-2 text-lg font-semibold text-white mb-3">
                        <Lightbulb className="w-5 h-5 text-yellow-400" />
                        AI Analysis Results
                      </h4>
                      
                      <div className="grid md:grid-cols-2 gap-4">
                        {/* Persona Result */}
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <User className="w-4 h-4 text-cyan-400" />
                            <span className="text-sm font-medium text-slate-300">Recommended Persona</span>
                            <div className={`flex items-center gap-1 ${getConfidenceColor(classificationResult.persona.confidence)}`}>
                              {getConfidenceIcon(classificationResult.persona.confidence)}
                              <span className="text-xs">{(classificationResult.persona.confidence * 100).toFixed(0)}%</span>
                            </div>
                          </div>
                          <div className="text-white font-medium">{classificationResult.persona.name}</div>
                          <div className="text-xs text-slate-400">{classificationResult.persona.reasoning}</div>
                        </div>

                        {/* Job Result */}
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <Target className="w-4 h-4 text-purple-400" />
                            <span className="text-sm font-medium text-slate-300">Recommended Task</span>
                            <div className={`flex items-center gap-1 ${getConfidenceColor(classificationResult.job.confidence)}`}>
                              {getConfidenceIcon(classificationResult.job.confidence)}
                              <span className="text-xs">{(classificationResult.job.confidence * 100).toFixed(0)}%</span>
                            </div>
                          </div>
                          <div className="text-white font-medium text-sm">{classificationResult.job.name}</div>
                          <div className="text-xs text-slate-400">{classificationResult.job.reasoning}</div>
                        </div>
                      </div>

                      {/* Overall Confidence */}
                      <div className="mt-4 pt-3 border-t border-slate-700">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-slate-300">Overall Confidence</span>
                          <div className={`flex items-center gap-1 ${getConfidenceColor(classificationResult.combined_confidence)}`}>
                            {getConfidenceIcon(classificationResult.combined_confidence)}
                            <span className="text-sm font-medium">{(classificationResult.combined_confidence * 100).toFixed(0)}%</span>
                          </div>
                        </div>

                        {/* Suggestions */}
                        {classificationResult.suggestions.length > 0 && (
                          <div className="mt-2">
                            <div className="text-xs text-slate-400">
                              💡 {classificationResult.suggestions[0]}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Alternative Suggestions */}
                    {classificationResult.alternatives && (
                      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                        <h5 className="text-sm font-medium text-slate-300 mb-3">Alternative Suggestions</h5>
                        <div className="grid md:grid-cols-2 gap-4">
                          <div>
                            <div className="text-xs text-slate-400 mb-2">Other Personas</div>
                            {classificationResult.alternatives.personas.slice(0, 3).map((alt, idx) => (
                              <button
                                key={idx}
                                type="button"
                                onClick={() => setSelectedPersona(alt.name)}
                                className="block w-full text-left text-xs text-slate-300 hover:text-white py-1 px-2 hover:bg-slate-700 rounded transition-colors"
                              >
                                {alt.name} ({(alt.confidence * 100).toFixed(0)}%)
                              </button>
                            ))}
                          </div>
                          <div>
                            <div className="text-xs text-slate-400 mb-2">Other Tasks</div>
                            {classificationResult.alternatives.jobs.slice(0, 3).map((alt, idx) => (
                              <button
                                key={idx}
                                type="button"
                                onClick={() => setSelectedJob(alt.name)}
                                className="block w-full text-left text-xs text-slate-300 hover:text-white py-1 px-2 hover:bg-slate-700 rounded transition-colors"
                              >
                                {alt.name.length > 40 ? alt.name.substring(0, 40) + '...' : alt.name} ({(alt.confidence * 100).toFixed(0)}%)
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Manual Selection Section */}
            {useManualSelection && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-white">Manual Selection</h3>
                  <button
                    type="button"
                    onClick={() => setUseManualSelection(false)}
                    className="text-sm text-cyan-400 hover:text-cyan-300"
                  >
                    Back to AI Analysis
                  </button>
                </div>

                {/* Persona Selection */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                    <User className="w-4 h-4" />
                    Your Role/Persona
                  </label>
                  <select
                    value={selectedPersona}
                    onChange={(e) => setSelectedPersona(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                  >
                    <option value="">Select your persona...</option>
                    {PREDEFINED_PERSONAS.map((persona) => (
                      <option key={persona} value={persona}>{persona}</option>
                    ))}
                  </select>
                </div>

                {/* Job Selection */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                    <Target className="w-4 h-4" />
                    What you want to accomplish
                  </label>
                  <select
                    value={selectedJob}
                    onChange={(e) => setSelectedJob(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
                  >
                    <option value="">Select your objective...</option>
                    {SAMPLE_JOBS.map((job) => (
                      <option key={job} value={job}>{job}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            {/* Final Selection Display */}
            {(selectedPersona || selectedJob) && (
              <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                <h4 className="text-sm font-medium text-slate-300 mb-3">Final Selection</h4>
                <div className="space-y-2">
                  <div className="flex items-start gap-2">
                    <User className="w-4 h-4 text-cyan-400 mt-0.5" />
                    <div>
                      <div className="text-sm font-medium text-white">{selectedPersona || 'Not selected'}</div>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Target className="w-4 h-4 text-purple-400 mt-0.5" />
                    <div>
                      <div className="text-sm text-white">{selectedJob || 'Not selected'}</div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4">
              <button
                type="submit"
                disabled={!selectedPersona || !selectedJob}
                className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-600 hover:to-purple-700 disabled:from-slate-600 disabled:to-slate-600 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-all duration-200 flex-1"
              >
                <Save className="w-4 h-4" />
                Continue with Selection
              </button>
              
              {onCancel && (
                <button
                  type="button"
                  onClick={onCancel}
                  className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-lg transition-colors"
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default AIPersonaJobForm;
