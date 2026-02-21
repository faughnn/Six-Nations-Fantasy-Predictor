import { useState } from 'react';
import { useMatches, useCurrentRound, useRoundScrapeStatus } from '../hooks/useMatches';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { MatchCard } from '../components/matches/MatchCard';

function timeAgo(iso: string | null): string {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

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
        const enriched = scrapeStatus?.enriched_matches ?? [];
        const useEnriched = enriched.length > 0;
        const hasPreSquadWarning = scrapeStatus?.warnings?.some(w => w.type === 'pre_squad_odds') ?? false;
        return (
          <div className="border-t-2 border-stone-900 border-b border-stone-300 py-3 px-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-sm text-stone-600">Data Status</h3>
              <div className="flex items-center gap-4">
                {scrapeStatus?.last_scrape_run?.completed_at && (
                  <span className="text-xs text-stone-400">
                    Last updated: {timeAgo(scrapeStatus.last_scrape_run.completed_at)}
                  </span>
                )}
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
            </div>

            {/* Pre-squad odds warning */}
            {hasPreSquadWarning && (
              <div className="mt-2 bg-amber-50 border border-amber-200 text-amber-800 text-xs px-3 py-2">
                Some odds were retrieved before team announcements and may have changed
              </div>
            )}

            {/* Per-match status indicators + warnings */}
            {scrapeStatus && (useEnriched ? enriched.length > 0 : scrapeStatus.matches.length > 0) && (
              <div className="mt-3 flex gap-6">
                {/* Left: per-match pills */}
                <div className="space-y-2 text-xs">
                  {useEnriched ? enriched.map((m) => {
                    const hOk = m.handicaps.status === 'complete';
                    const tOk = m.totals.status === 'complete';
                    const tsOk = m.try_scorer.status === 'complete' || m.try_scorer.status === 'warning';
                    return (
                      <div key={`${m.home_team}-${m.away_team}`} className="flex flex-wrap items-center gap-1.5">
                        <span className="font-medium text-stone-600 w-40">{m.home_team} v {m.away_team}</span>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 font-medium ${hOk ? 'bg-green-50 text-green-800' : 'bg-stone-100 text-stone-400'}`}>
                          <span className={`w-1.5 h-1.5 ${hOk ? 'bg-green-700' : 'bg-stone-300'}`} />
                          H{hOk && m.handicaps.scraped_at ? `: ${timeAgo(m.handicaps.scraped_at)}` : ''}
                        </span>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 font-medium ${tOk ? 'bg-green-50 text-green-800' : 'bg-stone-100 text-stone-400'}`}>
                          <span className={`w-1.5 h-1.5 ${tOk ? 'bg-green-700' : 'bg-stone-300'}`} />
                          T{tOk && m.totals.scraped_at ? `: ${timeAgo(m.totals.scraped_at)}` : ''}
                        </span>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 font-medium ${tsOk ? 'bg-green-50 text-green-800' : 'bg-stone-100 text-stone-400'}`}>
                          <span className={`w-1.5 h-1.5 ${tsOk ? 'bg-green-700' : 'bg-stone-300'}`} />
                          TS{tsOk ? ` (${m.try_scorer_count})` : ''}{tsOk && m.try_scorer.scraped_at ? `: ${timeAgo(m.try_scorer.scraped_at)}` : ''}
                        </span>
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 font-medium bg-stone-50 text-stone-500">
                          Squad: {m.squad_status.total}/{m.squad_status.expected}
                        </span>
                      </div>
                    );
                  }) : scrapeStatus.matches.map((m) => (
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
