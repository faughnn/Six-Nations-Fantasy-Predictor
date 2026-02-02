import type { MatchData } from '../../types';
import { CountryFlag } from '../common/CountryFlag';

interface MatchCardProps {
  match: MatchData;
}

export function MatchCard({ match }: MatchCardProps) {
  const formattedDate = new Date(match.match_date).toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  return (
    <div className="card">
      {/* Teams header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <CountryFlag country={match.home_team} size="lg" />
          <span className="font-bold text-lg">{match.home_team}</span>
        </div>
        <span className="text-gray-400 font-semibold text-sm">vs</span>
        <div className="flex items-center gap-2">
          <span className="font-bold text-lg">{match.away_team}</span>
          <CountryFlag country={match.away_team} size="lg" />
        </div>
      </div>

      <div className="text-center text-sm text-gray-500 mb-4">{formattedDate}</div>

      {/* Betting lines */}
      <div className="grid grid-cols-2 gap-3 mt-4">
        {match.handicap_line != null && (
          <div className="bg-gray-50 rounded-lg p-2 text-center">
            <div className="text-xs text-gray-500 mb-1">Handicap</div>
            <div className="font-semibold text-sm">
              {match.home_team.split(' ')[0]} {match.handicap_line > 0 ? '+' : ''}{match.handicap_line}
            </div>
            {match.home_handicap_odds != null && match.away_handicap_odds != null && (
              <div className="text-xs text-gray-500 mt-0.5">
                {match.home_handicap_odds.toFixed(2)} / {match.away_handicap_odds.toFixed(2)}
              </div>
            )}
          </div>
        )}
        {match.over_under_line != null && (
          <div className="bg-gray-50 rounded-lg p-2 text-center">
            <div className="text-xs text-gray-500 mb-1">Total Points</div>
            <div className="font-semibold text-sm">O/U {match.over_under_line}</div>
            {match.over_odds != null && match.under_odds != null && (
              <div className="text-xs text-gray-500 mt-0.5">
                {match.over_odds.toFixed(2)} / {match.under_odds.toFixed(2)}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Top try scorers */}
      {match.top_try_scorers.length > 0 && (
        <div className="mt-4">
          <div className="text-xs text-gray-500 font-medium mb-2">Top Try Threats</div>
          <div className="space-y-1">
            {match.top_try_scorers.map((scorer) => (
              <div key={scorer.player_id} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-1.5">
                  <CountryFlag country={scorer.country} size="sm" />
                  <span>{scorer.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">{scorer.odds.toFixed(2)}</span>
                  <span className="font-medium text-green-600">
                    {(scorer.implied_prob * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
