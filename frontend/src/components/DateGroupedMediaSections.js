import React, { useMemo, useState } from 'react';
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
  expandedDates,
  onToggleDate,
  showLimit = 6,
  showLocationNames = false,
  showDateLink = false,
  collapsible = true,
  headerStyle,
  groupBy = 'day',
  expandedKeyPrefix,
}) {
  const [internalExpandedDates, setInternalExpandedDates] = useState(new Set());

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

  const activeExpandedDates = expandedDates || internalExpandedDates;

  const toggle = (dateKey) => {
    if (!collapsible) return;

    if (onToggleDate) {
      onToggleDate(dateKey);
      return;
    }

    setInternalExpandedDates((prev) => {
      const next = new Set(prev);
      if (next.has(dateKey)) next.delete(dateKey);
      else next.add(dateKey);
      return next;
    });
  };

  return orderedDates.map((dateKey) => {
    const dateItems = groups[dateKey];
    const expandedKey = expandedKeyPrefix ? `${expandedKeyPrefix}:${dateKey}` : dateKey;
    const hasHidden = collapsible && dateItems.length > showLimit;
    const isExpanded = activeExpandedDates.has(expandedKey);
    const visibleItems = hasHidden && !isExpanded ? dateItems.slice(0, showLimit) : dateItems;
    const locationNames = showLocationNames
      ? Array.from(new Set(dateItems.map((m) => m.location_name).filter(Boolean)))
      : [];

    return (
      <div key={dateKey} className={`date-group ${dateItems.length > 20 ? 'busy-day' : ''}`}>
        <div
          className="group-header"
          onClick={() => toggle(expandedKey)}
          style={{ cursor: collapsible ? 'pointer' : 'default', ...headerStyle }}
        >
          <div className="group-info">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <h2 className="group-title">{dateKey}</h2>
              {locationNames.length > 0 && (
                <span className="group-location">{locationNames.join(' | ')}</span>
              )}
              {showDateLink && (
                <a
                  href={`/date/${dateKey}`}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="expand-toggle"
                >
                  Open full date in new tab
                </a>
              )}
            </div>
            <span className="group-count">{dateItems.length} items</span>
          </div>
          {hasHidden && (
            <button
              className="expand-toggle"
              onClick={(e) => {
                e.stopPropagation();
                toggle(expandedKey);
              }}
            >
              {isExpanded ? 'Collapse' : 'Expand'}
            </button>
          )}
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