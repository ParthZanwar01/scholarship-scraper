import PropTypes from 'prop-types';
import { ExternalLink, Instagram, Globe, MessageCircle } from 'lucide-react';

const ScholarshipCard = ({ scholarship }) => {
  const { title, description, amount, platform, source_url, created_at, deadline } = scholarship;

  // Format Date
  const date = new Date(created_at).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric'
  });

  // Determine Icon based on platform
  const getIcon = () => {
    switch (platform?.toLowerCase()) {
      case 'instagram': return <Instagram size={18} />;
      case 'reddit': return <MessageCircle size={18} />;
      default: return <Globe size={18} />;
    }
  };

  // Determine Badge Color
  const getPlatformColor = () => {
    switch (platform?.toLowerCase()) {
      case 'instagram': return 'badge-red'; // Instagram Colors
      case 'reddit': return 'badge-orange'; // Reddit Orange
      default: return 'badge-blue';
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
        <div className={`badge ${getPlatformColor()}`}>
          {getIcon()}
          <span style={{ textTransform: 'capitalize' }}>{platform || 'Web'}</span>
        </div>
        
        {amount && (
            <div className="badge badge-green">
              {amount}
            </div>
        )}
      </div>

      {/* Content */}
      <div>
        <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.25rem', lineHeight: '1.4' }}>
          {title || "Untitled Opportunity"}
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.5', overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', margin: 0 }}>
          {description}
        </p>
      </div>

      {/* Footer */}
      <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid rgba(0,0,0,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Found: {date}</span>
        
        <a 
          href={source_url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="btn-primary"
          style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}
        >
          Apply <ExternalLink size={16} />
        </a>
      </div>
    </div>
  );
};

ScholarshipCard.propTypes = {
  scholarship: PropTypes.shape({
    title: PropTypes.string,
    description: PropTypes.string,
    amount: PropTypes.string,
    platform: PropTypes.string,
    source_url: PropTypes.string,
    created_at: PropTypes.string,
    deadline: PropTypes.string,
  }).isRequired,
};

export default ScholarshipCard;
