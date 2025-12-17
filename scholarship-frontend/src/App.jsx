import { useState, useEffect } from 'react';
import { Search, Filter, SortDesc } from 'lucide-react';
import ScholarshipCard from './components/ScholarshipCard';

// API URL - uses /api proxy in production (Netlify), direct URL in development
const API_URL = import.meta.env.PROD 
  ? "/api"  // Production: proxy through Netlify to avoid mixed content
  : "http://64.23.231.89:8000";  // Development: direct connection

function App() {
  const [scholarships, setScholarships] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [platformFilter, setPlatformFilter] = useState("all");
  const [sortBy, setSortBy] = useState("date"); // 'date' or 'amount'

  useEffect(() => {
    fetchScholarships();
  }, []);

  const fetchScholarships = async () => {
    try {
      setLoading(true);
      // Fetching 100 most recent
      const res = await fetch(`${API_URL}/scholarships/?limit=100`);
      const data = await res.json();
      setScholarships(data);
    } catch (error) {
      console.error("Failed to fetch scholarships:", error);
    } finally {
      setLoading(false);
    }
  };

  // --- Filtering Logic ---
  const filteredScholarships = scholarships
    .filter(item => {
      // 1. Search Logic (Title or Description)
      const term = searchTerm.toLowerCase();
      const matchesSearch =
        (item.title && item.title.toLowerCase().includes(term)) ||
        (item.description && item.description.toLowerCase().includes(term));

      // 2. Platform Filter
      const matchesPlatform = platformFilter === "all" ? true : item.platform === platformFilter;

      return matchesSearch && matchesPlatform;
    })
    .sort((a, b) => {
      if (sortBy === 'amount') {
        // Simple heuristic sort for amounts (extract numbers)
        const getVal = (str) => {
          if (!str) return 0;
          return parseInt(str.replace(/[^0-9]/g, '')) || 0;
        };
        return getVal(b.amount) - getVal(a.amount);
      }
      // Default: Date (Backend already sends sorted by date, but good to ensure)
      return new Date(b.created_at) - new Date(a.created_at);
    });

  return (
    <div className="app-container">
      {/* --- Header Section --- */}
      <header style={{ marginBottom: '3rem', textAlign: 'center' }}>
        <h1 style={{ fontSize: '3rem', fontWeight: '800', marginBottom: '1rem', background: '-webkit-linear-gradient(45deg, #2563eb, #9333ea)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Scholarship Finder
        </h1>
        <p style={{ fontSize: '1.2rem', color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto' }}>
          Automatically aggregating opportunities from across the web.
        </p>
      </header>

      {/* --- Controls Bar --- */}
      <div className="glass-panel" style={{ padding: '1rem', display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center', marginBottom: '2rem' }}>

        {/* Search */}
        <div style={{ flex: '1 1 300px', position: 'relative' }}>
          <Search size={20} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
          <input
            type="text"
            placeholder="Search for engineering, grants, deadlines..."
            className="glass-input"
            style={{ paddingLeft: '40px' }}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>

          <div style={{ position: 'relative' }}>
            <select
              className="glass-input"
              style={{ paddingRight: '2.5rem', appearance: 'none', minWidth: '150px' }}
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
            >
              <option value="all">All Sources</option>
              <option value="instagram">Instagram</option>
              <option value="reddit">Reddit</option>
              <option value="google">Web (Google)</option>
            </select>
            <Filter size={16} style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', color: '#64748b', pointerEvents: 'none' }} />
          </div>

          <div style={{ position: 'relative' }}>
            <select
              className="glass-input"
              style={{ paddingRight: '2.5rem', appearance: 'none', minWidth: '150px' }}
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="date">Most Recent</option>
              <option value="amount">Highest Amount ($)</option>
            </select>
            <SortDesc size={16} style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', color: '#64748b', pointerEvents: 'none' }} />
          </div>

        </div>
      </div>

      {/* --- Results Grid --- */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-secondary)' }}>
          <div className="loader" style={{ fontSize: '2rem', marginBottom: '1rem' }}>Loading Scholarships...</div>
        </div>
      ) : (
        <>
          <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>
            Showing <strong>{filteredScholarships.length}</strong> opportunities
          </p>

          <div className="scholarship-grid">
            {filteredScholarships.map((sch) => (
              <ScholarshipCard key={sch.id} scholarship={sch} />
            ))}
          </div>

          {filteredScholarships.length === 0 && (
            <div className="glass-panel" style={{ textAlign: 'center', padding: '4rem' }}>
              <h3>No scholarships found</h3>
              <p>Try adjusting your search terms or filters.</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default App
