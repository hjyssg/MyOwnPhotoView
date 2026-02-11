import React, { useEffect, useRef, useState } from 'react';
import LazyImage from './LazyImage';
import { getThumbnailUrl } from '../utils/urlUtil';

function VideoDuration({ itemId, duration: initialDuration, formatDuration }) {
  const [duration, setDuration] = useState(initialDuration);
  const fetchedRef = useRef(false);
  const observerRef = useRef(null);
  const elRef = useRef(null);

  useEffect(() => {
    if (duration != null || fetchedRef.current) return;

    const el = elRef.current;
    if (!el) return;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && !fetchedRef.current) {
          fetchedRef.current = true;
          observerRef.current?.disconnect();
          fetch(`/api/media/${itemId}/duration`)
            .then((r) => r.json())
            .then((data) => { if (data.duration != null) setDuration(data.duration); })
            .catch(() => {});
        }
      },
      { rootMargin: '100px' }
    );
    observerRef.current.observe(el);

    return () => observerRef.current?.disconnect();
  }, [itemId, duration]);

  return (
    <span ref={elRef} className="duration">
      {duration != null ? formatDuration(duration) : ''}
    </span>
  );
}

function MediaCard({ item, onClick, formatDuration, imageStyle }) {
  return (
    <div className="gallery-item" onClick={onClick}>
      <div className="media-visual">
        <LazyImage
          src={getThumbnailUrl(item)}
          alt=""
          style={imageStyle}
        />
        {item.media_type === 'video' && (
          <div className="video-overlay">
            <span className="play-icon" aria-hidden="true">▶</span>
            <VideoDuration
              itemId={item.id}
              duration={item.duration}
              formatDuration={formatDuration}
            />
          </div>
        )}
        {/* <span className="source-badge">{item.source_type}</span> */}
      </div>

      {/* <div
        className={`media-hover-card ${panelSide === 'left' ? 'side-left' : 'side-right'}`}
        aria-hidden="true"
      >
        <div className="meta-row meta-path" title={item.filepath || ''}>
          <strong>Path:</strong> {item.filepath || 'Unknown'}
        </div>
        <div className="meta-row"><strong>Time:</strong> {formatDateTime(item.created_at)}</div>
        <div className="meta-row">
          <strong>Type:</strong> {item.media_type || 'unknown'} · {item.source_type || 'unknown'}
        </div>
        <div className="meta-row"><strong>Size:</strong> {formatFileSize(item.size)}</div>
        {!!item.location_name && <div className="meta-row"><strong>Location:</strong> {item.location_name}</div>}
        {item.media_type === 'video' && (
          <div className="meta-row"><strong>Duration:</strong> {formatDuration(item.duration)}</div>
        )}
      </div> */}
    </div>
  );
}

export default MediaCard;
