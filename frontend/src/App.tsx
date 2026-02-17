import { BrowserRouter as Router, Routes, Route, Link, NavLink, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useAuth } from './hooks/useAuth';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import PlayersAllStats from './pages/PlayersAllStats';
import HistoricalStats from './pages/HistoricalStats';
import PlayerProjections from './pages/PlayerProjections';
import Tryscorers from './pages/Tryscorers';
import AdminScrape from './pages/AdminScrape';
import FantasyStats from './pages/FantasyStats';
import IssueModal from './components/IssueModal';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/tryscorers', label: 'Try Scorers' },
  { to: '/fantasy-stats', label: '2026 Stats' },
  { to: '/players-all-stats', label: '2025 F6N Stats' },
  { to: '/projections', label: 'Projections', wip: true },
  { to: '/historical-stats', label: 'Historical Stats', wip: true },
];

function UserMenu({ onAction }: { onAction?: () => void }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  if (!user) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-slate-50 transition-colors"
      >
        {user.avatar_url ? (
          <img src={user.avatar_url} alt="" className="w-7 h-7 rounded-full" />
        ) : (
          <div className="w-7 h-7 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-semibold">
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
                onAction?.();
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

function MobileMenu({ open, onClose, isAdmin }: { open: boolean; onClose: () => void; isAdmin: boolean }) {
  const location = useLocation();

  // Close on route change
  useEffect(() => {
    onClose();
  }, [location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40 md:hidden" onClick={onClose} />
      <div className="fixed top-14 left-0 right-0 bg-white border-b border-slate-200 shadow-lg z-50 md:hidden">
        <div className="px-4 py-3 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `block px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-slate-600 hover:bg-slate-50'
                }`
              }
            >
              {item.label}
              {item.wip && <span className="ml-1.5 text-[10px] px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded-full font-semibold align-middle">WIP</span>}
            </NavLink>
          ))}
          {isAdmin && (
            <NavLink
              to="/admin/scrape"
              className={({ isActive }) =>
                `block px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-amber-50 text-amber-700'
                    : 'text-amber-500 hover:bg-amber-50'
                }`
              }
            >
              Admin
            </NavLink>
          )}
          <div className="border-t border-slate-100 pt-2 mt-2">
            <UserMenu onAction={onClose} />
          </div>
        </div>
      </div>
    </>
  );
}

function App() {
  const { user, isLoading } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [issueModalOpen, setIssueModalOpen] = useState(false);

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
              <Link to="/" className="text-lg font-bold text-slate-900 shrink-0">
                <span className="text-primary-600">Fantasy</span> Six Nations
              </Link>

              {/* Desktop nav */}
              <div className="hidden md:flex items-center space-x-1">
                {NAV_ITEMS.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      `relative px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-primary-50 text-primary-700'
                          : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                      }`
                    }
                  >
                    {item.label}
                    {item.wip && <span className="absolute -top-2 -right-1 text-[9px] px-1 py-px bg-amber-400 text-white rounded-full font-bold leading-tight">WIP</span>}
                  </NavLink>
                ))}
                {user.is_admin && (
                  <NavLink
                    to="/admin/scrape"
                    className={({ isActive }) =>
                      `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-amber-50 text-amber-700'
                          : 'text-amber-500 hover:text-amber-700 hover:bg-amber-50'
                      }`
                    }
                  >
                    Admin
                  </NavLink>
                )}
                <div className="w-px h-6 bg-slate-200 mx-1" />
                <UserMenu />
              </div>

              {/* Mobile hamburger + user avatar */}
              <div className="flex items-center gap-2 md:hidden">
                <UserMenu />
                <button
                  onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                  className="p-2 rounded-lg hover:bg-slate-50 text-slate-600"
                  aria-label="Toggle menu"
                >
                  {mobileMenuOpen ? (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
          </div>
        </nav>

        <MobileMenu open={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} isAdmin={user.is_admin} />

        <main>
          <Routes>
            <Route path="/fantasy-stats" element={
              <div className="px-4 py-6">
                <FantasyStats />
              </div>
            } />
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
            <Route path="/admin/scrape" element={<div className="max-w-7xl mx-auto px-4 py-6"><AdminScrape /></div>} />
            <Route path="/" element={<div className="max-w-7xl mx-auto px-4 py-6"><Dashboard /></div>} />
          </Routes>
        </main>

        <footer className="border-t border-slate-200 bg-white mt-8">
          <div className="max-w-7xl mx-auto px-4 py-4 flex justify-center">
            <button
              onClick={() => setIssueModalOpen(true)}
              className="text-sm text-slate-500 hover:text-primary-600 transition-colors"
            >
              Report a Bug or Request a Feature
            </button>
          </div>
        </footer>

        <IssueModal open={issueModalOpen} onClose={() => setIssueModalOpen(false)} />
      </div>
    </Router>
  );
}

export default App;
