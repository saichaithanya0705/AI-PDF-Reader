import React, { useState, useEffect } from 'react';
import { User, Target, Save, X } from 'lucide-react';

interface PersonaJobFormProps {
  onSubmit: (persona: string, job: string) => void;
  onCancel?: () => void;
  initialPersona?: string;
  initialJob?: string;
  isVisible: boolean;
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

const PersonaJobForm: React.FC<PersonaJobFormProps> = ({
  onSubmit,
  onCancel,
  initialPersona = '',
  initialJob = '',
  isVisible
}) => {
  const [persona, setPersona] = useState(initialPersona);
  const [job, setJob] = useState(initialJob);
  const [customPersona, setCustomPersona] = useState('');
  const [customJob, setCustomJob] = useState('');
  const [useCustomPersona, setUseCustomPersona] = useState(false);
  const [useCustomJob, setUseCustomJob] = useState(false);

  useEffect(() => {
    setPersona(initialPersona);
    setJob(initialJob);
  }, [initialPersona, initialJob]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const finalPersona = useCustomPersona ? customPersona : persona;
    const finalJob = useCustomJob ? customJob : job;
    
    if (finalPersona.trim() && finalJob.trim()) {
      onSubmit(finalPersona.trim(), finalJob.trim());
      
      // Save to localStorage for future use
      localStorage.setItem('lastPersona', finalPersona);
      localStorage.setItem('lastJob', finalJob);
    }
  };

  const loadSavedData = () => {
    const savedPersona = localStorage.getItem('lastPersona');
    const savedJob = localStorage.getItem('lastJob');
    
    if (savedPersona) {
      setPersona(savedPersona);
      setUseCustomPersona(!PREDEFINED_PERSONAS.includes(savedPersona));
      if (!PREDEFINED_PERSONAS.includes(savedPersona)) {
        setCustomPersona(savedPersona);
      }
    }
    
    if (savedJob) {
      setJob(savedJob);
      setUseCustomJob(!SAMPLE_JOBS.includes(savedJob));
      if (!SAMPLE_JOBS.includes(savedJob)) {
        setCustomJob(savedJob);
      }
    }
  };

  useEffect(() => {
    if (isVisible && !initialPersona && !initialJob) {
      loadSavedData();
    }
  }, [isVisible, initialPersona, initialJob]);

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 rounded-xl border border-slate-700 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-r from-cyan-400 to-purple-600 rounded-lg flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Personalize Your Experience</h2>
                <p className="text-slate-400 text-sm">Tell us about yourself and your goals</p>
              </div>
            </div>
            {onCancel && (
              <button
                onClick={onCancel}
                className="p-2 text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Persona Selection */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-3">
                <User className="w-4 h-4 inline mr-2" />
                Who are you? (Persona)
              </label>
              
              {!useCustomPersona ? (
                <div className="space-y-3">
                  <select
                    value={persona}
                    onChange={(e) => setPersona(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-3 text-white focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 outline-none"
                    required
                  >
                    <option value="">Select your role...</option>
                    {PREDEFINED_PERSONAS.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => setUseCustomPersona(true)}
                    className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
                  >
                    + Add custom persona
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <input
                    type="text"
                    value={customPersona}
                    onChange={(e) => setCustomPersona(e.target.value)}
                    placeholder="Enter your custom persona..."
                    className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-3 text-white focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 outline-none"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setUseCustomPersona(false)}
                    className="text-sm text-slate-400 hover:text-slate-300 transition-colors"
                  >
                    ← Choose from predefined personas
                  </button>
                </div>
              )}
            </div>

            {/* Job to be Done */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-3">
                <Target className="w-4 h-4 inline mr-2" />
                What do you want to accomplish? (Job to be Done)
              </label>
              
              {!useCustomJob ? (
                <div className="space-y-3">
                  <select
                    value={job}
                    onChange={(e) => setJob(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-3 text-white focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 outline-none"
                    required
                  >
                    <option value="">Select your goal...</option>
                    {SAMPLE_JOBS.map((j) => (
                      <option key={j} value={j}>{j}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => setUseCustomJob(true)}
                    className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
                  >
                    + Add custom goal
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <textarea
                    value={customJob}
                    onChange={(e) => setCustomJob(e.target.value)}
                    placeholder="Describe what you want to accomplish..."
                    rows={3}
                    className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-3 text-white focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 outline-none resize-none"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setUseCustomJob(false)}
                    className="text-sm text-slate-400 hover:text-slate-300 transition-colors"
                  >
                    ← Choose from predefined goals
                  </button>
                </div>
              )}
            </div>

            {/* Submit Button */}
            <div className="flex gap-3 pt-4">
              <button
                type="submit"
                className="flex-1 bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-600 hover:to-purple-700 text-white font-medium py-3 px-6 rounded-lg transition-all duration-200 flex items-center justify-center gap-2"
              >
                <Save className="w-4 h-4" />
                Save & Continue
              </button>
              {onCancel && (
                <button
                  type="button"
                  onClick={onCancel}
                  className="px-6 py-3 text-slate-400 hover:text-white transition-colors"
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

export default PersonaJobForm;
