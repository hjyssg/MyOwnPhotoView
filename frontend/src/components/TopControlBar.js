import React from 'react';

const FILTER_OPTIONS = [
  { key: 'all', label: 'ALL' },
  { key: 'camera', label: 'CAMERA' },
  { key: 'screenshot', label: 'SCREENSHOT' },
  { key: 'video', label: 'VIDEO' },
  { key: 'etc', label: 'ETC' },
];

const GROUP_OPTIONS = [
  { key: 'day', label: '按日' },
  { key: 'month', label: '按月' },
  { key: 'year', label: '按年' },
];

function TopControlBar({
  activeFilter = 'all',
  activeFilters = null,
  onFilterChange,
  groupBy = 'day',
  onGroupByChange,
  hideGroupBy = false,
}) {
  const selectedFilters = activeFilters instanceof Set
    ? activeFilters
    : new Set(activeFilter && activeFilter !== 'all' ? [activeFilter] : []);

  const isFilterActive = (filterKey) => {
    if (filterKey === 'all') return selectedFilters.size === 0;
    return selectedFilters.has(filterKey);
  };

  return (
    <div className="timeline-toolbar">
      <div className="timeline-filters">
        {FILTER_OPTIONS.map((filter) => (
          <button
            key={filter.key}
            className={isFilterActive(filter.key) ? 'active' : ''}
            onClick={() => onFilterChange?.(filter.key)}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {!hideGroupBy && (
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
      )}
    </div>
  );
}

export default TopControlBar;