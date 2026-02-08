import React, { useState } from 'react';
import DateGroupedMediaSections from '../components/DateGroupedMediaSections';

function TimelinePage({
  displayedMedia,
  activeFilter,
  setActiveFilter,
  smartAlbums,
  expandedDates,
  toggleDate,
  openLightboxWithList,
  formatDuration,
  loaderRef,
  hasMore,
}) {
  const [groupBy, setGroupBy] = useState('day');
  const showInfiniteLoader = groupBy === 'day' && hasMore;

  return (
    <div className="gallery-container">
      <div className="timeline-toolbar">
        <div className="timeline-filters">
          {['all', 'camera', 'screenshot', 'video'].map((filterName) => (
            <button
              key={filterName}
              className={(activeFilter?.name || 'all') === filterName ? 'active' : ''}
              onClick={() => {
                if (filterName === 'all') setActiveFilter(null);
                else setActiveFilter({ name: filterName, items: smartAlbums[filterName] });
              }}
            >
              {filterName.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="timeline-filters timeline-aggregate-filters">
          {[
            { key: 'day', label: '按日' },
            { key: 'month', label: '按月' },
            { key: 'year', label: '按年' },
          ].map((mode) => (
            <button
              key={mode.key}
              className={groupBy === mode.key ? 'active' : ''}
              onClick={() => setGroupBy(mode.key)}
            >
              {mode.label}
            </button>
          ))}
        </div>
      </div>

      {displayedMedia.length === 0 ? (
        <div className="empty-state">No media found</div>
      ) : (
        <DateGroupedMediaSections
          items={displayedMedia}
          openLightboxWithList={openLightboxWithList}
          formatDuration={formatDuration}
          expandedDates={expandedDates}
          onToggleDate={toggleDate}
          showLimit={8}
          showLocationNames
          locationDisplayMode="top"
          showDateLink
          groupBy={groupBy}
          expandedKeyPrefix={groupBy}
          collapsible
        />
      )}

      {showInfiniteLoader ? (
        <div ref={loaderRef} className="loading-indicator">
          <span className="loading-spinner" aria-label="Loading" />
        </div>
      ) : (
        <div className="end-divider" aria-label="No more results">—</div>
      )}
    </div>
  );
}

export default TimelinePage;
