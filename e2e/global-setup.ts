import { FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  // Seed database with test data
  const baseURL = 'http://localhost:8000';

  // Create test players
  const players = [
    { name: 'Johnny Sexton', country: 'Ireland', fantasy_position: 'out_half', is_kicker: true },
    { name: 'Antoine Dupont', country: 'France', fantasy_position: 'scrum_half', is_kicker: false },
    { name: 'Tadhg Furlong', country: 'Ireland', fantasy_position: 'prop', is_kicker: false },
    { name: 'Maro Itoje', country: 'England', fantasy_position: 'second_row', is_kicker: false },
    { name: 'Caelan Doris', country: 'Ireland', fantasy_position: 'back_row', is_kicker: false },
    { name: 'Jamison Gibson-Park', country: 'Ireland', fantasy_position: 'scrum_half', is_kicker: false },
    { name: 'Marcus Smith', country: 'England', fantasy_position: 'out_half', is_kicker: true },
    { name: 'Thomas Ramos', country: 'France', fantasy_position: 'back_3', is_kicker: true },
    { name: 'Dan Sheehan', country: 'Ireland', fantasy_position: 'hooker', is_kicker: false },
    { name: 'James Ryan', country: 'Ireland', fantasy_position: 'second_row', is_kicker: false },
    { name: 'Garry Ringrose', country: 'Ireland', fantasy_position: 'centre', is_kicker: false },
    { name: 'Bundee Aki', country: 'Ireland', fantasy_position: 'centre', is_kicker: false },
    { name: 'Hugo Keenan', country: 'Ireland', fantasy_position: 'back_3', is_kicker: false },
    { name: 'Mack Hansen', country: 'Ireland', fantasy_position: 'back_3', is_kicker: false },
    { name: 'Ellis Genge', country: 'England', fantasy_position: 'prop', is_kicker: false },
    { name: 'Jamie George', country: 'England', fantasy_position: 'hooker', is_kicker: false },
    { name: 'Tom Curry', country: 'England', fantasy_position: 'back_row', is_kicker: false },
    { name: 'Romain Ntamack', country: 'France', fantasy_position: 'out_half', is_kicker: true },
    { name: 'Damian Penaud', country: 'France', fantasy_position: 'back_3', is_kicker: false },
    { name: 'Gregory Alldritt', country: 'France', fantasy_position: 'back_row', is_kicker: false },
  ];

  try {
    // Create players
    for (const player of players) {
      await fetch(`${baseURL}/api/players`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(player),
      });
    }

    // Import prices
    const prices = players.map((p, i) => ({
      player_name: p.name,
      price: 10 + Math.random() * 10,
    }));

    await fetch(`${baseURL}/api/import/prices`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ round: 1, season: 2025, prices }),
    });

    // Import team selections (all players available)
    const teamSelections: Record<string, { player_name: string; squad_position: number }[]> = {};
    let pos = 1;
    for (const player of players) {
      if (!teamSelections[player.country]) {
        teamSelections[player.country] = [];
      }
      teamSelections[player.country].push({
        player_name: player.name,
        squad_position: pos++,
      });
    }

    await fetch(`${baseURL}/api/import/team-selection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ round: 1, season: 2025, teams: teamSelections }),
    });

    // Generate predictions
    await fetch(`${baseURL}/api/predictions/generate?round=1&season=2025`, {
      method: 'POST',
    });

    console.log('Database seeded successfully');
  } catch (error) {
    console.error('Failed to seed database:', error);
  }
}

export default globalSetup;
