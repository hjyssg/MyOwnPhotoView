import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useParams } from 'react-router-dom';
import MediaGrid from '../components/MediaGrid';

function DateDetailPage({ openLightboxWithList, formatDuration, allMedia }) {
  const { dateKey } = useParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let canceled = false;

    const load = async () => {
      setLoading(true);
      try {
        const res = await axios.get(`/api/media/by-date?date=${encodeURIComponent(dateKey)}`);
        if (!canceled) setItems(res.data);
      } catch (_) {
        if (!canceled) {
          const fallback = allMedia.filter((m) => {
            const d = new Date(m.created_at);
            const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
              d.getDate()
            ).padStart(2, '0')}`;
            return key === dateKey;
          });
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
  }, [dateKey, allMedia]);

  return (
    <div className="gallery-container">
      <h2>{dateKey}</h2>
      {loading ? (
        <div className="loading-indicator">Loading...</div>
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
