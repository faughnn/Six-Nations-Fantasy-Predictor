import { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { usePlayers } from '../hooks/usePlayers';
import { useMatches, useCurrentRound, useRoundScrapeStatus } from '../hooks/useMatches';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { CountryFlag } from '../components/common/CountryFlag';
import { MatchCard } from '../components/matches/MatchCard';
import { scrapeApi } from '../api/client';
import type { ScrapeResponse } from '../api/client';

type ScrapeState = 'idle' | 'scraping' | 'done' | 'error';

function useScrapeJob(season: number, round: number) {
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
        // Immediate completion (e.g. "nothing missing")
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
  const base = 'px-3 py-1.5 text-sm rounded border transition-colors disabled:opacity-50 disabled:cursor-not-allowed';
  const styles = variant === 'primary'
    ? `${base} border-primary-500 text-primary-600 hover:bg-primary-50 font-medium`
    : `${base} border-gray-300 text-gray-600 hover:bg-gray-50`;

  return (
    <button onClick={onClick} disabled={disabled} className={styles}>
      {label}
    </button>
  );
}

export default function Dashboard() {
  const { data: currentRound, isLoading: roundLoading } = useCurrentRound();
  const season = currentRound?.season ?? 0;
  const round = currentRound?.round ?? 0;

  const { data: players, isLoading: playersLoading } = usePlayers({ is_available: true, season, round });
  const { data: matches, isLoading: matchesLoading } = useMatches(season, round);
  const { data: scrapeStatus } = useRoundScrapeStatus(season, round);

  const scrapeJob = useScrapeJob(season, round);

  const isLoading = roundLoading || playersLoading || matchesLoading;

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const availablePlayers = players || [];
  const matchList = matches || [];
  const missing = scrapeStatus?.missing_markets || [];

  const valuePicks = [...availablePlayers]
    .filter((p) => p.value_score != null && p.value_score > 0)
    .sort((a, b) => (b.value_score || 0) - (a.value_score || 0))
    .slice(0, 8);

  const tryThreats = [...availablePlayers]
    .filter((p) => p.anytime_try_odds != null && p.anytime_try_odds > 0)
    .sort((a, b) => (a.anytime_try_odds || 999) - (b.anytime_try_odds || 999))
    .slice(0, 8);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-gray-500">Round {round} Overview — {season} Six Nations</p>
      </div>

      {/* Scrape Controls */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-sm text-gray-700">Data Controls</h3>
          {scrapeStatus && (
            <div className="flex items-center gap-2 text-xs">
              <span className={`inline-block w-2 h-2 rounded-full ${missing.length === 0 ? 'bg-green-500' : 'bg-yellow-500'}`} />
              <span className="text-gray-500">
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
        </div>

        {scrapeJob.status !== 'idle' && (
          <div className={`mt-2 text-sm flex items-center gap-2 ${
            scrapeJob.status === 'scraping' ? 'text-gray-500'
              : scrapeJob.status === 'done' ? 'text-green-600'
              : 'text-red-600'
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
              <div key={`${m.home_team}-${m.away_team}`} className="flex items-center gap-1.5 text-gray-500">
                <span className="font-medium">{m.home_team} v {m.away_team}:</span>
                <span className={m.has_handicap ? 'text-green-600' : 'text-gray-300'}>H</span>
                <span className={m.has_totals ? 'text-green-600' : 'text-gray-300'}>T</span>
                <span className={m.has_try_scorer ? 'text-green-600' : 'text-gray-300'}>
                  TS{m.has_try_scorer ? `(${m.try_scorer_count})` : ''}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upcoming Matches */}
      <div>
        <h2 className="text-xl font-bold mb-3">Upcoming Matches</h2>
        {matchList.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            {matchList.map((match) => (
              <MatchCard
                key={`${match.home_team}-${match.away_team}`}
                match={match}
              />
            ))}
          </div>
        ) : (
          <div className="card text-center text-gray-500 py-8">
            No match odds available for this round yet — use the scrape controls above
          </div>
        )}
      </div>

      {/* Two-column section: Value Picks + Try Threats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Value Picks */}
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">Top Value Picks</h2>
            <Link to="/players" className="text-primary-600 text-sm hover:underline">
              View All
            </Link>
          </div>
          {valuePicks.length > 0 ? (
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-500 text-xs uppercase">
                  <th className="pb-2">Player</th>
                  <th className="pb-2">Pos</th>
                  <th className="pb-2 text-right">Price</th>
                  <th className="pb-2 text-right">Pred</th>
                  <th className="pb-2 text-right">Value</th>
                </tr>
              </thead>
              <tbody>
                {valuePicks.map((player) => (
                  <tr key={player.id} className="border-t">
                    <td className="py-1.5">
                      <div className="flex items-center gap-1.5">
                        <CountryFlag country={player.country} size="sm" />
                        <Link to={`/players/${player.id}`} className="font-medium hover:text-primary-600">
                          {player.name}
                        </Link>
                      </div>
                    </td>
                    <td className="py-1.5 text-gray-500 text-sm">{player.fantasy_position}</td>
                    <td className="py-1.5 text-right text-sm">{player.price ?? '-'}</td>
                    <td className="py-1.5 text-right text-sm font-medium text-primary-600">
                      {player.predicted_points?.toFixed(1) ?? '-'}
                    </td>
                    <td className="py-1.5 text-right text-sm font-semibold text-green-600">
                      {player.value_score?.toFixed(2) ?? '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-gray-500">No value data available yet</p>
          )}
        </div>

        {/* Top Try Threats */}
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">Top Try Threats</h2>
            <Link to="/players" className="text-primary-600 text-sm hover:underline">
              View All
            </Link>
          </div>
          {tryThreats.length > 0 ? (
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-500 text-xs uppercase">
                  <th className="pb-2">Player</th>
                  <th className="pb-2 text-right">Try Odds</th>
                  <th className="pb-2 text-right">Implied %</th>
                </tr>
              </thead>
              <tbody>
                {tryThreats.map((player) => (
                  <tr key={player.id} className="border-t">
                    <td className="py-1.5">
                      <div className="flex items-center gap-1.5">
                        <CountryFlag country={player.country} size="sm" />
                        <Link to={`/players/${player.id}`} className="font-medium hover:text-primary-600">
                          {player.name}
                        </Link>
                      </div>
                    </td>
                    <td className="py-1.5 text-right text-sm">
                      {player.anytime_try_odds?.toFixed(2) ?? '-'}
                    </td>
                    <td className="py-1.5 text-right text-sm font-semibold text-green-600">
                      {player.anytime_try_odds
                        ? `${(100 / player.anytime_try_odds).toFixed(0)}%`
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-gray-500">No try odds available yet</p>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <Link
          to="/players"
          className="card hover:shadow-lg transition-shadow group inline-block"
        >
          <h3 className="font-semibold group-hover:text-primary-600">
            Browse Players
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            View all available players and their stats
          </p>
        </Link>
      </div>
    </div>
  );
}
