import React, { useMemo } from 'react';
import MediaGrid from './MediaGrid';

function formatDateKey(createdAt) {
  const d = new Date(createdAt);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function formatMonthKey(createdAt) {
  const d = new Date(createdAt);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  return `${y}-${m}`;
}

function formatYearKey(createdAt) {
  return String(new Date(createdAt).getFullYear());
}

function buildGroupKey(createdAt, groupBy) {
  if (groupBy === 'month') return formatMonthKey(createdAt);
  if (groupBy === 'year') return formatYearKey(createdAt);
  return formatDateKey(createdAt);
}

function getGroupSortTime(key, groupBy) {
  if (groupBy === 'year') return new Date(`${key}-01-01`).getTime();
  if (groupBy === 'month') return new Date(`${key}-01`).getTime();
  return new Date(key).getTime();
}

function DateGroupedMediaSections({
  items,
  openLightboxWithList,
  formatDuration,
  showLimit = 6,
  showLocationNames = false,
  showDateLink = false,
  collapsible = true,
  headerStyle,
  groupBy = 'day',
}) {
  const groups = useMemo(() => {
    return (items || []).reduce((acc, item) => {
      const key = buildGroupKey(item.created_at, groupBy);
      if (!acc[key]) acc[key] = [];
      acc[key].push(item);
      return acc;
    }, {});
  }, [items, groupBy]);

  const orderedDates = useMemo(
    () => Object.keys(groups).sort((a, b) => getGroupSortTime(b, groupBy) - getGroupSortTime(a, groupBy)),
    [groups, groupBy]
  );

  return orderedDates.map((dateKey) => {
    const dateItems = groups[dateKey];
    const visibleItems = collapsible ? dateItems.slice(0, showLimit) : dateItems;
    const locationEntries = showLocationNames
      ? Array.from(
          new Map(
            dateItems
              .map((m) => {
                const key = (m.location_key || '').trim().toLowerCase();
                if (!key) return null;
                return [key, { key, label: m.location_city || m.location_name || key }];
              })
              .filter(Boolean)
          ).values()
        )
      : [];

    return (
      <div key={dateKey} className={`date-group ${dateItems.length > 20 ? 'busy-day' : ''}`}>
        <div
          className="group-header"
          style={{ ...headerStyle }}
        >
          <div className="group-info">
            <div className="group-main">
              <div className="group-top-line">
                <h2 className="group-title">
                  {showDateLink ? (
                    <a
                      href={`/date/${dateKey}`}
                      target="_blank"
                      rel="noreferrer"
                      className="group-title-link"
                    >
                      {dateKey}
                    </a>
                  ) : (
                    dateKey
                  )}
                </h2>
                <span className="group-count">{dateItems.length} items</span>
              </div>
              {locationEntries.length > 0 && (
                <span className="group-location group-location-links">
                  {locationEntries.map((entry, idx) => (
                    <React.Fragment key={entry.key}>
                      <a
                        href={`/location/${encodeURIComponent(entry.key)}`}
                        className="group-location-link"
                        title={`打开城市页：${entry.label}`}
                      >
                        {entry.label}
                      </a>
                      {idx < locationEntries.length - 1 && <span className="group-location-sep"> | </span>}
                    </React.Fragment>
                  ))}
                </span>
              )}
            </div>
          </div>
        </div>

        <MediaGrid
          items={visibleItems}
          onItemClick={(_, idx) => openLightboxWithList(visibleItems, idx)}
          formatDuration={formatDuration}
          className="date-group-grid"
        />
      </div>
    );
  });
}

export default DateGroupedMediaSections;