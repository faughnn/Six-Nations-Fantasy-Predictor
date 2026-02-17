import { BrowserRouter as Router, Routes, Route, Link, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Players from './pages/Players';
import PlayersAllStats from './pages/PlayersAllStats';
import HistoricalStats from './pages/HistoricalStats';
import PlayerProjections from './pages/PlayerProjections';
import Tryscorers from './pages/Tryscorers';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-slate-50">
        <nav className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-card">
          <div className="max-w-7xl mx-auto px-4">
            <div className="flex items-center justify-between h-14">
              <Link to="/" className="text-lg font-bold text-slate-900">
                <span className="text-primary-600">Fantasy</span> Six Nations
              </Link>
              <div className="flex space-x-1">
                <NavLink
                  to="/"
                  end
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                    }`
                  }
                >
                  Dashboard
                </NavLink>
                <NavLink
                  to="/players"
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                    }`
                  }
                >
                  Players
                </NavLink>
                <NavLink
                  to="/tryscorers"
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                    }`
                  }
                >
                  Try Scorers
                </NavLink>
                <NavLink
                  to="/players-all-stats"
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                    }`
                  }
                >
                  2025 F6N Stats
                </NavLink>
                <NavLink
                  to="/projections"
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                    }`
                  }
                >
                  Projections
                </NavLink>
                <NavLink
                  to="/historical-stats"
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
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
            <Route path="/tryscorers" element={<div className="max-w-7xl mx-auto px-4 py-6"><Tryscorers /></div>} />
            <Route path="/" element={<div className="max-w-7xl mx-auto px-4 py-6"><Dashboard /></div>} />
            <Route path="/players" element={<div className="max-w-7xl mx-auto px-4 py-6"><Players /></div>} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
