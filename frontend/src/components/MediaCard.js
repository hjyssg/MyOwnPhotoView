import React, { useRef, useState } from 'react';
import LazyImage from './LazyImage';

function formatFileSize(bytes) {
  const value = Number(bytes);
  if (!Number.isFinite(value) || value <= 0) return 'Unknown';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let idx = 0;
  let size = value;
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024;
    idx += 1;
  }
  return `${size.toFixed(size >= 10 || idx === 0 ? 0 : 1)} ${units[idx]}`;
}

function formatDateTime(value) {
  if (!value) return 'Unknown';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  const ss = String(d.getSeconds()).padStart(2, '0');
  return `${y}-${m}-${day} ${hh}:${mm}:${ss}`;
}

function MediaCard({ item, onClick, formatDuration, imageStyle }) {
  const cardRef = useRef(null);
  const [panelSide, setPanelSide] = useState('right');

  const handleMouseEnter = () => {
    const el = cardRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const panelWidth = 380;
    const gap = 12;
    const canShowRight = rect.right + gap + panelWidth < window.innerWidth;
    setPanelSide(canShowRight ? 'right' : 'left');
  };

  return (
    <div className="gallery-item" onClick={onClick} ref={cardRef} onMouseEnter={handleMouseEnter}>
      <div className="media-visual">
        <LazyImage
          src={item.thumbnail_path ? `/${item.thumbnail_path}` : `/api/media/image/${item.id}`}
          alt=""
          style={imageStyle}
        />
        {item.media_type === 'video' && (
          <div className="video-overlay">
            <span className="play-icon" aria-hidden="true">▶</span>
            <span className="duration">{formatDuration(item.duration)}</span>
          </div>
        )}
        <span className="source-badge">{item.source_type}</span>
      </div>

      <div
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
      </div>
    </div>
  );
}

export default MediaCard;
