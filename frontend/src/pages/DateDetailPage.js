import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useParams } from 'react-router-dom';
import MediaGrid from '../components/MediaGrid';

function DateDetailPage({ openLightboxWithList, formatDuration, allMedia, granularity = 'day' }) {
  const { dateKey } = useParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

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

  const granularityLabel = granularity === 'year' ? 'Year' : granularity === 'month' ? 'Month' : 'Date';

  return (
    <div className="gallery-container">
      <h2>{granularityLabel}: {dateKey} · {items.length} items</h2>
      {loading ? (
        <div className="loading-indicator">
          <span className="loading-spinner" aria-label="Loading" />
        </div>
      ) : (
        <MediaGrid
          items={items}
          onItemClick={(_, idx) => openLightboxWithList(items, idx)}
          formatDuration={formatDuration}
        />
      )}
    </div>
  );
}

export default DateDetailPage;
