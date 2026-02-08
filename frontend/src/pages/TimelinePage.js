import React, { useState } from 'react';
import DateGroupedMediaSections from '../components/DateGroupedMediaSections';
import TopControlBar from '../components/TopControlBar';

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
      <TopControlBar
        activeFilter={activeFilter?.name || 'all'}
        onFilterChange={(filterName) => {
          if (filterName === 'all') setActiveFilter(null);
          else setActiveFilter({ name: filterName, items: smartAlbums[filterName] });
        }}
        groupBy={groupBy}
        onGroupByChange={setGroupBy}
      />

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
