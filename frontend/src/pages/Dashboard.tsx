import { useState } from 'react';
import { Link } from 'react-router-dom';
import { usePlayers } from '../hooks/usePlayers';
import { useMatches, useCurrentRound, useRoundScrapeStatus } from '../hooks/useMatches';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { CountryFlag } from '../components/common/CountryFlag';
import { MatchCard } from '../components/matches/MatchCard';
import { Tooltip } from '../components/common/Tooltip';

export default function Dashboard() {
  const { data: currentRound, isLoading: roundLoading } = useCurrentRound();
  const [roundOverride, setRoundOverride] = useState<number | null>(null);
  const season = currentRound?.season ?? 0;
  const round = roundOverride ?? currentRound?.round ?? 0;

  const { data: players, isLoading: playersLoading } = usePlayers({ is_available: true, season, round });
  const { data: matches, isLoading: matchesLoading } = useMatches(season, round);
  const { data: scrapeStatus } = useRoundScrapeStatus(season, round);

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
      <div className="card">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-sm text-slate-600">Data Status</h3>
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
                <span className="text-red-400">(not imported)</span>
              )}
            </div>
          </div>
        )}
      </div>

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

      {/* Two-column section: Value Picks + Try Threats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Value Picks */}
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-bold text-slate-800">Top Value Picks</h2>
            <Link to="/players" className="text-primary-600 text-sm hover:underline font-medium">
              View All
            </Link>
          </div>
          {valuePicks.length > 0 ? (
            <table className="w-full">
              <thead>
                <tr className="text-left text-slate-400 text-xs uppercase">
                  <th className="pb-2">Player</th>
                  <th className="pb-2"><Tooltip text="Fantasy position category">Pos</Tooltip></th>
                  <th className="pb-2 text-right"><Tooltip text="Fantasy cost in stars">Price</Tooltip></th>
                  <th className="pb-2 text-right"><Tooltip text="ML-predicted fantasy points">Pred</Tooltip></th>
                  <th className="pb-2 text-right"><Tooltip text="Predicted points per star — higher is better">Value</Tooltip></th>
                </tr>
              </thead>
              <tbody>
                {valuePicks.map((player) => (
                  <tr key={player.id} className="border-t border-slate-100">
                    <td className="py-1.5">
                      <div className="flex items-center gap-1.5">
                        <CountryFlag country={player.country} size="sm" />
                        <Link to={`/players/${player.id}`} className="font-medium text-slate-700 hover:text-primary-600">
                          {player.name}
                        </Link>
                      </div>
                    </td>
                    <td className="py-1.5 text-slate-400 text-sm">{player.fantasy_position}</td>
                    <td className="py-1.5 text-right text-sm tabular-nums">{player.price ?? '-'}</td>
                    <td className="py-1.5 text-right text-sm font-medium text-primary-600 tabular-nums">
                      {player.predicted_points?.toFixed(1) ?? '-'}
                    </td>
                    <td className="py-1.5 text-right text-sm font-semibold text-emerald-600 tabular-nums">
                      {player.value_score?.toFixed(2) ?? '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-slate-400">No value data available yet</p>
          )}
        </div>

        {/* Top Try Threats */}
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-bold text-slate-800">Top Try Threats</h2>
            <Link to="/tryscorers" className="text-primary-600 text-sm hover:underline font-medium">
              View All
            </Link>
          </div>
          {tryThreats.length > 0 ? (
            <table className="w-full">
              <thead>
                <tr className="text-left text-slate-400 text-xs uppercase">
                  <th className="pb-2">Player</th>
                  <th className="pb-2 text-right"><Tooltip text="Bookmaker anytime try scorer odds">Try Odds</Tooltip></th>
                  <th className="pb-2 text-right"><Tooltip text="Implied probability of scoring a try (100 / odds)">Implied %</Tooltip></th>
                </tr>
              </thead>
              <tbody>
                {tryThreats.map((player) => (
                  <tr key={player.id} className="border-t border-slate-100">
                    <td className="py-1.5">
                      <div className="flex items-center gap-1.5">
                        <CountryFlag country={player.country} size="sm" />
                        <Link to={`/players/${player.id}`} className="font-medium text-slate-700 hover:text-primary-600">
                          {player.name}
                        </Link>
                      </div>
                    </td>
                    <td className="py-1.5 text-right text-sm tabular-nums">
                      {player.anytime_try_odds?.toFixed(2) ?? '-'}
                    </td>
                    <td className="py-1.5 text-right text-sm font-semibold text-emerald-600 tabular-nums">
                      {player.anytime_try_odds
                        ? `${(100 / player.anytime_try_odds).toFixed(0)}%`
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-slate-400">No try odds available yet</p>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <Link
          to="/players"
          className="card hover:shadow-card-hover transition-shadow group inline-block"
        >
          <h3 className="font-semibold text-slate-700 group-hover:text-primary-600 transition-colors">
            Browse Players
          </h3>
          <p className="text-sm text-slate-400 mt-1">
            View all available players and their stats
          </p>
        </Link>
      </div>
    </div>
  );
}
