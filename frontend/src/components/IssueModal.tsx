import { useState } from 'react';
import { issuesApi } from '../api/client';

interface IssueModalProps {
  open: boolean;
  onClose: () => void;
}

export default function IssueModal({ open, onClose }: IssueModalProps) {
  const [type, setType] = useState<'bug' | 'feature'>('feature');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  if (!open) return null;

  const handleClose = () => {
    setTitle('');
    setDescription('');
    setError('');
    setSuccess(false);
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      await issuesApi.create({ type, title, description });
      setSuccess(true);
    } catch {
      setError('Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-50" onClick={handleClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div
          className="bg-[#faf8f4] shadow-xl border border-stone-300 w-full max-w-md pointer-events-auto"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between px-5 py-4 border-b border-stone-300">
            <h2 className="text-base font-bold text-stone-900" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
              {success ? 'Thanks!' : 'Report a Bug or Request a Feature'}
            </h2>
            <button
              onClick={handleClose}
              className="p-1 rounded-md hover:bg-stone-100 text-stone-400 hover:text-stone-600 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {success ? (
            <div className="px-5 py-8 text-center">
              <div className="w-12 h-12 rounded-full bg-green-50 flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-green-800" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-sm text-stone-700 font-medium">Your submission has been received.</p>
              <p className="text-xs text-stone-500 mt-1">We'll take a look and get back to you.</p>
              <button onClick={handleClose} className="btn-primary mt-5">
                Close
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="px-5 py-4 space-y-4">
              {/* Type selector */}
              <div>
                <label className="label">What would you like to do?</label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setType('feature')}
                    className={`flex-1 px-3 py-2 text-sm font-medium border transition-colors ${
                      type === 'feature'
                        ? 'bg-stone-100 border-stone-900 text-stone-900'
                        : 'bg-white border-stone-300 text-stone-500 hover:bg-stone-100'
                    }`}
                  >
                    Request a Feature
                  </button>
                  <button
                    type="button"
                    onClick={() => setType('bug')}
                    className={`flex-1 px-3 py-2 text-sm font-medium border transition-colors ${
                      type === 'bug'
                        ? 'bg-red-50 border-red-700 text-red-800'
                        : 'bg-white border-stone-300 text-stone-500 hover:bg-stone-100'
                    }`}
                  >
                    Report a Bug
                  </button>
                </div>
              </div>

              {/* Title */}
              <div>
                <label htmlFor="issue-title" className="label">Title</label>
                <input
                  id="issue-title"
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder={type === 'bug' ? 'Brief description of the bug' : 'What feature would you like?'}
                  className="input"
                  required
                  minLength={3}
                  maxLength={200}
                />
              </div>

              {/* Description */}
              <div>
                <label htmlFor="issue-desc" className="label">Description</label>
                <textarea
                  id="issue-desc"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={
                    type === 'bug'
                      ? 'What happened? What did you expect to happen?'
                      : 'Describe the feature and why it would be useful'
                  }
                  className="input min-h-[100px] resize-y"
                  required
                  minLength={10}
                  maxLength={2000}
                />
              </div>

              {error && (
                <p className="text-sm text-red-800">{error}</p>
              )}

              <div className="flex justify-end gap-2 pt-1">
                <button type="button" onClick={handleClose} className="btn-secondary">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || title.length < 3 || description.length < 10}
                  className="btn-primary"
                >
                  {submitting ? 'Submitting...' : 'Submit'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </>
  );
}
