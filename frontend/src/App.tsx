import { BrowserRouter as Router, Routes, Route, Link, NavLink, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useAuth } from './hooks/useAuth';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import PlayersAllStats from './pages/PlayersAllStats';
import HistoricalStats from './pages/HistoricalStats';
import Tryscorers from './pages/Tryscorers';
import AdminScrape from './pages/AdminScrape';
import FantasyStats from './pages/FantasyStats';
import IssueModal from './components/IssueModal';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/tryscorers', label: 'Player Analysis' },
  { to: '/fantasy-stats', label: '2026 Stats' },
  { to: '/players-all-stats', label: '2025 F6N Stats' },
  { to: '/historical-stats', label: 'Historical Stats', wip: true },
];

function UserMenu({ onAction, onReportBug }: { onAction?: () => void; onReportBug?: () => void }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  if (!user) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-white/5 transition-colors"
      >
        {user.avatar_url ? (
          <img src={user.avatar_url} alt="" className="w-7 h-7 rounded-full" />
        ) : (
          <div className="w-7 h-7 rounded-full bg-white/10 text-white flex items-center justify-center text-xs font-semibold">
            {user.name.charAt(0).toUpperCase()}
          </div>
        )}
        <span className="text-[11px] text-stone-400 uppercase tracking-wider font-semibold hidden sm:inline">{user.name}</span>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-1 w-48 bg-[#faf8f4] border border-stone-300 shadow-lg z-50 py-1">
            <div className="px-3 py-2 border-b border-stone-200">
              <p className="text-sm font-medium text-stone-900 truncate">{user.name}</p>
              <p className="text-xs text-stone-400 truncate">{user.email}</p>
            </div>
            <button
              onClick={() => {
                setOpen(false);
                onAction?.();
                onReportBug?.();
              }}
              className="w-full text-left px-3 py-2 text-sm text-stone-600 hover:bg-stone-100"
            >
              Report a Bug
            </button>
            <button
              onClick={() => {
                logout();
                setOpen(false);
                onAction?.();
              }}
              className="w-full text-left px-3 py-2 text-sm text-stone-600 hover:bg-stone-100"
            >
              Sign out
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function MobileMenu({ open, onClose, isAdmin, onReportBug }: { open: boolean; onClose: () => void; isAdmin: boolean; onReportBug: () => void }) {
  const location = useLocation();

  // Close on route change
  useEffect(() => {
    onClose();
  }, [location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40 md:hidden" onClick={onClose} />
      <div className="fixed top-14 left-0 right-0 bg-[#1c1917] border-b border-stone-700 shadow-lg z-50 md:hidden">
        <div className="px-4 py-3 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `block px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'text-white bg-white/5'
                    : 'text-stone-400 hover:text-white hover:bg-white/5'
                }`
              }
            >
              {item.label}
              {item.wip && <span className="ml-1 text-[8px] text-amber-400 font-bold">WIP</span>}
            </NavLink>
          ))}
          {isAdmin && (
            <NavLink
              to="/admin/scrape"
              className={({ isActive }) =>
                `block px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'text-amber-400 bg-white/5'
                    : 'text-amber-500/70 hover:text-amber-400 hover:bg-white/5'
                }`
              }
            >
              Admin
            </NavLink>
          )}
          <div className="border-t border-stone-700 pt-2 mt-2">
            <UserMenu onAction={onClose} onReportBug={onReportBug} />
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
      <div className="min-h-screen bg-[#faf8f4] flex items-center justify-center">
        <div className="text-stone-400 font-mono text-sm">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  return (
    <Router>
      <div className="min-h-screen bg-[#faf8f4]">
        <nav className="bg-[#1c1917] sticky top-0 z-30">
          <div className="max-w-6xl mx-auto px-4">
            <div className="flex items-center justify-between h-11">
              <Link to="/" className="text-sm font-bold text-white tracking-wide shrink-0" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
                Fantasy Six Nations
              </Link>

              {/* Desktop nav */}
              <div className="hidden md:flex items-center gap-6">
                {NAV_ITEMS.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      `text-[11px] font-semibold uppercase tracking-[1.5px] transition-colors ${
                        isActive
                          ? 'text-white'
                          : 'text-stone-400 hover:text-white'
                      }`
                    }
                  >
                    {item.label}
                    {item.wip && <span className="ml-1 text-[8px] text-amber-400 font-bold">WIP</span>}
                  </NavLink>
                ))}
                {user.is_admin && (
                  <NavLink
                    to="/admin/scrape"
                    className={({ isActive }) =>
                      `text-[11px] font-semibold uppercase tracking-[1.5px] transition-colors ${
                        isActive
                          ? 'text-amber-400'
                          : 'text-amber-500/70 hover:text-amber-400'
                      }`
                    }
                  >
                    Admin
                  </NavLink>
                )}
                <UserMenu onReportBug={() => setIssueModalOpen(true)} />
              </div>

              {/* Mobile hamburger + user avatar */}
              <div className="flex items-center gap-2 md:hidden">
                <UserMenu onReportBug={() => setIssueModalOpen(true)} />
                <button
                  onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                  className="p-2 rounded-lg hover:bg-white/5 text-stone-400"
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

        <MobileMenu open={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} isAdmin={user.is_admin} onReportBug={() => setIssueModalOpen(true)} />

        <main>
          <Routes>
            <Route path="/fantasy-stats" element={
              <div className="px-6 py-6">
                <FantasyStats />
              </div>
            } />
            <Route path="/players-all-stats" element={
              <div className="px-6 py-6">
                <PlayersAllStats />
              </div>
            } />
            <Route path="/historical-stats" element={
              <div className="px-6 py-6">
                <HistoricalStats />
              </div>
            } />
            <Route path="/tryscorers" element={<div className="max-w-6xl mx-auto px-6 py-6"><Tryscorers /></div>} />
            <Route path="/admin/scrape" element={<div className="max-w-6xl mx-auto px-6 py-6"><AdminScrape /></div>} />
            <Route path="/" element={<div className="max-w-6xl mx-auto px-6 py-6"><Dashboard /></div>} />
          </Routes>
        </main>

        <footer className="border-t-2 border-stone-900 bg-[#faf8f4] mt-8">
          <div className="max-w-6xl mx-auto px-6 py-6 flex justify-center">
            <button
              onClick={() => setIssueModalOpen(true)}
              className="text-xs text-stone-400 uppercase tracking-wider font-semibold hover:text-[#b91c1c] transition-colors"
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
