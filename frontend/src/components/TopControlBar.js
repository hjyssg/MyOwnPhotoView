import React from 'react';

const FILTER_OPTIONS = [
  { key: 'all', label: 'ALL' },
  { key: 'camera', label: 'CAMERA' },
  { key: 'screenshot', label: 'SCREENSHOT' },
  { key: 'video', label: 'VIDEO' },
];

const GROUP_OPTIONS = [
  { key: 'day', label: '按日' },
  { key: 'month', label: '按月' },
  { key: 'year', label: '按年' },
];

function TopControlBar({ activeFilter = 'all', onFilterChange, groupBy = 'day', onGroupByChange }) {
  return (
    <div className="timeline-toolbar">
      <div className="timeline-filters">
        {FILTER_OPTIONS.map((filter) => (
          <button
            key={filter.key}
            className={activeFilter === filter.key ? 'active' : ''}
            onClick={() => onFilterChange?.(filter.key)}
          >
            {filter.label}
          </button>
        ))}
      </div>

      <div className="timeline-filters timeline-aggregate-filters">
        {GROUP_OPTIONS.map((mode) => (
          <button
            key={mode.key}
            className={groupBy === mode.key ? 'active' : ''}
            onClick={() => onGroupByChange?.(mode.key)}
          >
            {mode.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default TopControlBar;