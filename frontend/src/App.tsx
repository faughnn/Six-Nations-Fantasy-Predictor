import { BrowserRouter as Router, Routes, Route, Link, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Players from './pages/Players';
import PlayersAllStats from './pages/PlayersAllStats';
import HistoricalStats from './pages/HistoricalStats';
import PlayerProjections from './pages/PlayerProjections';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-100">
        <nav className="bg-primary-700 text-white shadow-lg">
          <div className="max-w-7xl mx-auto px-4">
            <div className="flex items-center justify-between h-16">
              <Link to="/" className="text-xl font-bold">
                Fantasy Six Nations
              </Link>
              <div className="flex space-x-4">
                <NavLink
                  to="/"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium ${
                      isActive ? 'bg-primary-800' : 'hover:bg-primary-600'
                    }`
                  }
                >
                  Dashboard
                </NavLink>
                <NavLink
                  to="/players"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium ${
                      isActive ? 'bg-primary-800' : 'hover:bg-primary-600'
                    }`
                  }
                >
                  Players
                </NavLink>
                <NavLink
                  to="/players-all-stats"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium ${
                      isActive ? 'bg-primary-800' : 'hover:bg-primary-600'
                    }`
                  }
                >
                  2025 F6N Stats
                </NavLink>
                <NavLink
                  to="/projections"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium ${
                      isActive ? 'bg-primary-800' : 'hover:bg-primary-600'
                    }`
                  }
                >
                  Projections
                </NavLink>
                <NavLink
                  to="/historical-stats"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium ${
                      isActive ? 'bg-primary-800' : 'hover:bg-primary-600'
                    }`
                  }
                >
                  Historical Stats
                </NavLink>
              </div>
            </div>
          </div>
        </nav>

        <main>
          <Routes>
            <Route path="/players-all-stats" element={
              <div className="px-4 py-6">
                <PlayersAllStats />
              </div>
            } />
            <Route path="/projections" element={
              <div className="px-4 py-6">
                <PlayerProjections />
              </div>
            } />
            <Route path="/historical-stats" element={
              <div className="px-4 py-6">
                <HistoricalStats />
              </div>
            } />
            <Route path="/" element={<div className="max-w-7xl mx-auto px-4 py-6"><Dashboard /></div>} />
            <Route path="/players" element={<div className="max-w-7xl mx-auto px-4 py-6"><Players /></div>} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
