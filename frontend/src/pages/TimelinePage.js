import React from 'react';
import { useSearchParams } from 'react-router-dom';
import DateGroupedMediaSections from '../components/DateGroupedMediaSections';
import TopControlBar from '../components/TopControlBar';

function TimelinePage({
  sourceMedia,
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
  const [searchParams, setSearchParams] = useSearchParams();
  const groupByParam = searchParams.get('groupBy');
  const groupBy = groupByParam === 'month' || groupByParam === 'year' || groupByParam === 'day' ? groupByParam : 'day';
  const timelineItems = groupBy === 'day' ? displayedMedia : sourceMedia;
  const showInfiniteLoader = groupBy === 'day' && hasMore;

  const handleGroupByChange = (nextGroupBy) => {
    const next = new URLSearchParams(searchParams);
    if (nextGroupBy === 'day') next.delete('groupBy');
    else next.set('groupBy', nextGroupBy);
    setSearchParams(next);
  };

  return (
    <div className="gallery-container">
      <TopControlBar
        activeFilter={activeFilter?.name || 'all'}
        onFilterChange={(filterName) => {
          if (filterName === 'all') setActiveFilter(null);
          else setActiveFilter({ name: filterName, items: smartAlbums[filterName] });
        }}
        groupBy={groupBy}
        onGroupByChange={handleGroupByChange}
      />

      {timelineItems.length === 0 ? (
        <div className="empty-state">No media found</div>
      ) : (
        <DateGroupedMediaSections
          items={timelineItems}
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
