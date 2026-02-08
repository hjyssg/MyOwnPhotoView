import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useParams } from 'react-router-dom';
import MediaGrid from '../components/MediaGrid';

function AlbumDetailPage({ openLightboxWithList, formatDuration, allMedia }) {
  const { albumName } = useParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const safeName = useMemo(() => (albumName || '').toLowerCase(), [albumName]);

  useEffect(() => {
    let canceled = false;

    const load = async () => {
      setLoading(true);
      try {
        const res = await axios.get(`/api/media/by-album?name=${encodeURIComponent(safeName)}`);
        if (!canceled) setItems(res.data);
      } catch (_) {
        if (!canceled) {
          const fallback = allMedia.filter((m) => {
            if (safeName === 'video') return m.media_type === 'video';
            if (safeName === 'all') return true;
            return m.source_type === safeName;
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
  }, [safeName, allMedia]);

  const orderedItems = useMemo(
    () =>
      [...items].sort(
        (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      ),
    [items]
  );

  return (
    <div className="gallery-container">
      <h2>{safeName.toUpperCase()}</h2>
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

export default AlbumDetailPage;
