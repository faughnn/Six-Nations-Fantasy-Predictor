import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../hooks/useAuth';
import { useCurrentRound, useRoundScrapeStatus } from '../hooks/useMatches';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import api, { scrapeApi } from '../api/client';
import type { ScrapeResponse } from '../api/client';
import type { MarketStatus, ValidationWarning, ScrapeRunSummary } from '../types';

interface MetricsUser {
  id: number;
  name: string;
  email: string;
  created_at: string | null;
  last_login_at: string | null;
  login_count: number;
  is_admin: boolean;
  auth_method: 'google' | 'email';
}

interface UserMetrics {
  total_users: number;
  active_7d: number;
  active_30d: number;
  new_signups_7d: number;
  users: MetricsUser[];
}

function useUserMetrics() {
  return useQuery<UserMetrics>({
    queryKey: ['adminMetrics'],
    queryFn: async () => {
      const res = await api.get('/api/auth/admin/metrics');
      return res.data;
    },
    refetchInterval: 60_000,
  });
}

type ScrapeState = 'idle' | 'scraping' | 'done' | 'error';

function useScrapeJob() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<ScrapeState>('idle');
  const [message, setMessage] = useState('');
  const [stepLabel, setStepLabel] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [needsLogin, setNeedsLogin] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const initRef = useRef(false);

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
    queryClient.invalidateQueries({ queryKey: ['scrapeHistory'] });
  }, [queryClient]);

  const dismiss = useCallback(() => {
    setStatus('idle');
    setMessage('');
    setStepLabel(null);
    setNeedsLogin(false);
  }, []);

  // Poll an existing job by ID
  const pollJob = useCallback((jobId: string) => {
    const startTime = Date.now();
    const MAX_POLL_MS = 10 * 60 * 1000;

    pollRef.current = setInterval(async () => {
      if (Date.now() - startTime > MAX_POLL_MS) {
        stopPolling();
        setStatus('error');
        setMessage('Scrape timed out');
        setStepLabel(null);
        return;
      }

      try {
        const jobStatus = await scrapeApi.getJobStatus(jobId);
        setMessage(jobStatus.message || 'Scraping...');
        setStepLabel(jobStatus.step_label || null);

        if (jobStatus.status === 'completed') {
          stopPolling();
          setActiveJobId(null);
          setStatus('done');
          setStepLabel(null);
          invalidateAll();
        } else if (jobStatus.status === 'session_expired') {
          stopPolling();
          setActiveJobId(null);
          setStatus('error');
          setStepLabel(null);
          setNeedsLogin(true);
          setMessage(jobStatus.message || 'Session expired — login required');
        } else if (jobStatus.status === 'failed' || jobStatus.status === 'cancelled') {
          stopPolling();
          setActiveJobId(null);
          setStatus('error');
          setStepLabel(null);
          setMessage(jobStatus.message || 'Scrape failed');
        }
      } catch {
        stopPolling();
        setStatus('error');
        setStepLabel(null);
        setMessage('Failed to check scrape status');
      }
    }, 3000);
  }, [stopPolling, invalidateAll]);

  // On mount, check for any active or recently finished jobs
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    scrapeApi.getActiveJobs().then(({ active, latest_finished }) => {
      if (active.length > 0) {
        const job = active[0];
        setStatus('scraping');
        setMessage(job.message || 'Scraping...');
        setActiveJobId(job.job_id);
        pollJob(job.job_id);
      } else if (latest_finished) {
        if (latest_finished.status === 'session_expired') {
          setStatus('error');
          setNeedsLogin(true);
          setMessage(latest_finished.message || 'Session expired — login required');
        } else if (latest_finished.status === 'failed') {
          setStatus('error');
          setMessage(latest_finished.message || 'Last scrape failed');
        } else if (latest_finished.status === 'completed') {
          setStatus('done');
          setMessage(latest_finished.message || 'Last scrape completed');
        }
      }
    }).catch(() => {
      // Ignore — endpoint may not exist on older backends
    });
  }, [pollJob]);

  const startJob = useCallback(async (apiCall: () => Promise<ScrapeResponse>) => {
    setStatus('scraping');
    setMessage('Starting...');
    setStepLabel(null);
    setNeedsLogin(false);

    try {
      const response = await apiCall();

      if (response.status === 'completed') {
        setStatus('done');
        setMessage(response.message || 'Done');
        invalidateAll();
        return;
      }

      if (!response.job_id) {
        setStatus('error');
        setMessage(response.message || 'No job started');
        return;
      }

      setActiveJobId(response.job_id);
      pollJob(response.job_id);
    } catch {
      setStatus('error');
      setMessage('Failed to start scrape');
    }
  }, [pollJob, invalidateAll]);

  const killJob = useCallback(async () => {
    if (!activeJobId) return;
    try {
      await scrapeApi.killJob(activeJobId);
      setMessage('Cancelling...');
    } catch {
      // Ignore — poll will pick up final status
    }
  }, [activeJobId]);

  return { status, message, stepLabel, startJob, dismiss, killJob, activeJobId, needsLogin, isBusy: status === 'scraping' };
}

