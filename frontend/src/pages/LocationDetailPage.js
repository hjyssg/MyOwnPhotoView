import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useParams, useSearchParams } from 'react-router-dom';
import DateGroupedMediaSections from '../components/DateGroupedMediaSections';
import TopControlBar from '../components/TopControlBar';
import { normalizeEnumParam, readEnumParam, withParam } from '../utils/urlState';

function LocationDetailPage({ openLightboxWithList, formatDuration, allMedia }) {
  const { locationKey } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const activeFilterParam = searchParams.get('filter');
  const activeFilter = readEnumParam(
    searchParams,
    'filter',
    ['all', 'camera', 'screenshot', 'video', 'etc'],
    'all'
  );

  const groupByParam = searchParams.get('groupBy');
  const groupBy = readEnumParam(searchParams, 'groupBy', ['day', 'month', 'year'], 'day');

  useEffect(() => {
    let next = normalizeEnumParam(searchParams, 'filter', ['all', 'camera', 'screenshot', 'video', 'etc'], 'all');
    if (!next) next = normalizeEnumParam(searchParams, 'groupBy', ['day', 'month', 'year'], 'day');
    if (next) setSearchParams(next, { replace: true });
  }, [activeFilter, activeFilterParam, groupBy, groupByParam, searchParams, setSearchParams]);

  const handleFilterChange = (value) => {
    const next = withParam(searchParams, 'filter', value || 'all', { defaultValue: 'all' });
    setSearchParams(next, { replace: true });
  };

  const handleGroupByChange = (value) => {
    const next = withParam(searchParams, 'groupBy', value || 'day', { defaultValue: 'day' });
    setSearchParams(next, { replace: true });
  };

  useEffect(() => {
    let canceled = false;

    const load = async () => {
      setLoading(true);
      try {
        const res = await axios.get(`/api/media/by-location?key=${encodeURIComponent(locationKey)}`);
        if (!canceled) setItems(res.data || []);
      } catch (_) {
        if (!canceled) {
          const fallback = (allMedia || []).filter(
            (m) => (m.location_key || '').toLowerCase() === (locationKey || '').toLowerCase()
          );
          setItems(fallback);
        }
      } finally {
        if (!canceled) setLoading(false);
      }
    };

    load();
    return () => {
      canceled = true;
    };
  }, [locationKey, allMedia]);

  const title = items[0]?.location_city || decodeURIComponent(locationKey || '未知地点');
  const filteredItems = useMemo(() => {
    if (activeFilter === 'all') return items;
    if (activeFilter === 'video') return items.filter((m) => m.media_type === 'video');
    return items.filter((m) => m.source_type === activeFilter);
  }, [items, activeFilter]);

  return (
    <div className="gallery-container">
      <h2 className="location-page-title">{title}</h2>
      <div className="location-page-count">共 {filteredItems.length} 张</div>

      <TopControlBar
        activeFilter={activeFilter}
        onFilterChange={handleFilterChange}
        groupBy={groupBy}
        onGroupByChange={handleGroupByChange}
      />

      {loading ? (
        <div className="loading-indicator">
          <span className="loading-spinner" aria-label="Loading" />
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="empty-state">该地点暂无媒体</div>
      ) : (
        <DateGroupedMediaSections
          items={filteredItems}
          openLightboxWithList={openLightboxWithList}
          formatDuration={formatDuration}
          showDateLink
          groupBy={groupBy}
          sortOrder="asc"
          collapsible
        />
      )}
    </div>
  );
}

export default LocationDetailPage;
