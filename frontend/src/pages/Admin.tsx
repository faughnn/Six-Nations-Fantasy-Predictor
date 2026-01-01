import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { scrapeApi, importApi } from '../api/client';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export default function Admin() {
  const queryClient = useQueryClient();
  const [round, setRound] = useState(1);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const { data: scrapeStatus, refetch: refetchStatus } = useQuery({
    queryKey: ['scrapeStatus'],
    queryFn: scrapeApi.getStatus,
    refetchInterval: 5000,
  });

  const scrapeOddsMutation = useMutation({
    mutationFn: () => scrapeApi.scrapeOdds(round),
    onSuccess: () => {
      setMessage({ type: 'success', text: 'Odds scrape started!' });
      refetchStatus();
    },
    onError: () => {
      setMessage({ type: 'error', text: 'Failed to start odds scrape' });
    },
  });

  const scrapePricesMutation = useMutation({
    mutationFn: () => scrapeApi.scrapePrices(round),
    onSuccess: () => {
      setMessage({ type: 'success', text: 'Prices scrape started!' });
      refetchStatus();
    },
    onError: () => {
      setMessage({ type: 'error', text: 'Failed to start prices scrape' });
    },
  });

  const isAnyScraping =
    scrapeOddsMutation.isPending || scrapePricesMutation.isPending;

  const activeJobs = Object.entries(scrapeStatus || {}).filter(
    ([, job]) => job.status === 'started'
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Admin</h1>

      {message && (
        <div
          className={`card ${
            message.type === 'success'
              ? 'bg-green-50 border-green-200'
              : 'bg-red-50 border-red-200'
          } border`}
        >
          <p
            className={
              message.type === 'success' ? 'text-green-600' : 'text-red-600'
            }
          >
            {message.text}
          </p>
        </div>
      )}

      <div className="card">
        <h2 className="text-xl font-bold mb-4">Data Scraping</h2>

        <div className="mb-4">
          <label htmlFor="round" className="label">
            Round
          </label>
          <select
            id="round"
            className="input w-32"
            value={round}
            onChange={(e) => setRound(parseInt(e.target.value))}
          >
            {[1, 2, 3, 4, 5].map((r) => (
              <option key={r} value={r}>
                Round {r}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={() => scrapeOddsMutation.mutate()}
            disabled={isAnyScraping}
            className="btn-primary"
          >
            {scrapeOddsMutation.isPending ? (
              <span className="flex items-center gap-2">
                <LoadingSpinner size="sm" /> Scraping...
              </span>
            ) : (
              'Scrape Odds'
            )}
          </button>

          <button
            onClick={() => scrapePricesMutation.mutate()}
            disabled={isAnyScraping}
            className="btn-primary"
          >
            {scrapePricesMutation.isPending ? (
              <span className="flex items-center gap-2">
                <LoadingSpinner size="sm" /> Scraping...
              </span>
            ) : (
              'Scrape Prices'
            )}
          </button>
        </div>
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-4">Scrape Status</h2>

        {activeJobs.length > 0 ? (
          <div className="space-y-2">
            {activeJobs.map(([jobId, job]) => (
              <div
                key={jobId}
                className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg"
              >
                <span className="font-medium">{jobId}</span>
                <span className="text-yellow-600 flex items-center gap-2">
                  <LoadingSpinner size="sm" />
                  {job.message || 'In progress...'}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No active scraping jobs</p>
        )}
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-4">Manual Data Import</h2>
        <p className="text-gray-500 mb-4">
          Use the API endpoints directly to import data:
        </p>
        <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
          <li>
            <code>POST /api/import/prices</code> - Import player prices
          </li>
          <li>
            <code>POST /api/import/team-selection</code> - Import team selections
          </li>
        </ul>
      </div>

      <div className="card">
        <h2 className="text-xl font-bold mb-4">Prediction Generation</h2>
        <p className="text-gray-500 mb-4">
          Generate predictions for available players:
        </p>
        <button
          onClick={() => {
            fetch(`/api/predictions/generate?round=${round}&season=2025`, {
              method: 'POST',
            })
              .then((res) => res.json())
              .then((data) => {
                setMessage({
                  type: 'success',
                  text: `Generated ${data.predictions_generated} predictions`,
                });
                queryClient.invalidateQueries({ queryKey: ['predictions'] });
              })
              .catch(() => {
                setMessage({ type: 'error', text: 'Failed to generate predictions' });
              });
          }}
          className="btn-primary"
        >
          Generate Predictions for Round {round}
        </button>
      </div>
    </div>
  );
}
