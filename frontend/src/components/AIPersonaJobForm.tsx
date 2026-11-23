import React, { useState, useEffect } from 'react';
import { User, Target, X, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';
import { usePDF } from '../context/usePDF';

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
    personas: Array<{ name: string; confidence: number }>;
    jobs: Array<{ name: string; confidence: number }>;
  };
}

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
  'General Reader',
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
  'General understanding and learning',
];

const AIPersonaJobForm: React.FC<AIPersonaJobFormProps> = ({
  onSubmit,
  onCancel,
  initialPersona = '',
  initialJob = '',
  isVisible,
}) => {
  const { classifyUserIntent } = usePDF();

  const [userIntent, setUserIntent] = useState('');
  const [isClassifying, setIsClassifying] = useState(false);
  const [classificationResult, setClassificationResult] = useState<ClassificationResult | null>(null);
  const [selectedPersona, setSelectedPersona] = useState(initialPersona);
  const [selectedJob, setSelectedJob] = useState(initialJob);
  const [useManualSelection, setUseManualSelection] = useState(false);

  useEffect(() => {
    setSelectedPersona(initialPersona);
    setSelectedJob(initialJob);
  }, [initialPersona, initialJob]);

  useEffect(() => {
    if (isVisible && !initialPersona && !initialJob) {
      const savedIntent = localStorage.getItem('lastUserIntent');
      const savedPersona = localStorage.getItem('lastPersona');
      const savedJob = localStorage.getItem('lastJob');

      if (savedIntent) setUserIntent(savedIntent);
      if (savedPersona) setSelectedPersona(savedPersona);
      if (savedJob) setSelectedJob(savedJob);
    }
  }, [isVisible, initialPersona, initialJob]);

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
    } catch {
      setUseManualSelection(true);
    } finally {
      setIsClassifying(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (selectedPersona.trim() && selectedJob.trim()) {
      onSubmit(selectedPersona.trim(), selectedJob.trim());
      localStorage.setItem('lastPersona', selectedPersona);
      localStorage.setItem('lastJob', selectedJob);
      localStorage.setItem('lastUserIntent', userIntent);
    }
  };

  const getConfidenceTone = (confidence: number) => {
    if (confidence >= 0.8) return 'text-semantic-positive';
    if (confidence >= 0.6) return 'text-semantic-warning';
    return 'text-semantic-negative';
  };

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-primary/35 p-phi-4 backdrop-blur-[2px]">
      <div className="max-h-[90vh] w-full max-w-phi-modal-lg overflow-y-auto rounded-phi-lg border border-[rgba(25,24,22,0.12)] bg-app-surface shadow-float">
        <div className="flex items-start justify-between gap-phi-4 border-b border-[rgba(25,24,22,0.08)] px-phi-5 py-phi-4">
          <div>
            <h2 className="font-serif text-phi-lg font-normal text-ink-primary">Reading profile</h2>
            <p className="mt-phi-1 text-phi-sm text-ink-secondary">
              Describe your role and objective so cross-document recommendations stay relevant.
            </p>
          </div>
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="rounded-phi-sm p-phi-2 text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
              aria-label="Close reading profile"
            >
              <X className="h-4 w-4" strokeWidth={1.5} />
            </button>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-phi-5 p-phi-5">
          {/* Mode switch */}
          <div className="inline-flex rounded-phi-md border border-[rgba(25,24,22,0.1)] bg-app-raised p-phi-1 text-phi-xs">
            <button
              type="button"
              onClick={() => setUseManualSelection(false)}
              className={`rounded-phi-sm px-phi-3 py-phi-2 font-medium transition-colors duration-phi-fast ${
                !useManualSelection
                  ? 'bg-app-surface text-ink-primary shadow-subtle'
                  : 'text-ink-secondary hover:text-ink-primary'
              }`}
            >
              Describe intent
            </button>
            <button
              type="button"
              onClick={() => setUseManualSelection(true)}
              className={`rounded-phi-sm px-phi-3 py-phi-2 font-medium transition-colors duration-phi-fast ${
                useManualSelection
                  ? 'bg-app-surface text-ink-primary shadow-subtle'
                  : 'text-ink-secondary hover:text-ink-primary'
              }`}
            >
              Select manually
            </button>
          </div>

          {!useManualSelection ? (
            <div className="space-y-phi-4">
              <div>
                <label className="text-phi-sm font-medium text-ink-primary" htmlFor="reading-intent">
                  What are you working on
                </label>
                <textarea
                  id="reading-intent"
                  value={userIntent}
                  onChange={(e) => setUserIntent(e.target.value)}
                  placeholder="Example: Chemistry student reviewing organic reaction mechanisms for an upcoming exam"
                  rows={3}
                  className="mt-phi-2 w-full resize-none rounded-phi-md border border-[rgba(25,24,22,0.14)] bg-paper-50 px-phi-3 py-phi-3 text-phi-sm text-ink-primary placeholder:text-ink-faint focus:border-ink-primary focus:outline-none focus:ring-2 focus:ring-accent/15"
                />
                <div className="mt-phi-3 flex items-center gap-phi-3">
                  <button
                    type="button"
                    onClick={handleClassifyIntent}
                    disabled={!userIntent.trim() || isClassifying}
                    className="btn-secondary h-phi-ctrl"
                  >
                    {isClassifying ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
                        Inferring profile
                      </>
                    ) : (
                      'Infer persona and goal'
                    )}
                  </button>
                </div>
              </div>

              {classificationResult && (
                <div className="space-y-phi-4 rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-paper-50 p-phi-4">
                  <div className="flex items-center justify-between gap-phi-2">
                    <span className="text-phi-xs font-medium text-ink-muted">Suggested profile</span>
                    <span
                      className={`inline-flex items-center gap-phi-1 font-mono text-phi-xs tabular-nums ${getConfidenceTone(
                        classificationResult.combined_confidence
                      )}`}
                    >
                      {classificationResult.combined_confidence >= 0.8 ? (
                        <CheckCircle2 className="h-3.5 w-3.5" strokeWidth={1.5} />
                      ) : (
                        <AlertTriangle className="h-3.5 w-3.5" strokeWidth={1.5} />
                      )}
                      {Math.round(classificationResult.combined_confidence * 100)}% match
                    </span>
                  </div>

                  <div className="grid gap-phi-4 md:grid-cols-2">
                    <div>
                      <p className="text-phi-xs text-ink-muted">Persona</p>
                      <p className="mt-phi-1 text-phi-sm font-medium text-ink-primary">
                        {classificationResult.persona.name}
                      </p>
                      <p className="mt-phi-1 text-phi-xs leading-phi text-ink-secondary">
                        {classificationResult.persona.reasoning}
                      </p>
                    </div>

                    <div>
                      <p className="text-phi-xs text-ink-muted">Objective</p>
                      <p className="mt-phi-1 text-phi-sm font-medium text-ink-primary">
                        {classificationResult.job.name}
                      </p>
                      <p className="mt-phi-1 text-phi-xs leading-phi text-ink-secondary">
                        {classificationResult.job.reasoning}
                      </p>
                    </div>
                  </div>

                  {classificationResult.suggestions.length > 0 && (
                    <p className="border-t border-[rgba(25,24,22,0.08)] pt-phi-3 text-phi-xs text-ink-secondary">
                      {classificationResult.suggestions[0]}
                    </p>
                  )}

                  {classificationResult.alternatives && (
                    <div className="grid gap-phi-4 border-t border-[rgba(25,24,22,0.08)] pt-phi-3 md:grid-cols-2">
                      <div>
                        <p className="mb-phi-2 text-phi-xs text-ink-muted">Other personas</p>
                        <div className="space-y-phi-1">
                          {classificationResult.alternatives.personas.slice(0, 3).map((alt, idx) => (
                            <button
                              key={idx}
                              type="button"
                              onClick={() => setSelectedPersona(alt.name)}
                              className="flex w-full items-center justify-between rounded-phi-sm px-phi-2 py-phi-1 text-left text-phi-xs text-ink-secondary transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
                            >
                              <span className="truncate">{alt.name}</span>
                              <span className="font-mono tabular-nums text-ink-muted">
                                {Math.round(alt.confidence * 100)}%
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="mb-phi-2 text-phi-xs text-ink-muted">Other objectives</p>
                        <div className="space-y-phi-1">
                          {classificationResult.alternatives.jobs.slice(0, 3).map((alt, idx) => (
                            <button
                              key={idx}
                              type="button"
                              onClick={() => setSelectedJob(alt.name)}
                              className="flex w-full items-center justify-between gap-phi-2 rounded-phi-sm px-phi-2 py-phi-1 text-left text-phi-xs text-ink-secondary transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
                            >
                              <span className="truncate">{alt.name}</span>
                              <span className="shrink-0 font-mono tabular-nums text-ink-muted">
                                {Math.round(alt.confidence * 100)}%
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-phi-4">
              <div>
                <label className="text-phi-sm font-medium text-ink-primary" htmlFor="manual-persona">
                  Role or persona
                </label>
                <select
                  id="manual-persona"
                  value={selectedPersona}
                  onChange={(e) => setSelectedPersona(e.target.value)}
                  className="mt-phi-2 h-phi-ctrl w-full rounded-phi-md border border-[rgba(25,24,22,0.14)] bg-app-surface px-phi-3 text-phi-sm text-ink-primary focus:border-ink-primary focus:outline-none focus:ring-2 focus:ring-accent/15"
                >
                  <option value="">Choose a persona</option>
                  {PREDEFINED_PERSONAS.map((persona) => (
                    <option key={persona} value={persona}>
                      {persona}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-phi-sm font-medium text-ink-primary" htmlFor="manual-job">
                  Reading objective
                </label>
                <select
                  id="manual-job"
                  value={selectedJob}
                  onChange={(e) => setSelectedJob(e.target.value)}
                  className="mt-phi-2 h-phi-ctrl w-full rounded-phi-md border border-[rgba(25,24,22,0.14)] bg-app-surface px-phi-3 text-phi-sm text-ink-primary focus:border-ink-primary focus:outline-none focus:ring-2 focus:ring-accent/15"
                >
                  <option value="">Choose an objective</option>
                  {SAMPLE_JOBS.map((job) => (
                    <option key={job} value={job}>
                      {job}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {(selectedPersona || selectedJob) && (
            <div className="folio-mark rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-paper-50 py-phi-3 pl-phi-4 pr-phi-4">
              <p className="text-phi-xs font-medium text-ink-muted">Active selection</p>
              <div className="mt-phi-2 space-y-phi-2 text-phi-sm">
                <div className="flex items-center gap-phi-2 text-ink-primary">
                  <User className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
                  <span className="font-medium">{selectedPersona || 'Not selected'}</span>
                </div>
                <div className="flex items-center gap-phi-2 text-ink-secondary">
                  <Target className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
                  <span>{selectedJob || 'Not selected'}</span>
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center justify-end gap-phi-3 border-t border-[rgba(25,24,22,0.08)] pt-phi-4">
            {onCancel && (
              <button type="button" onClick={onCancel} className="btn-secondary h-phi-ctrl">
                Cancel
              </button>
            )}
            <button
              type="submit"
              disabled={!selectedPersona || !selectedJob}
              className="btn-primary h-phi-ctrl"
            >
              Save profile
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AIPersonaJobForm;
