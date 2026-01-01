export const mockPlayers = [
  {
    id: 1,
    name: 'Johnny Sexton',
    country: 'Ireland',
    fantasy_position: 'out_half',
    price: 12.5,
    predicted_points: 18.5,
    is_kicker: true,
  },
  {
    id: 2,
    name: 'Antoine Dupont',
    country: 'France',
    fantasy_position: 'scrum_half',
    price: 15.0,
    predicted_points: 22.0,
    is_kicker: false,
  },
  {
    id: 3,
    name: 'Tadhg Furlong',
    country: 'Ireland',
    fantasy_position: 'prop',
    price: 10.0,
    predicted_points: 12.0,
    is_kicker: false,
  },
  {
    id: 4,
    name: 'Maro Itoje',
    country: 'England',
    fantasy_position: 'second_row',
    price: 11.0,
    predicted_points: 14.0,
    is_kicker: false,
  },
];

export const irishPlayers = mockPlayers.filter(p => p.country === 'Ireland');
