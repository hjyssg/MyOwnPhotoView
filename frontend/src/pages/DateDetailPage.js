import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useParams, useSearchParams } from 'react-router-dom';
import MediaGrid from '../components/MediaGrid';
import TopControlBar from '../components/TopControlBar';
import {
  normalizeCsvEnumSetParam,
  readCsvEnumSetParam,
  withCsvEnumSetParam,
} from '../utils/urlState';

const AVAILABLE_FILTER_KEYS = ['camera', 'screenshot', 'video', 'etc'];

function DateDetailPage({
  openLightboxWithList,
  formatDuration,
  allMedia,
  granularity = 'day',
  matchesFilter,
}) {
  const { dateKey } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  // 从 URL 读取过滤状态
  const activeFilters = useMemo(() => {
    return new Set(readCsvEnumSetParam(searchParams, 'filters', AVAILABLE_FILTER_KEYS));
  }, [searchParams]);

  // 规范化 URL 参数
  useEffect(() => {
    const next = normalizeCsvEnumSetParam(
      searchParams,
      'filters',
      AVAILABLE_FILTER_KEYS
    );
    if (next) {
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  // 处理过滤切换
  const handleToggleFilter = (filterKey) => {
    const current = new Set(activeFilters);

    if (filterKey === 'all') {
      current.clear();
    } else if (AVAILABLE_FILTER_KEYS.includes(filterKey)) {
      if (current.has(filterKey)) current.delete(filterKey);
      else current.add(filterKey);
    }

    const nextFilters = Array.from(current);
    const next = withCsvEnumSetParam(searchParams, 'filters', nextFilters);
    setSearchParams(next, { replace: true });
  };

  // 过滤逻辑（如果父组件没传，使用默认实现）
  const defaultMatchesFilter = (item, filterKey) => {
    if (filterKey === 'video') return item.media_type === 'video';
    if (filterKey === 'camera') return item.source_type === 'camera';
    if (filterKey === 'screenshot') return item.source_type === 'screenshot';
    if (filterKey === 'etc') {
      const source = item.source_type;
      return item.media_type !== 'video' && source !== 'camera' && source !== 'screenshot';
    }
    return false;
  };

  const doMatchFilter = matchesFilter || defaultMatchesFilter;

  useEffect(() => {
    let canceled = false;

    const buildKey = (date) => {
      const y = date.getFullYear();
      const m = String(date.getMonth() + 1).padStart(2, '0');
      const d = String(date.getDate()).padStart(2, '0');
      if (granularity === 'year') return String(y);
      if (granularity === 'month') return `${y}-${m}`;
      return `${y}-${m}-${d}`;
    };

    const filterByGranularity = () => {
      const list = allMedia || [];
      return list.filter((m) => {
        const d = new Date(m.created_at);
        return buildKey(d) === dateKey;
      });
    };

    if (granularity !== 'day') {
      setItems(filterByGranularity());
      setLoading(false);
      return () => {
        canceled = true;
      };
    }

    const load = async () => {
      setLoading(true);
      try {
        const res = await axios.get(`/api/media/by-date?date=${encodeURIComponent(dateKey)}`);
        if (!canceled) setItems(res.data);
      } catch (_) {
        if (!canceled) {
          const fallback = filterByGranularity();
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
  }, [dateKey, allMedia, granularity]);

  // 应用过滤
  const filteredItems = useMemo(() => {
    if (!activeFilters.size) return items;
    return items.filter((item) => {
      for (const key of activeFilters) {
        if (doMatchFilter(item, key)) return true;
      }
      return false;
    });
  }, [items, activeFilters, doMatchFilter]);

  const orderedItems = useMemo(
    () =>
      [...filteredItems].sort(
        (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      ),
    [filteredItems]
  );

  const granularityLabel = granularity === 'year' ? 'Year' : granularity === 'month' ? 'Month' : 'Date';

  return (
    <div className="gallery-container">
      <h2>{granularityLabel}: {dateKey} · {orderedItems.length} items</h2>

      {/* 过滤条 */}
      <TopControlBar
        activeFilters={activeFilters}
        onFilterChange={handleToggleFilter}
        hideGroupBy
      />

      {loading ? (
        <div className="loading-indicator">
          <span className="loading-spinner" aria-label="Loading" />
        </div>
      ) : (
        <MediaGrid
          items={orderedItems}
          onItemClick={(_, idx) => openLightboxWithList(orderedItems, idx)}
          formatDuration={formatDuration}
        />
      )}
    </div>
  );
}

export default DateDetailPage;
