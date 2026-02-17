import { BrowserRouter as Router, Routes, Route, Link, NavLink } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from './hooks/useAuth';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Players from './pages/Players';
import PlayersAllStats from './pages/PlayersAllStats';
import HistoricalStats from './pages/HistoricalStats';
import PlayerProjections from './pages/PlayerProjections';
import Tryscorers from './pages/Tryscorers';

function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  if (!user) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-2 py-1 rounded-md hover:bg-slate-50 transition-colors"
      >
        {user.avatar_url ? (
          <img src={user.avatar_url} alt="" className="w-6 h-6 rounded-full" />
        ) : (
          <div className="w-6 h-6 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-semibold">
            {user.name.charAt(0).toUpperCase()}
          </div>
        )}
        <span className="text-sm text-slate-700 hidden sm:inline">{user.name}</span>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-1 w-48 bg-white rounded-lg border border-slate-200 shadow-lg z-50 py-1">
            <div className="px-3 py-2 border-b border-slate-100">
              <p className="text-sm font-medium text-slate-900 truncate">{user.name}</p>
              <p className="text-xs text-slate-500 truncate">{user.email}</p>
            </div>
            <button
              onClick={() => {
                logout();
                setOpen(false);
              }}
              className="w-full text-left px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            >
              Sign out
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function App() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-slate-400 text-sm">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  return (
    <Router>
      <div className="min-h-screen bg-slate-50">
        <nav className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-card">
          <div className="max-w-7xl mx-auto px-4">
            <div className="flex items-center justify-between h-14">
              <Link to="/" className="text-lg font-bold text-slate-900">
                <span className="text-primary-600">Fantasy</span> Six Nations
              </Link>
              <div className="flex items-center space-x-1">
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
                <div className="w-px h-6 bg-slate-200 mx-1" />
                <UserMenu />
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
