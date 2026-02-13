import { useState, useEffect } from 'react';
import type { MatchData } from '../../types';
import { CountryFlag } from '../common/CountryFlag';

// 2026 Six Nations kickoff times (UTC) — key: "HomeTeam vs AwayTeam|YYYY-MM-DD"
// Times sourced from sixnationsrugby.com. All GMT (= UTC during winter).
const KICKOFF_TIMES: Record<string, string> = {
  // Round 1 — 5/7 Feb
  'France vs Ireland|2026-02-05':    '2026-02-05T21:10:00Z',
  'Italy vs Scotland|2026-02-07':    '2026-02-07T15:10:00Z',
  'England vs Wales|2026-02-07':     '2026-02-07T16:40:00Z',
  // Round 2 — 14/15 Feb
  'Ireland vs Italy|2026-02-14':     '2026-02-14T14:10:00Z',
  'Scotland vs England|2026-02-14':  '2026-02-14T16:40:00Z',
  'Wales vs France|2026-02-15':      '2026-02-15T15:10:00Z',
  // DB may store all round-2 matches as 2026-02-13 — duplicate keys for safety
  'Ireland vs Italy|2026-02-13':     '2026-02-14T14:10:00Z',
  'Scotland vs England|2026-02-13':  '2026-02-14T16:40:00Z',
  'Wales vs France|2026-02-13':      '2026-02-15T15:10:00Z',
  // Round 3 — 21/22 Feb
  'England vs Ireland|2026-02-21':   '2026-02-21T14:10:00Z',
  'Wales vs Scotland|2026-02-21':    '2026-02-21T16:40:00Z',
  'France vs Italy|2026-02-22':      '2026-02-22T15:10:00Z',
  // Round 4 — 6/7 Mar
  'Ireland vs Wales|2026-03-06':     '2026-03-06T20:10:00Z',
  'Scotland vs France|2026-03-07':   '2026-03-07T14:10:00Z',
  'Italy vs England|2026-03-07':     '2026-03-07T16:40:00Z',
  // Round 5 — 14 Mar
  'Ireland vs Scotland|2026-03-14':  '2026-03-14T14:10:00Z',
  'Wales vs Italy|2026-03-14':       '2026-03-14T16:40:00Z',
  'France vs England|2026-03-14':    '2026-03-14T20:10:00Z',
};

function getKickoffTime(home: string, away: string, matchDate: string): Date | null {
  // Try both "Home vs Away" orderings with the match_date from the DB
  const key1 = `${home} vs ${away}|${matchDate}`;
  const key2 = `${away} vs ${home}|${matchDate}`;
  const iso = KICKOFF_TIMES[key1] || KICKOFF_TIMES[key2];
  return iso ? new Date(iso) : null;
}

function formatCountdown(diffMs: number): string {
  if (diffMs <= 0) return 'LIVE';
  const totalSeconds = Math.floor(diffMs / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (days > 0) return `${days}d ${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

function useCountdown(kickoff: Date | null): string | null {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!kickoff) return;
    // Don't tick if match was more than 3 hours ago (over)
    if (Date.now() - kickoff.getTime() > 3 * 3600 * 1000) return;

    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [kickoff]);

  if (!kickoff) return null;
  const diff = kickoff.getTime() - now;
  if (diff < -3 * 3600 * 1000) return 'FT'; // ~3 hours after kickoff
  if (diff <= 0) return 'LIVE';
  return formatCountdown(diff);
}

interface MatchCardProps {
  match: MatchData;
}

export function MatchCard({ match }: MatchCardProps) {
  const kickoff = getKickoffTime(match.home_team, match.away_team, match.match_date);
  const countdown = useCountdown(kickoff);

  const formattedDate = kickoff
    ? kickoff.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })
    : new Date(match.match_date).toLocaleDateString('en-GB', {
        weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
      });

  const formattedTime = kickoff
    ? kickoff.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
    : null;

  const isLive = countdown === 'LIVE';
  const isFT = countdown === 'FT';

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

      {/* Date, time, countdown */}
      <div className="text-center mb-4">
        <div className="text-sm text-gray-500">
          {formattedDate}{formattedTime ? ` — ${formattedTime}` : ''}
        </div>
        {countdown && (
          <div className={`text-xs font-semibold mt-0.5 ${
            isLive ? 'text-red-500 animate-pulse' : isFT ? 'text-gray-400' : 'text-primary-600'
          }`}>
            {isLive ? 'LIVE NOW' : isFT ? 'Full Time' : countdown}
          </div>
        )}
      </div>

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
