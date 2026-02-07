import React from 'react';
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
  return (
    <div className="gallery-container">
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
          showDateLink
          collapsible
        />
      )}

      {hasMore && (
        <div ref={loaderRef} className="loading-indicator">
          <span className="loading-spinner" aria-label="Loading" />
        </div>
      )}
    </div>
  );
}

export default TimelinePage;
