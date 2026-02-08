import React from 'react';
import { useSearchParams } from 'react-router-dom';
import DateGroupedMediaSections from '../components/DateGroupedMediaSections';
import TopControlBar from '../components/TopControlBar';
import { normalizeEnumParam, readEnumParam, withParam } from '../utils/urlState';

function TimelinePage({
  sourceMedia,
  displayedMedia,
  mediaLoading,
  activeFilters,
  onToggleFilter,
  expandedDates,
  toggleDate,
  openLightboxWithList,
  formatDuration,
  loaderRef,
  hasMore,
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const groupByParam = searchParams.get('groupBy');
  const groupBy = readEnumParam(searchParams, 'groupBy', ['day', 'month', 'year'], 'day');
  const timelineItems = groupBy === 'day' ? displayedMedia : sourceMedia;
  const showInfiniteLoader = groupBy === 'day' && hasMore;
  const groupShowLimit = groupBy === 'year' ? 24 : groupBy === 'month' ? 16 : 8;

  const handleGroupByChange = (nextGroupBy) => {
    const next = withParam(searchParams, 'groupBy', nextGroupBy, { defaultValue: 'day' });
    setSearchParams(next, { replace: true });
  };

  React.useEffect(() => {
    const next = normalizeEnumParam(searchParams, 'groupBy', ['day', 'month', 'year'], 'day');
    if (next) setSearchParams(next, { replace: true });
  }, [groupBy, groupByParam, searchParams, setSearchParams]);

  return (
    <div className="gallery-container">
      <TopControlBar
        activeFilters={activeFilters}
        onFilterChange={onToggleFilter}
        groupBy={groupBy}
        onGroupByChange={handleGroupByChange}
      />

      {mediaLoading ? (
        <div className="loading-indicator" aria-live="polite">
          <span className="loading-spinner" aria-label="Loading" />
        </div>
      ) : timelineItems.length === 0 ? (
        <div className="empty-state">No media found</div>
      ) : (
        <DateGroupedMediaSections
          items={timelineItems}
          openLightboxWithList={openLightboxWithList}
          formatDuration={formatDuration}
          expandedDates={expandedDates}
          onToggleDate={toggleDate}
          showLimit={groupShowLimit}
          showLocationNames
          locationDisplayMode="top"
          showDateLink
          groupBy={groupBy}
          expandedKeyPrefix={groupBy}
          collapsible
        />
      )}

      {!mediaLoading && showInfiniteLoader ? (
        <div ref={loaderRef} className="loading-indicator">
          <span className="loading-spinner" aria-label="Loading" />
        </div>
      ) : !mediaLoading ? (
        <div className="end-divider" aria-label="No more results">—</div>
      ) : null}
    </div>
  );
}

export default TimelinePage;
