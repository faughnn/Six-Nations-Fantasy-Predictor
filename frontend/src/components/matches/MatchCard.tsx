import { useState, useEffect } from 'react';
import type { MatchData } from '../../types';
import { CountryFlag } from '../common/CountryFlag';

// 2026 Six Nations kickoff times (UTC) — keyed by team pairing (sorted alphabetically)
// Times sourced from sixnationsrugby.com. All GMT (= UTC during winter).
const KICKOFF_TIMES: Record<string, string> = {
  // Round 1 — 5/7 Feb
  'France vs Ireland':    '2026-02-05T21:10:00Z',
  'Italy vs Scotland':    '2026-02-07T15:10:00Z',
  'England vs Wales':     '2026-02-07T16:40:00Z',
  // Round 2 — 14/15 Feb
  'Ireland vs Italy':     '2026-02-14T14:10:00Z',
  'England vs Scotland':  '2026-02-14T16:40:00Z',
  'France vs Wales':      '2026-02-15T15:10:00Z',
  // Round 3 — 21/22 Feb
  'England vs Ireland':   '2026-02-21T14:10:00Z',
  'Scotland vs Wales':    '2026-02-21T16:40:00Z',
  'France vs Italy':      '2026-02-22T15:10:00Z',
  // Round 4 — 6/7 Mar
  'Ireland vs Wales':     '2026-03-06T20:10:00Z',
  'France vs Scotland':   '2026-03-07T14:10:00Z',
  'England vs Italy':     '2026-03-07T16:40:00Z',
  // Round 5 — 14 Mar
  'Ireland vs Scotland':  '2026-03-14T14:10:00Z',
  'Italy vs Wales':       '2026-03-14T16:40:00Z',
  'England vs France':    '2026-03-14T20:10:00Z',
};

const TEAM_COLORS: Record<string, string> = {
  England: '#e4002b',
  France: '#002654',
  Ireland: '#009a44',
  Italy: '#009246',
  Scotland: '#003399',
  Wales: '#d4003c',
};

function teamKey(a: string, b: string): string {
  return [a, b].sort().join(' vs ');
}

function getKickoffTime(home: string, away: string): Date | null {
  const iso = KICKOFF_TIMES[teamKey(home, away)];
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
  const kickoff = getKickoffTime(match.home_team, match.away_team);
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
    <div className="border-r border-stone-300 last:border-r-0 p-5 transition-colors hover:bg-[#f5f0e8]">
      {/* Team-color stripe */}
      <div className="h-1 -mx-5 -mt-5 mb-4" style={{ background: `linear-gradient(90deg, ${TEAM_COLORS[match.home_team] || '#999'}, ${TEAM_COLORS[match.away_team] || '#999'})` }} />
      {/* Teams header */}
      <div className="flex items-center justify-between mb-3 gap-2">
        <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
          <CountryFlag country={match.home_team} size="lg" />
          <span className="font-black text-lg text-stone-900 truncate" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>{match.home_team}</span>
        </div>
        <span className="text-stone-300 text-xs uppercase tracking-widest shrink-0" style={{ fontFamily: 'Fraunces, Georgia, serif', fontStyle: 'italic' }}>vs</span>
        <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
          <span className="font-black text-lg text-stone-900 truncate" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>{match.away_team}</span>
          <CountryFlag country={match.away_team} size="lg" />
        </div>
      </div>

      {/* Date, time, countdown */}
      <div className="text-center mb-4">
        <div className="text-[11px] uppercase tracking-[1.5px] text-stone-400 font-semibold">
          {formattedDate}{formattedTime ? ` — ${formattedTime}` : ''}
        </div>
        {countdown && (
          <div className={`text-xs font-mono font-semibold mt-0.5 tabular-nums ${
            isLive ? 'text-red-500 animate-pulse' : isFT ? 'text-stone-400' : 'text-[#b91c1c]'
          }`}>
            {isLive ? 'LIVE NOW' : isFT ? 'Full Time' : countdown}
          </div>
        )}
      </div>

      <div className="border-t border-stone-300" />

      {/* Betting lines */}
      <div className="grid grid-cols-2 gap-3 mt-4">
        {match.handicap_line != null && Math.abs(match.handicap_line) <= 40 && (
          <div className="bg-[#f5f0e8] p-2.5 text-center">
            <div className="text-[10px] text-stone-400 uppercase tracking-[1.2px] font-semibold mb-1">Handicap</div>
            <div className="font-mono font-semibold text-sm text-stone-800 tabular-nums">
              {match.home_team.split(' ')[0]} {-match.handicap_line > 0 ? '+' : ''}{-match.handicap_line}
            </div>
            {match.home_handicap_odds != null && match.away_handicap_odds != null && (
              <div className="text-xs text-stone-400 font-mono mt-0.5 tabular-nums">
                {match.home_handicap_odds.toFixed(2)} / {match.away_handicap_odds.toFixed(2)}
              </div>
            )}
          </div>
        )}
        {match.over_under_line != null && (
          <div className="bg-[#f5f0e8] p-2.5 text-center">
            <div className="text-[10px] text-stone-400 uppercase tracking-[1.2px] font-semibold mb-1">Total Points</div>
            <div className="font-mono font-semibold text-sm text-stone-800 tabular-nums">O/U {match.over_under_line}</div>
            {match.over_odds != null && match.under_odds != null && (
              <div className="text-xs text-stone-400 font-mono mt-0.5 tabular-nums">
                {match.over_odds.toFixed(2)} / {match.under_odds.toFixed(2)}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Top try scorers */}
      {match.top_try_scorers.length > 0 && (
        <div className="mt-4">
          <div className="text-[10px] text-stone-400 uppercase tracking-[2px] font-bold mb-2">Top Try Threats</div>
          <div className="space-y-1.5">
            {match.top_try_scorers.map((scorer) => (
              <div key={scorer.player_id} className="flex items-center justify-between text-sm border-b border-dotted border-stone-300 pb-1.5 mb-1.5 last:border-b-0">
                <div className="flex items-center gap-1.5">
                  <CountryFlag country={scorer.country} size="sm" />
                  <span className="text-stone-800 font-medium">{scorer.name}</span>
                </div>
                <div className="flex items-center gap-2 tabular-nums">
                  <span className="text-stone-400 font-mono">{scorer.odds.toFixed(2)}</span>
                  <span className="font-semibold text-green-800 font-mono">
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
