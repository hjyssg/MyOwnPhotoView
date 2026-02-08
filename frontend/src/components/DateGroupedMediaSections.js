import React, { useMemo } from 'react';
import MediaGrid from './MediaGrid';
import DateLabel from './DateLabel';

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

function sampleItemsByRange(items, sampleCount) {
  if (!Array.isArray(items) || sampleCount <= 0) return [];
  if (items.length <= sampleCount) return items;

  const total = items.length;
  const sampled = [];

  for (let i = 0; i < sampleCount; i += 1) {
    const start = Math.floor((i * total) / sampleCount);
    const end = Math.floor(((i + 1) * total) / sampleCount);
    const pickIndex = Math.floor((start + Math.max(start, end - 1)) / 2);
    sampled.push(items[pickIndex]);
  }

  return sampled;
}

function DateGroupedMediaSections({
  items,
  openLightboxWithList,
  formatDuration,
  showLimit = 8,
  showLocationNames = false,
  locationDisplayMode = 'all',
  showDateLink = false,
  collapsible = true,
  headerStyle,
  groupBy = 'day',
  sortOrder = 'desc',
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
    () =>
      Object.keys(groups).sort((a, b) => {
        const diff = getGroupSortTime(a, groupBy) - getGroupSortTime(b, groupBy);
        return sortOrder === 'asc' ? diff : -diff;
      }),
    [groups, groupBy, sortOrder]
  );

  return orderedDates.map((dateKey) => {
    const dateItems = [...groups[dateKey]].sort((a, b) => {
      const diff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      return sortOrder === 'asc' ? diff : -diff;
    });
    const visibleItems = collapsible ? sampleItemsByRange(dateItems, showLimit) : dateItems;
    const locationEntries = showLocationNames
      ? (() => {
          const bucket = {};
          dateItems.forEach((m) => {
            const key = (m.location_key || '').trim().toLowerCase();
            const label = (m.location_city || '').trim();
            // 与 busy-days 主地点逻辑一致：仅统计可归一化出的地点
            if (!key || !label) return;
            if (!bucket[key]) bucket[key] = { key, label, count: 0 };
            bucket[key].count += 1;
          });

          const sorted = Object.values(bucket).sort((a, b) => {
            if (b.count !== a.count) return b.count - a.count;
            return a.label.localeCompare(b.label, 'zh-CN');
          });

          if (locationDisplayMode === 'top') {
            return sorted.length ? [{ key: sorted[0].key, label: sorted[0].label }] : [];
          }
          return sorted.map((x) => ({ key: x.key, label: x.label }));
        })()
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
                  <DateLabel value={dateKey} groupBy={groupBy} clickable={showDateLink} />
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