import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../hooks/useAuth';
import { useCurrentRound, useRoundScrapeStatus } from '../hooks/useMatches';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { scrapeApi } from '../api/client';
import type { ScrapeResponse } from '../api/client';

type ScrapeState = 'idle' | 'scraping' | 'done' | 'error';

function useScrapeJob() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<ScrapeState>('idle');
  const [message, setMessage] = useState('');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  const invalidateAll = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['matches'] });
    queryClient.invalidateQueries({ queryKey: ['roundScrapeStatus'] });
    queryClient.invalidateQueries({ queryKey: ['players'] });
  }, [queryClient]);

  const startJob = useCallback(async (apiCall: () => Promise<ScrapeResponse>) => {
    setStatus('scraping');
    setMessage('Starting...');

    try {
      const response = await apiCall();

      if (response.status === 'completed') {
        setStatus('done');
        setMessage(response.message || 'Done');
        invalidateAll();
        setTimeout(() => setStatus('idle'), 5000);
        return;
      }

      if (!response.job_id) {
        setStatus('error');
        setMessage(response.message || 'No job started');
        setTimeout(() => setStatus('idle'), 8000);
        return;
      }

      const startTime = Date.now();
      const MAX_POLL_MS = 10 * 60 * 1000;

      pollRef.current = setInterval(async () => {
        if (Date.now() - startTime > MAX_POLL_MS) {
          stopPolling();
          setStatus('error');
          setMessage('Scrape timed out');
          setTimeout(() => setStatus('idle'), 8000);
          return;
        }

        try {
          const jobStatus = await scrapeApi.getJobStatus(response.job_id);
          setMessage(jobStatus.message || 'Scraping...');

          if (jobStatus.status === 'completed') {
            stopPolling();
            setStatus('done');
            invalidateAll();
            setTimeout(() => setStatus('idle'), 5000);
          } else if (jobStatus.status === 'failed') {
            stopPolling();
            setStatus('error');
            setMessage(jobStatus.message || 'Scrape failed');
            setTimeout(() => setStatus('idle'), 8000);
          }
        } catch {
          stopPolling();
          setStatus('error');
          setMessage('Failed to check scrape status');
          setTimeout(() => setStatus('idle'), 8000);
        }
      }, 3000);
    } catch {
      setStatus('error');
      setMessage('Failed to start scrape');
      setTimeout(() => setStatus('idle'), 8000);
    }
  }, [stopPolling, invalidateAll]);

  return { status, message, startJob, isBusy: status === 'scraping' };
}

function ScrapeButton({
  label,
  onClick,
  disabled,
  variant = 'default',
}: {
  label: string;
  onClick: () => void;
  disabled: boolean;
  variant?: 'default' | 'primary';
}) {
  const base = 'px-3 py-1.5 text-sm rounded-lg border transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium';
  const styles = variant === 'primary'
    ? `${base} border-primary-200 text-primary-600 hover:bg-primary-50 bg-white`
    : `${base} border-slate-200 text-slate-600 hover:bg-slate-50 bg-white`;

  return (
    <button onClick={onClick} disabled={disabled} className={styles}>
      {label}
    </button>
  );
}

export default function AdminScrape() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data: currentRound, isLoading: roundLoading } = useCurrentRound();
  const [roundOverride, setRoundOverride] = useState<number | null>(null);
  const season = currentRound?.season ?? 0;
  const round = roundOverride ?? currentRound?.round ?? 0;

  const { data: scrapeStatus } = useRoundScrapeStatus(season, round);
  const scrapeJob = useScrapeJob();

  // Redirect non-admins
  useEffect(() => {
    if (user && !user.is_admin) {
      navigate('/', { replace: true });
    }
  }, [user, navigate]);

  if (!user?.is_admin) {
    return null;
  }

  if (roundLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const missing = scrapeStatus?.missing_markets || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Scraper Controls</h1>
        <p className="text-sm text-slate-400 mt-1 mb-2">
          Admin-only page for triggering data scraping and imports.
        </p>
        <div className="flex items-center gap-3 mt-1">
          <p className="text-slate-400">Round {round} — {season} Six Nations</p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setRoundOverride(Math.max(1, round - 1))}
              disabled={round <= 1}
              className="w-7 h-7 flex items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed text-sm font-bold transition-colors"
            >
              −
            </button>
            <span className="text-sm text-slate-500 w-6 text-center tabular-nums font-medium">{round}</span>
            <button
              onClick={() => setRoundOverride(Math.min(5, round + 1))}
              disabled={round >= 5}
              className="w-7 h-7 flex items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed text-sm font-bold transition-colors"
            >
              +
            </button>
          </div>
        </div>
      </div>

      {/* Scrape Controls */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-sm text-slate-600">Data Controls</h3>
          {scrapeStatus && (
            <div className="flex items-center gap-2 text-xs">
              <span className={`inline-block w-2 h-2 rounded-full ${missing.length === 0 ? 'bg-emerald-500' : 'bg-yellow-500'}`} />
              <span className="text-slate-400">
                {missing.length === 0
                  ? 'All markets scraped'
                  : `Missing: ${missing.join(', ')}`}
              </span>
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          <ScrapeButton
            label="Scrape Missing"
            onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeMissing(season, round))}
            disabled={scrapeJob.isBusy || missing.length === 0}
            variant="primary"
          />
          <ScrapeButton
            label="Handicaps"
            onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeMarket(season, round, 'handicaps'))}
            disabled={scrapeJob.isBusy}
          />
          <ScrapeButton
            label="Totals"
            onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeMarket(season, round, 'totals'))}
            disabled={scrapeJob.isBusy}
          />
          <ScrapeButton
            label="Try Scorers"
            onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeMarket(season, round, 'try_scorer'))}
            disabled={scrapeJob.isBusy}
          />
          <ScrapeButton
            label="Refresh All"
            onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeAllMatchOdds(season, round))}
            disabled={scrapeJob.isBusy}
          />
          <ScrapeButton
            label="Import Prices"
            onClick={() => scrapeJob.startJob(() => scrapeApi.importPrices(season, round))}
            disabled={scrapeJob.isBusy}
          />
        </div>

        {scrapeJob.status !== 'idle' && (
          <div className={`mt-2 text-sm flex items-center gap-2 ${
            scrapeJob.status === 'scraping' ? 'text-slate-400'
              : scrapeJob.status === 'done' ? 'text-emerald-600'
              : 'text-red-500'
          }`}>
            {scrapeJob.status === 'scraping' && (
              <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {scrapeJob.message}
          </div>
        )}

        {/* Per-match status indicators */}
        {scrapeStatus && scrapeStatus.matches.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-3 text-xs">
            {scrapeStatus.matches.map((m) => (
              <div key={`${m.home_team}-${m.away_team}`} className="flex items-center gap-1.5 text-slate-400">
                <span className="font-medium text-slate-500">{m.home_team} v {m.away_team}:</span>
                <span className={m.has_handicap ? 'text-emerald-600' : 'text-slate-300'}>H</span>
                <span className={m.has_totals ? 'text-emerald-600' : 'text-slate-300'}>T</span>
                <span className={m.has_try_scorer ? 'text-emerald-600' : 'text-slate-300'}>
                  TS{m.has_try_scorer ? `(${m.try_scorer_count})` : ''}
                </span>
              </div>
            ))}
            <div className="flex items-center gap-1.5 text-slate-400">
              <span className="font-medium text-slate-500">Prices:</span>
              {scrapeStatus.has_prices ? (
                <span className="text-emerald-600">({scrapeStatus.price_count})</span>
              ) : (
                <span className="text-red-400">(run CLI scraper)</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