function ScrapeButton({
  label,
  description,
  onClick,
  disabled,
  variant = 'default',
  size = 'default',
}: {
  label: string;
  description?: string;
  onClick: () => void;
  disabled: boolean;
  variant?: 'default' | 'primary' | 'hero';
  size?: 'default' | 'large';
}) {
  const base = 'border transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-left';
  const sizeClass = size === 'large' ? 'px-4 py-2.5' : 'px-3 py-2';
  const styles = variant === 'hero'
    ? `${base} ${sizeClass} border-stone-900 bg-stone-900 text-white hover:bg-stone-800`
    : variant === 'primary'
    ? `${base} ${sizeClass} border-stone-900 text-stone-900 hover:bg-stone-100 bg-white`
    : `${base} ${sizeClass} border-stone-300 text-stone-600 hover:bg-stone-100 bg-white`;

  return (
    <button onClick={onClick} disabled={disabled} className={styles}>
      <span className="block text-sm font-semibold uppercase tracking-wider">{label}</span>
      {description && (
        <span className={`block text-xs mt-0.5 font-normal normal-case tracking-normal ${
          variant === 'hero' ? 'text-stone-300' : 'text-stone-400'
        }`}>{description}</span>
      )}
    </button>
  );
}

function timeAgo(iso: string | null): string {
  if (!iso) return 'Never';
  // Handle both naive (no tz) and aware (with tz) datetime strings
  const d = new Date(iso);
  const ts = isNaN(d.getTime()) ? new Date(iso + 'Z').getTime() : d.getTime();
  if (isNaN(ts)) return '—';
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return '—';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

function MarketCell({
  market,
  onClick,
  disabled,
}: {
  market: MarketStatus;
  onClick: () => void;
  disabled: boolean;
}) {
  if (market.status === 'missing') {
    return (
      <button
        onClick={onClick}
        disabled={disabled}
        className="w-full text-left px-2 py-1 text-xs text-stone-300 hover:bg-stone-50 transition-colors disabled:cursor-not-allowed"
      >
        — missing
      </button>
    );
  }

  if (market.status === 'warning') {
    return (
      <button
        onClick={onClick}
        disabled={disabled}
        className="w-full text-left px-2 py-1 text-xs text-amber-700 hover:bg-amber-50 transition-colors disabled:cursor-not-allowed"
      >
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-600 mr-1" />
        {timeAgo(market.scraped_at)}
        <span className="text-amber-500 ml-1">(pre-squad)</span>
      </button>
    );
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="w-full text-left px-2 py-1 text-xs text-green-800 hover:bg-green-50 transition-colors disabled:cursor-not-allowed"
    >
      <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-700 mr-1" />
      {timeAgo(market.scraped_at)}
    </button>
  );
}

function WarningActionButton({
  warning,
  season,
  round,
  scrapeJob,
}: {
  warning: ValidationWarning;
  season: number;
  round: number;
  scrapeJob: ReturnType<typeof useScrapeJob>;
}) {
  const action = warning.action;
  if (!action) return null;

  const handleClick = () => {
    if (action === 're_scrape_try_scorer' || action === 're_scrape_try_scorers') {
      scrapeJob.startJob(() => scrapeApi.scrapeMarket(season, round, 'try_scorer'));
    } else if (action === 're_scrape_prices') {
      scrapeJob.startJob(() => scrapeApi.importPrices(season, round));
    } else if (action === 'scrape_missing') {
      scrapeJob.startJob(() => scrapeApi.scrapeMissing(season, round));
    } else if (action === 're_scrape_handicaps') {
      scrapeJob.startJob(() => scrapeApi.scrapeMarket(season, round, 'handicaps'));
    } else if (action === 're_scrape_totals') {
      scrapeJob.startJob(() => scrapeApi.scrapeMarket(season, round, 'totals'));
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={scrapeJob.isBusy}
      className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider border border-amber-400 text-amber-800 bg-amber-50 hover:bg-amber-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
    >
      Re-scrape
    </button>
  );
}

function marketTypeLabel(marketType: string): string {
  const labels: Record<string, string> = {
    handicaps: 'Handicaps',
    totals: 'Totals',
    try_scorer: 'Try Scorers',
    all_match_odds: 'All Match Odds',
    all: 'Scrape All',
    import_prices: 'Fantasy Prices',
    import_prices_login: 'Fantasy Prices (Login)',
    fantasy_stats: 'Fantasy Stats',
    missing: 'Missing Markets',
  };
  return labels[marketType] || marketType;
}

export default function AdminScrape() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data: currentRound, isLoading: roundLoading } = useCurrentRound();
  const [roundOverride, setRoundOverride] = useState<number | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const season = currentRound?.season ?? 0;
  const round = roundOverride ?? currentRound?.round ?? 0;

  const { data: scrapeStatus } = useRoundScrapeStatus(season, round);
  const { data: metrics } = useUserMetrics();
  const scrapeJob = useScrapeJob();

  const { data: scrapeHistory } = useQuery<ScrapeRunSummary[]>({
    queryKey: ['scrapeHistory', season, round],
    queryFn: () => scrapeApi.getHistory(season, round),
    enabled: season > 0 && round > 0 && historyOpen,
    refetchInterval: historyOpen ? 30_000 : false,
  });

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
  const enrichedMatches = scrapeStatus?.enriched_matches || [];
  const warnings = scrapeStatus?.warnings || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-stone-900" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>Administration</h1>
        <p className="text-sm text-stone-400 mt-1 mb-2">
          Scraper controls and user metrics.
        </p>
        <div className="flex items-center gap-3 mt-1">
          <p className="text-stone-400">Round {round} — {season} Six Nations</p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setRoundOverride(Math.max(1, round - 1))}
              disabled={round <= 1}
              className="w-7 h-7 flex items-center justify-center border border-stone-300 text-stone-400 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed text-sm font-bold transition-colors"
            >
              −
            </button>
            <span className="text-sm text-stone-500 w-6 text-center tabular-nums font-medium font-mono">{round}</span>
            <button
              onClick={() => setRoundOverride(Math.min(5, round + 1))}
              disabled={round >= 5}
              className="w-7 h-7 flex items-center justify-center border border-stone-300 text-stone-400 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed text-sm font-bold transition-colors"
            >
              +
            </button>
          </div>
        </div>
      </div>

      {/* Scrape Controls */}
      <div className="border-t-2 border-stone-900 border-b border-stone-300 py-4 px-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-sm text-stone-600">Data Controls</h3>
          {scrapeStatus && (
            <div className="flex items-center gap-2 text-xs">
              <span className={`inline-block w-2 h-2 rounded-full ${missing.length === 0 ? 'bg-green-700' : 'bg-amber-600'}`} />
              <span className="text-stone-400">
                {missing.length === 0
                  ? 'All markets scraped'
                  : `Missing: ${missing.join(', ')}`}
              </span>
            </div>
          )}
        </div>

        {/* Master button */}
        <div className="mb-4">
          <ScrapeButton
            label="Scrape Everything"
            description="Scrape all odds from Oddschecker + player prices &amp; squads from Fantasy site (does not include Round Stats)"
            onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeAll(season, round))}
            disabled={scrapeJob.isBusy}
            variant="hero"
            size="large"
          />
        </div>

        {/* Grouped controls */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Betting Odds */}
          <div>
            <h4 className="text-[10px] font-bold text-stone-400 uppercase tracking-widest mb-2">Betting Odds</h4>
            <p className="text-xs text-stone-400 mb-2">Scrape odds from Oddschecker for predictions</p>
            <div className="flex flex-col gap-1.5">
              <ScrapeButton
                label="Scrape Missing"
                description="Detect which odds markets are missing per match and only scrape those"
                onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeMissing(season, round))}
                disabled={scrapeJob.isBusy || missing.length === 0}
                variant="primary"
              />
              <ScrapeButton
                label="Refresh All Odds"
                description="Re-scrape all 3 odds markets for every unplayed match, overwriting existing data"
                onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeAllMatchOdds(season, round))}
                disabled={scrapeJob.isBusy}
              />
              <div className="flex gap-1.5">
                <ScrapeButton
                  label="Handicaps"
                  description="Spread lines only"
                  onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeMarket(season, round, 'handicaps'))}
                  disabled={scrapeJob.isBusy}
                />
                <ScrapeButton
                  label="Totals"
                  description="Over/under only"
                  onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeMarket(season, round, 'totals'))}
                  disabled={scrapeJob.isBusy}
                />
                <ScrapeButton
                  label="Try Scorers"
                  description="Player try odds only"
                  onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeMarket(season, round, 'try_scorer'))}
                  disabled={scrapeJob.isBusy}
                />
              </div>
            </div>
          </div>

          {/* Fantasy Game Data */}
          <div>
            <h4 className="text-[10px] font-bold text-stone-400 uppercase tracking-widest mb-2">Fantasy Game Data</h4>
            <p className="text-xs text-stone-400 mb-2">Scrape from the Fantasy Six Nations website</p>
            <div className="flex flex-col gap-1.5">
              {scrapeJob.needsLogin ? (
                <ScrapeButton
                  label="Prices & Squads (Login)"
                  description="Opens a visible browser for login, then scrapes player prices, ownership %, and squad availability from Fantasy Six Nations"
                  onClick={() => scrapeJob.startJob(() => scrapeApi.importPricesLogin(season, round))}
                  disabled={scrapeJob.isBusy}
                  variant="primary"
                />
              ) : (
                <ScrapeButton
                  label="Prices & Squads"
                  description="Scrape player prices, ownership %, and squad availability from Fantasy Six Nations (uses saved session)"
                  onClick={() => scrapeJob.startJob(() => scrapeApi.importPrices(season, round))}
                  disabled={scrapeJob.isBusy}
                />
              )}
              <ScrapeButton
                label="Round Stats"
                description="Scrape per-player game stats (fantasy points, tries, tackles, metres, etc.) from Fantasy Six Nations — feeds the Fantasy Statistics page. Only available after matches are played."
                onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeFantasyStats(season, round))}
                disabled={scrapeJob.isBusy}
              />
            </div>
          </div>

          {/* Info */}
          <div>
            <h4 className="text-[10px] font-bold text-stone-400 uppercase tracking-widest mb-2">Notes</h4>
            <ul className="text-xs text-stone-400 space-y-1.5 list-disc list-inside">
              <li><strong className="text-stone-500">Scrape Everything</strong> runs odds + prices/squads only — Round Stats must be run separately</li>
              <li><strong className="text-stone-500">Odds</strong> are scraped from Oddschecker — no login needed</li>
              <li><strong className="text-stone-500">Prices & Round Stats</strong> are scraped from the Fantasy Six Nations website — both need a saved browser session</li>
              <li>If a session expires, a copyable prompt will appear to fix it via Claude</li>
            </ul>
          </div>
        </div>

        {/* Job status banner */}
        {scrapeJob.status !== 'idle' && (
          <div className={`mt-3 px-3 py-2 text-sm flex items-center gap-2 ${
            scrapeJob.status === 'scraping' ? 'bg-blue-50 text-blue-800 border border-blue-200'
              : scrapeJob.status === 'done' ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
            {scrapeJob.status === 'scraping' && (
              <svg className="animate-spin h-3.5 w-3.5 flex-shrink-0" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            <span className="flex-1">
              {scrapeJob.message}
              {scrapeJob.status === 'scraping' && scrapeJob.stepLabel && (
                <span className="ml-2 text-blue-600 font-mono text-xs">
                  [{scrapeJob.stepLabel}]
                </span>
              )}
            </span>
            {scrapeJob.status === 'scraping' && (
              <button
                onClick={scrapeJob.killJob}
                className="px-2 py-0.5 text-xs font-medium bg-red-100 text-red-800 hover:bg-red-200 transition-colors"
              >
                Kill
              </button>
            )}
            {scrapeJob.status !== 'scraping' && (
              <button
                onClick={scrapeJob.dismiss}
                className="text-xs opacity-60 hover:opacity-100 transition-opacity"
              >
                dismiss
              </button>
            )}
          </div>
        )}
        {scrapeJob.needsLogin && scrapeJob.status === 'error' && (
          <div className="mt-2 px-3 py-2 bg-amber-50 border border-amber-200 text-sm">
            <p className="text-amber-800 font-medium mb-1.5">Paste this into Claude Code to fix:</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-xs bg-white border border-amber-300 px-2 py-1.5 text-stone-700 font-mono select-all">
                Run `python capture_session.py` from the `fantasy-six-nations/backend` directory to capture a new Fantasy Six Nations login session. A browser will open for me to log in.
              </code>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(
                    'Run `python capture_session.py` from the `fantasy-six-nations/backend` directory to capture a new Fantasy Six Nations login session. A browser will open for me to log in.'
                  );
                }}
                className="px-2 py-1.5 text-xs font-medium bg-amber-100 text-amber-800 hover:bg-amber-200 border border-amber-300 transition-colors whitespace-nowrap"
              >
                Copy
              </button>
            </div>
          </div>
        )}

        {scrapeJob.status === 'idle' && (
          <p className="mt-3 text-xs text-stone-400">No active scrapes</p>
        )}

        {/* Status Grid */}
        {scrapeStatus && enrichedMatches.length > 0 && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[10px] text-stone-400 uppercase tracking-wider font-bold">
                  <th className="pb-2 pr-4">Match</th>
                  <th className="pb-2 pr-2">Handicaps</th>
                  <th className="pb-2 pr-2">Totals</th>
                  <th className="pb-2 pr-2">Try Scorers</th>
                  <th className="pb-2">Squad</th>
                </tr>
              </thead>
              <tbody>
                {enrichedMatches.map((m) => {
                  const isPlayed = m.is_played;
                  const squadTotal = m.squad_status.total;
                  const squadExpected = m.squad_status.expected;
                  const squadOk = squadTotal >= squadExpected && squadExpected > 0;
                  const squadPartial = squadTotal > 0 && squadTotal < squadExpected;

                  return (
                    <tr key={`${m.home_team}-${m.away_team}`} className={`border-b border-dotted border-stone-200 ${isPlayed ? 'opacity-40' : ''}`}>
                      <td className="py-1.5 pr-4 font-medium text-stone-700 whitespace-nowrap">
                        {m.home_team} v {m.away_team}
                        {isPlayed && (
                          <span className="ml-2 text-[10px] px-1.5 py-0.5 bg-stone-100 text-stone-400 border border-stone-200 font-semibold uppercase tracking-wider">
                            Played
                          </span>
                        )}
                      </td>
                      <td className="py-1.5 pr-2">
                        <MarketCell
                          market={m.handicaps}
                          onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeMatchMarket(season, round, 'handicaps', m.home_team, m.away_team))}
                          disabled={scrapeJob.isBusy || isPlayed}
                        />
                      </td>
                      <td className="py-1.5 pr-2">
                        <MarketCell
                          market={m.totals}
                          onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeMatchMarket(season, round, 'totals', m.home_team, m.away_team))}
                          disabled={scrapeJob.isBusy || isPlayed}
                        />
                      </td>
                      <td className="py-1.5 pr-2">
                        <MarketCell
                          market={m.try_scorer}
                          onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeMatchMarket(season, round, 'try_scorer', m.home_team, m.away_team))}
                          disabled={scrapeJob.isBusy || isPlayed}
                        />
                      </td>
                      <td className="py-1.5">
                        <span className={`text-xs font-mono ${
                          squadOk ? 'text-green-800' : squadPartial ? 'text-amber-700' : 'text-stone-300'
                        }`}>
                          {squadTotal}/{squadExpected}
                          {squadOk && <span className="ml-1">&#10003;</span>}
                          {squadPartial && <span className="ml-1">&#9888;</span>}
                        </span>
                      </td>
                    </tr>
                  );
                })}
                {/* Fantasy Prices row */}
                {scrapeStatus.fantasy_prices && (
                  <tr className="border-b border-dotted border-stone-200">
                    <td className="py-1.5 pr-4 font-medium text-stone-700 whitespace-nowrap" colSpan={1}>
                      Fantasy Prices
                    </td>
                    <td className="py-1.5" colSpan={4}>
                      {scrapeStatus.fantasy_prices.status === 'complete' ? (
                        <span className="text-xs text-green-800">
                          <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-700 mr-1" />
                          {timeAgo(scrapeStatus.fantasy_prices.scraped_at)}
                          {scrapeStatus.fantasy_prices.player_count !== null && (
                            <span className="text-stone-400 ml-2">
                              ({scrapeStatus.fantasy_prices.player_count} players)
                            </span>
                          )}
                        </span>
                      ) : scrapeStatus.fantasy_prices.status === 'missing' ? (
                        <span className="text-xs text-stone-300">— not imported</span>
                      ) : (
                        <span className="text-xs text-stone-300">— n/a</span>
                      )}
                    </td>
                  </tr>
                )}
                {/* Fantasy Stats row */}
                {scrapeStatus.fantasy_stats && (
                  <tr className="border-b border-dotted border-stone-200">
                    <td className="py-1.5 pr-4 font-medium text-stone-700 whitespace-nowrap" colSpan={1}>
                      Fantasy Stats
                    </td>
                    <td className="py-1.5" colSpan={4}>
                      {scrapeStatus.fantasy_stats.status === 'complete' ? (
                        <span className="text-xs text-green-800">
                          <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-700 mr-1" />
                          {timeAgo(scrapeStatus.fantasy_stats.scraped_at)}
                          {scrapeStatus.fantasy_stats.player_count !== null && (
                            <span className="text-stone-400 ml-2">
                              ({scrapeStatus.fantasy_stats.player_count} players)
                            </span>
                          )}
                        </span>
                      ) : scrapeStatus.fantasy_stats.status === 'missing' ? (
                        <span className="text-xs text-stone-300">— not scraped</span>
                      ) : (
                        <span className="text-xs text-stone-300">
                          — n/a
                          {scrapeStatus.fantasy_stats.note && (
                            <span className="ml-1 text-stone-400">({scrapeStatus.fantasy_stats.note})</span>
                          )}
                        </span>
                      )}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Warnings Panel */}
      {scrapeStatus && (
        <div className="border border-stone-300 py-3 px-4">
          {warnings.length === 0 ? (
            <div className="flex items-center gap-2 text-sm text-green-800">
              <span>&#10003;</span>
              <span>All data looks good</span>
            </div>
          ) : (
            <div className="space-y-2">
              <h4 className="text-[10px] uppercase tracking-wider font-bold text-stone-400 mb-2">Warnings</h4>
              {warnings.map((w, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <span className="text-amber-600 flex-shrink-0">&#9888;</span>
                  <span className="flex-1 text-stone-600">{w.message}</span>
                  <WarningActionButton
                    warning={w}
                    season={season}
                    round={round}
                    scrapeJob={scrapeJob}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Scrape History */}
      <div className="border border-stone-300">
        <button
          onClick={() => setHistoryOpen(!historyOpen)}
          className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-stone-600 hover:bg-stone-50 transition-colors"
        >
          <span>Scrape History</span>
          <span className="text-stone-400">{historyOpen ? '\u25B4' : '\u25BE'}</span>
        </button>
        {historyOpen && (
          <div className="border-t border-stone-200 px-4 py-3">
            {!scrapeHistory ? (
              <div className="flex justify-center py-4">
                <LoadingSpinner size="sm" />
              </div>
            ) : scrapeHistory.length === 0 ? (
              <p className="text-xs text-stone-400">No scrape runs recorded for this round.</p>
            ) : (
              <div className="space-y-1.5">
                {scrapeHistory.map((run) => {
                  const isCompleted = run.status === 'completed';
                  const isFailed = run.status === 'failed';
                  const warningCount = run.warnings?.length ?? 0;

                  return (
                    <div
                      key={run.id}
                      className="flex items-center gap-3 text-xs py-1 border-b border-dotted border-stone-200 last:border-0"
                    >
                      <span className="text-stone-400 w-16 text-right font-mono tabular-nums flex-shrink-0">
                        {timeAgo(run.started_at)}
                      </span>
                      <span className={`flex-shrink-0 ${
                        isCompleted ? 'text-green-800' : isFailed ? 'text-red-700' : 'text-stone-400'
                      }`}>
                        {isCompleted ? '\u2713' : isFailed ? '\u2717' : '\u2022'}
                      </span>
                      <span className="font-medium text-stone-700 w-32 flex-shrink-0">
                        {marketTypeLabel(run.market_type)}
                      </span>
                      {run.match_slug && (
                        <span className="text-stone-400 font-mono text-[11px]">
                          {run.match_slug}
                        </span>
                      )}
                      <span className="text-stone-400 font-mono tabular-nums flex-shrink-0">
                        {formatDuration(run.duration_seconds)}
                      </span>
                      {warningCount > 0 && (
                        <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-300">
                          {warningCount} warning{warningCount !== 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* User Metrics */}
      {metrics && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="border border-stone-300 p-4 text-center">
              <p className="text-2xl font-black text-stone-900 font-mono tabular-nums">{metrics.total_users}</p>
              <p className="text-xs text-stone-400 mt-1 uppercase tracking-wider font-semibold">Total Users</p>
            </div>
            <div className="border border-stone-300 p-4 text-center">
              <p className="text-2xl font-black text-green-800 font-mono tabular-nums">{metrics.active_7d}</p>
              <p className="text-xs text-stone-400 mt-1 uppercase tracking-wider font-semibold">Active (7d)</p>
            </div>
            <div className="border border-stone-300 p-4 text-center">
              <p className="text-2xl font-black text-[#b91c1c] font-mono tabular-nums">{metrics.active_30d}</p>
              <p className="text-xs text-stone-400 mt-1 uppercase tracking-wider font-semibold">Active (30d)</p>
            </div>
            <div className="border border-stone-300 p-4 text-center">
              <p className="text-2xl font-black text-amber-800 font-mono tabular-nums">{metrics.new_signups_7d}</p>
              <p className="text-xs text-stone-400 mt-1 uppercase tracking-wider font-semibold">New (7d)</p>
            </div>
          </div>

          <div className="border-t-2 border-stone-900 border-b border-stone-300 py-4 px-4">
            <h3 className="font-semibold text-sm text-stone-600 mb-3">Recent Users</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-stone-400 text-[10px] uppercase tracking-wider font-bold">
                    <th className="pb-2">Name</th>
                    <th className="pb-2">Email</th>
                    <th className="pb-2">Method</th>
                    <th className="pb-2 text-right">Logins</th>
                    <th className="pb-2 text-right">Last Active</th>
                    <th className="pb-2 text-right">Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.users.map((u) => (
                    <tr key={u.id} className="border-b border-dotted border-stone-300">
                      <td className="py-1.5 font-medium text-stone-800">
                        {u.name}
                        {u.is_admin && (
                          <span className="ml-1.5 text-[10px] px-1.5 py-0.5 bg-amber-50 text-amber-800 border border-amber-300 font-semibold">
                            admin
                          </span>
                        )}
                      </td>
                      <td className="py-1.5 text-stone-400">{u.email}</td>
                      <td className="py-1.5">
                        <span className={`text-xs px-1.5 py-0.5 font-medium ${
                          u.auth_method === 'google'
                            ? 'bg-blue-50 text-blue-800'
                            : 'bg-stone-100 text-stone-500'
                        }`}>
                          {u.auth_method}
                        </span>
                      </td>
                      <td className="py-1.5 text-right tabular-nums text-stone-500 font-mono">{u.login_count}</td>
                      <td className="py-1.5 text-right text-stone-400">{timeAgo(u.last_login_at)}</td>
                      <td className="py-1.5 text-right text-stone-400">{timeAgo(u.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
