import React, { useMemo } from 'react';
import MediaGrid from '../components/MediaGrid';

function formatDateKey(createdAt) {
  const d = new Date(createdAt);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

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
  const groups = useMemo(() => {
    return displayedMedia.reduce((acc, item) => {
      const key = formatDateKey(item.created_at);
      if (!acc[key]) acc[key] = [];
      acc[key].push(item);
      return acc;
    }, {});
  }, [displayedMedia]);

  const orderedDates = useMemo(
    () => Object.keys(groups).sort((a, b) => new Date(b) - new Date(a)),
    [groups]
  );

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
        orderedDates.map((dateKey) => {
          const items = groups[dateKey];
          const isExpanded = expandedDates.has(dateKey);
          const showLimit = 6;
          const visibleItems = isExpanded ? items : items.slice(0, showLimit);
          const hasHidden = items.length > showLimit;
          const locationNames = Array.from(
            new Set(items.map((m) => m.location_name).filter(Boolean))
          );

          return (
            <div key={dateKey} className={`date-group ${items.length > 20 ? 'busy-day' : ''}`}>
              <div className="group-header" onClick={() => toggleDate(dateKey)}>
                <div className="group-info">
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <h2 className="group-title">{dateKey}</h2>
                    {locationNames.length > 0 && (
                      <span className="group-location">{locationNames.join(' | ')}</span>
                    )}
                    <a
                      href={`/date/${dateKey}`}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="expand-toggle"
                    >
                      Open full date in new tab
                    </a>
                  </div>
                  <span className="group-count">{items.length} items</span>
                </div>
                {hasHidden && (
                  <button className="expand-toggle">
                    {isExpanded ? 'Collapse' : 'Expand'}
                  </button>
                )}
              </div>

              <MediaGrid
                items={visibleItems}
                onItemClick={(_, idx) => openLightboxWithList(visibleItems, idx)}
                formatDuration={formatDuration}
              />
            </div>
          );
        })
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
