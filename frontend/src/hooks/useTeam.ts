import { useState, useCallback, useMemo } from 'react';
import type { PlayerSummary, Position, Country } from '../types';

export interface TeamState {
  props: PlayerSummary[];
  hooker: PlayerSummary | null;
  second_row: PlayerSummary[];
  back_row: PlayerSummary[];
  scrum_half: PlayerSummary | null;
  out_half: PlayerSummary | null;
  centres: PlayerSummary[];
  back_3: PlayerSummary[];
  bench: PlayerSummary[];
  captain: PlayerSummary | null;
  super_sub: PlayerSummary | null;
}

const POSITION_LIMITS: Record<Position, number> = {
  prop: 2,
  hooker: 1,
  second_row: 2,
  back_row: 3,
  scrum_half: 1,
  out_half: 1,
  centre: 2,
  back_3: 3,
};

const MAX_PER_COUNTRY = 4;
const BUDGET = 230;
const MAX_BENCH = 3;

export function useTeam() {
  const [team, setTeam] = useState<TeamState>({
    props: [],
    hooker: null,
    second_row: [],
    back_row: [],
    scrum_half: null,
    out_half: null,
    centres: [],
    back_3: [],
    bench: [],
    captain: null,
    super_sub: null,
  });

  const allPlayers = useMemo(() => {
    const players: PlayerSummary[] = [];
    players.push(...team.props);
    if (team.hooker) players.push(team.hooker);
    players.push(...team.second_row);
    players.push(...team.back_row);
    if (team.scrum_half) players.push(team.scrum_half);
    if (team.out_half) players.push(team.out_half);
    players.push(...team.centres);
    players.push(...team.back_3);
    players.push(...team.bench);
    return players;
  }, [team]);

  const totalCost = useMemo(() => {
    return allPlayers.reduce((sum, p) => sum + (p.price || 0), 0);
  }, [allPlayers]);

  const remainingBudget = useMemo(() => BUDGET - totalCost, [totalCost]);

  const countryCount = useMemo(() => {
    const counts: Record<string, number> = {};
    allPlayers.forEach((p) => {
      counts[p.country] = (counts[p.country] || 0) + 1;
    });
    return counts;
  }, [allPlayers]);

  const totalPredictedPoints = useMemo(() => {
    let points = 0;

    // Starting XV
    team.props.forEach((p) => (points += p.predicted_points || 0));
    if (team.hooker) points += team.hooker.predicted_points || 0;
    team.second_row.forEach((p) => (points += p.predicted_points || 0));
    team.back_row.forEach((p) => (points += p.predicted_points || 0));
    if (team.scrum_half) points += team.scrum_half.predicted_points || 0;
    if (team.out_half) points += team.out_half.predicted_points || 0;
    team.centres.forEach((p) => (points += p.predicted_points || 0));
    team.back_3.forEach((p) => (points += p.predicted_points || 0));

    // Bench (0.5x)
    team.bench.forEach((p) => (points += (p.predicted_points || 0) * 0.5));

    // Captain bonus
    if (team.captain) points += team.captain.predicted_points || 0;

    // Super sub bonus (2.5x extra on top of bench 0.5x)
    if (team.super_sub) points += (team.super_sub.predicted_points || 0) * 2.5;

    return points;
  }, [team]);

  const canAddPlayer = useCallback(
    (player: PlayerSummary, toBench = false): { valid: boolean; reason?: string } => {
      // Already in team
      if (allPlayers.some((p) => p.id === player.id)) {
        return { valid: false, reason: 'Player already in team' };
      }

      // Budget check
      if ((player.price || 0) > remainingBudget) {
        return { valid: false, reason: 'Over budget' };
      }

      // Country limit
      const currentCount = countryCount[player.country] || 0;
      if (currentCount >= MAX_PER_COUNTRY) {
        return { valid: false, reason: `Maximum ${MAX_PER_COUNTRY} players from ${player.country}` };
      }

      if (toBench) {
        if (team.bench.length >= MAX_BENCH) {
          return { valid: false, reason: 'Bench is full' };
        }
      } else {
        // Position limit
        const position = player.fantasy_position;
        const limit = POSITION_LIMITS[position];

        let currentPositionCount = 0;
        switch (position) {
          case 'prop':
            currentPositionCount = team.props.length;
            break;
          case 'hooker':
            currentPositionCount = team.hooker ? 1 : 0;
            break;
          case 'second_row':
            currentPositionCount = team.second_row.length;
            break;
          case 'back_row':
            currentPositionCount = team.back_row.length;
            break;
          case 'scrum_half':
            currentPositionCount = team.scrum_half ? 1 : 0;
            break;
          case 'out_half':
            currentPositionCount = team.out_half ? 1 : 0;
            break;
          case 'centre':
            currentPositionCount = team.centres.length;
            break;
          case 'back_3':
            currentPositionCount = team.back_3.length;
            break;
        }

        if (currentPositionCount >= limit) {
          return { valid: false, reason: `Position ${position} is full` };
        }
      }

      return { valid: true };
    },
    [allPlayers, remainingBudget, countryCount, team]
  );

  const addPlayer = useCallback(
    (player: PlayerSummary, toBench = false) => {
      const check = canAddPlayer(player, toBench);
      if (!check.valid) return check;

      setTeam((prev) => {
        if (toBench) {
          return { ...prev, bench: [...prev.bench, player] };
        }

        const position = player.fantasy_position;
        switch (position) {
          case 'prop':
            return { ...prev, props: [...prev.props, player] };
          case 'hooker':
            return { ...prev, hooker: player };
          case 'second_row':
            return { ...prev, second_row: [...prev.second_row, player] };
          case 'back_row':
            return { ...prev, back_row: [...prev.back_row, player] };
          case 'scrum_half':
            return { ...prev, scrum_half: player };
          case 'out_half':
            return { ...prev, out_half: player };
          case 'centre':
            return { ...prev, centres: [...prev.centres, player] };
          case 'back_3':
            return { ...prev, back_3: [...prev.back_3, player] };
          default:
            return prev;
        }
      });

      return { valid: true };
    },
    [canAddPlayer]
  );

  const removePlayer = useCallback((playerId: number) => {
    setTeam((prev) => ({
      ...prev,
      props: prev.props.filter((p) => p.id !== playerId),
      hooker: prev.hooker?.id === playerId ? null : prev.hooker,
      second_row: prev.second_row.filter((p) => p.id !== playerId),
      back_row: prev.back_row.filter((p) => p.id !== playerId),
      scrum_half: prev.scrum_half?.id === playerId ? null : prev.scrum_half,
      out_half: prev.out_half?.id === playerId ? null : prev.out_half,
      centres: prev.centres.filter((p) => p.id !== playerId),
      back_3: prev.back_3.filter((p) => p.id !== playerId),
      bench: prev.bench.filter((p) => p.id !== playerId),
      captain: prev.captain?.id === playerId ? null : prev.captain,
      super_sub: prev.super_sub?.id === playerId ? null : prev.super_sub,
    }));
  }, []);

  const setCaptain = useCallback((player: PlayerSummary) => {
    setTeam((prev) => ({ ...prev, captain: player }));
  }, []);

  const setSuperSub = useCallback((player: PlayerSummary) => {
    if (!team.bench.some((p) => p.id === player.id)) {
      return { valid: false, reason: 'Super sub must be on bench' };
    }
    setTeam((prev) => ({ ...prev, super_sub: player }));
    return { valid: true };
  }, [team.bench]);

  const clearTeam = useCallback(() => {
    setTeam({
      props: [],
      hooker: null,
      second_row: [],
      back_row: [],
      scrum_half: null,
      out_half: null,
      centres: [],
      back_3: [],
      bench: [],
      captain: null,
      super_sub: null,
    });
  }, []);

  return {
    team,
    allPlayers,
    totalCost,
    remainingBudget,
    countryCount,
    totalPredictedPoints,
    canAddPlayer,
    addPlayer,
    removePlayer,
    setCaptain,
    setSuperSub,
    clearTeam,
    setTeam,
  };
}
