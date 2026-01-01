import { BrowserRouter as Router, Routes, Route, Link, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Players from './pages/Players';
import TeamBuilder from './pages/TeamBuilder';
import Optimiser from './pages/Optimiser';
import Compare from './pages/Compare';
import Admin from './pages/Admin';

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
                  to="/team-builder"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium ${
                      isActive ? 'bg-primary-800' : 'hover:bg-primary-600'
                    }`
                  }
                >
                  Team Builder
                </NavLink>
                <NavLink
                  to="/optimiser"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium ${
                      isActive ? 'bg-primary-800' : 'hover:bg-primary-600'
                    }`
                  }
                >
                  Optimiser
                </NavLink>
                <NavLink
                  to="/compare"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium ${
                      isActive ? 'bg-primary-800' : 'hover:bg-primary-600'
                    }`
                  }
                >
                  Compare
                </NavLink>
                <NavLink
                  to="/admin"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium ${
                      isActive ? 'bg-primary-800' : 'hover:bg-primary-600'
                    }`
                  }
                >
                  Admin
                </NavLink>
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/players" element={<Players />} />
            <Route path="/team-builder" element={<TeamBuilder />} />
            <Route path="/optimiser" element={<Optimiser />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/admin" element={<Admin />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
