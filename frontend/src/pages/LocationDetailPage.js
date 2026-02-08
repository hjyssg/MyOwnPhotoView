import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useParams } from 'react-router-dom';
import DateGroupedMediaSections from '../components/DateGroupedMediaSections';

function LocationDetailPage({ openLightboxWithList, formatDuration, allMedia }) {
  const { locationKey } = useParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

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

  return (
    <div className="gallery-container">
      <h2 className="location-page-title">{title}</h2>

      {loading ? (
        <div className="loading-indicator">
          <span className="loading-spinner" aria-label="Loading" />
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state">该地点暂无媒体</div>
      ) : (
        <DateGroupedMediaSections
          items={items}
          openLightboxWithList={openLightboxWithList}
          formatDuration={formatDuration}
          showLimit={6}
          showDateLink
          collapsible
        />
      )}
    </div>
  );
}

export default LocationDetailPage;
