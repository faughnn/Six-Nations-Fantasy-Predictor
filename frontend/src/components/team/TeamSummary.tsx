import { getCountryFlag } from '../../utils';

interface TeamSummaryProps {
  totalPredictedPoints: number;
  countryCount: Record<string, number>;
  playerCount: number;
}

const COUNTRIES = ['Ireland', 'England', 'France', 'Wales', 'Scotland', 'Italy'];

export function TeamSummary({
  totalPredictedPoints,
  countryCount,
  playerCount,
}: TeamSummaryProps) {
  return (
    <div className="card">
      <h3 className="font-semibold mb-3">Team Summary</h3>

      <div className="space-y-4">
        <div className="text-center p-3 bg-primary-50 rounded-lg">
          <div className="text-2xl font-bold text-primary-600">
            {totalPredictedPoints.toFixed(1)}
          </div>
          <div className="text-sm text-gray-600">Predicted Points</div>
        </div>

        <div className="text-center p-3 bg-gray-50 rounded-lg" data-testid="team-count">
          <div className="text-xl font-bold">{playerCount} players</div>
          <div className="text-sm text-gray-500">selected</div>
        </div>

        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            Players by Country (max 4)
          </h4>
          <div className="grid grid-cols-2 gap-2">
            {COUNTRIES.map((country) => {
              const count = countryCount[country] || 0;
              const isAtLimit = count >= 4;

              return (
                <div
                  key={country}
                  className={`flex items-center justify-between text-sm p-2 rounded ${
                    isAtLimit ? 'bg-yellow-50 text-yellow-800' : 'bg-gray-50'
                  }`}
                >
                  <span>
                    {getCountryFlag(country)} {country.slice(0, 3)}
                  </span>
                  <span className="font-medium">{count}/4</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
