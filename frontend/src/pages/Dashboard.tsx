import { useState } from 'react';
import { useMatches, useCurrentRound, useRoundScrapeStatus } from '../hooks/useMatches';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { MatchCard } from '../components/matches/MatchCard';

export default function Dashboard() {
  const { data: currentRound, isLoading: roundLoading } = useCurrentRound();
  const [roundOverride, setRoundOverride] = useState<number | null>(null);
  const season = currentRound?.season ?? 0;
  const round = roundOverride ?? currentRound?.round ?? 0;

  const { data: matches, isLoading: matchesLoading } = useMatches(season, round);
  const { data: scrapeStatus } = useRoundScrapeStatus(season, round);

  const isLoading = roundLoading || matchesLoading;

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const matchList = matches || [];
  const missing = scrapeStatus?.missing_markets || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Dashboard</h1>
        <p className="text-sm text-slate-400 mt-1 mb-2">
          Your command centre for the current round. View upcoming fixtures and spot the best value picks and try threats at a glance.
        </p>
        <div className="flex items-center gap-3 mt-1">
          <p className="text-slate-400">Round {round} Overview — {season} Six Nations</p>
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

      {/* Data Status */}
      {(() => {
        const isComplete = scrapeStatus && missing.length === 0 && scrapeStatus.availability_unknown === 0;
        return (
          <div className="card">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-sm text-slate-600">Data Status</h3>
              {scrapeStatus && (
                <div className="flex items-center gap-2 text-xs">
                  <span className={`inline-block w-2 h-2 rounded-full ${isComplete ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                  <span className="text-slate-400">
                    {isComplete
                      ? 'All data complete'
                      : `Round ${round} data is incomplete — projections will be updated`}
                  </span>
                </div>
              )}
            </div>

            {/* Per-match status indicators + warnings */}
            {scrapeStatus && scrapeStatus.matches.length > 0 && (
              <div className="mt-3 flex gap-6">
                {/* Left: per-match pills */}
                <div className="space-y-2 text-xs">
                  {scrapeStatus.matches.map((m) => (
                    <div key={`${m.home_team}-${m.away_team}`} className="flex flex-wrap items-center gap-1.5">
                      <span className="font-medium text-slate-600 w-40">{m.home_team} v {m.away_team}</span>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium ${m.has_handicap ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-400'}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${m.has_handicap ? 'bg-emerald-500' : 'bg-slate-300'}`} />
                        Handicaps
                      </span>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium ${m.has_totals ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-400'}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${m.has_totals ? 'bg-emerald-500' : 'bg-slate-300'}`} />
                        Totals
                      </span>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium ${m.has_try_scorer ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-400'}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${m.has_try_scorer ? 'bg-emerald-500' : 'bg-slate-300'}`} />
                        Try Scorers{m.has_try_scorer ? ` (${m.try_scorer_count})` : ''}
                      </span>
                    </div>
                  ))}
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium text-slate-600 w-40">Fantasy Prices</span>
                    {scrapeStatus.has_prices ? (
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium ${
                        scrapeStatus.availability_unknown > 0 ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          scrapeStatus.availability_unknown > 0 ? 'bg-amber-500' : 'bg-emerald-500'
                        }`} />
                        Imported ({scrapeStatus.price_count} players)
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium bg-red-50 text-red-600">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                        Not imported
                      </span>
                    )}
                  </div>
                </div>

                {/* Right: warnings */}
                {(scrapeStatus.availability_unknown > 0 || missing.length > 0) && (
                  <div className="ml-auto text-xs text-amber-700 space-y-1.5 text-right max-w-sm">
                    {scrapeStatus.availability_unknown > 0 && (
                      <p>{scrapeStatus.availability_unknown} players missing lineup availability — will be re-scraped once teams are announced</p>
                    )}
                    {scrapeStatus.matches.some(m => !m.has_handicap && (m.home_team === 'Wales' || m.away_team === 'Wales')) && (
                      <p>Wales spread not yet available — will be updated closer to kick-off</p>
                    )}
                    {missing.filter(m => m !== 'prices').length > 0 && (
                      <p>Missing market data: {missing.filter(m => m !== 'prices').join(', ')}</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })()}

      {/* Upcoming Matches */}
      <div>
        <h2 className="text-xl font-bold text-slate-800 mb-3">Upcoming Matches</h2>
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
          <div className="card text-center text-slate-400 py-8">
            No match odds available for this round yet
          </div>
        )}
      </div>

    </div>
  );
}
