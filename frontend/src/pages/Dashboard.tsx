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
      {/* Masthead */}
      <div className="masthead">
        <h1 className="masthead-title">Command <span className="italic" style={{ color: '#b91c1c' }}>Centre</span></h1>
        <p className="masthead-subtitle">Analytics & Intelligence</p>
      </div>
      <div className="edition-bar">
        <span>Six Nations Championship {season}</span>
        <span className="font-bold" style={{ color: '#b91c1c' }}>Round {round}</span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setRoundOverride(Math.max(1, round - 1))}
            disabled={round <= 1}
            className="w-6 h-6 flex items-center justify-center border border-stone-300 text-stone-400 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed text-xs font-bold transition-colors"
          >
            −
          </button>
          <span className="font-mono text-sm text-stone-800 tabular-nums">{round}</span>
          <button
            onClick={() => setRoundOverride(Math.min(5, round + 1))}
            disabled={round >= 5}
            className="w-6 h-6 flex items-center justify-center border border-stone-300 text-stone-400 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed text-xs font-bold transition-colors"
          >
            +
          </button>
        </div>
      </div>

      {/* Data Status */}
      {(() => {
        const isComplete = scrapeStatus && missing.length === 0 && scrapeStatus.availability_unknown === 0;
        return (
          <div className="border-t-2 border-stone-900 border-b border-stone-300 py-3 px-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-sm text-stone-600">Data Status</h3>
              {scrapeStatus && (
                <div className="flex items-center gap-2 text-xs">
                  <span className={`inline-block w-2 h-2 ${isComplete ? 'bg-green-700' : 'bg-amber-600'}`} />
                  <span className="text-stone-400">
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
                      <span className="font-medium text-stone-600 w-40">{m.home_team} v {m.away_team}</span>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 font-medium ${m.has_handicap ? 'bg-green-50 text-green-800' : 'bg-stone-100 text-stone-400'}`}>
                        <span className={`w-1.5 h-1.5 ${m.has_handicap ? 'bg-green-700' : 'bg-stone-300'}`} />
                        Handicaps
                      </span>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 font-medium ${m.has_totals ? 'bg-green-50 text-green-800' : 'bg-stone-100 text-stone-400'}`}>
                        <span className={`w-1.5 h-1.5 ${m.has_totals ? 'bg-green-700' : 'bg-stone-300'}`} />
                        Totals
                      </span>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 font-medium ${m.has_try_scorer ? 'bg-green-50 text-green-800' : 'bg-stone-100 text-stone-400'}`}>
                        <span className={`w-1.5 h-1.5 ${m.has_try_scorer ? 'bg-green-700' : 'bg-stone-300'}`} />
                        Try Scorers{m.has_try_scorer ? ` (${m.try_scorer_count})` : ''}
                      </span>
                    </div>
                  ))}
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium text-stone-600 w-40">Fantasy Prices</span>
                    {scrapeStatus.has_prices ? (
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 font-medium ${
                        scrapeStatus.availability_unknown > 0 ? 'bg-amber-50 text-amber-800' : 'bg-green-50 text-green-800'
                      }`}>
                        <span className={`w-1.5 h-1.5 ${
                          scrapeStatus.availability_unknown > 0 ? 'bg-amber-600' : 'bg-green-700'
                        }`} />
                        Imported ({scrapeStatus.price_count} players)
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 font-medium bg-red-50 text-red-800">
                        <span className="w-1.5 h-1.5 bg-red-600" />
                        Not imported
                      </span>
                    )}
                  </div>
                </div>

                {/* Right: warnings */}
                {(scrapeStatus.availability_unknown > 0 || missing.length > 0) && (
                  <div className="ml-auto text-xs text-amber-800 space-y-1.5 text-right max-w-sm">
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
        <h2 className="text-sm font-bold text-stone-400 uppercase tracking-[2px] mb-4" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>This Week's Fixtures</h2>
        {matchList.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 border-t-2 border-stone-900">
            {matchList.map((match) => (
              <MatchCard
                key={`${match.home_team}-${match.away_team}`}
                match={match}
              />
            ))}
          </div>
        ) : (
          <div className="text-center text-stone-400 py-8 border-t-2 border-stone-900">
            No match odds available for this round yet
          </div>
        )}
      </div>

    </div>
  );
}
