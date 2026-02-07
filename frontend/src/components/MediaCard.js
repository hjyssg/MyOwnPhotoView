import React from 'react';
import LazyImage from './LazyImage';

function MediaCard({ item, onClick, formatDuration, imageStyle }) {
  return (
    <div className="gallery-item" onClick={onClick}>
      <LazyImage
        src={item.thumbnail_path ? `/${item.thumbnail_path}` : `/api/media/image/${item.id}`}
        alt=""
        style={imageStyle}
      />
      {item.media_type === 'video' && (
        <div className="video-overlay">
          <span className="play-icon">Play</span>
          <span className="duration">{formatDuration(item.duration)}</span>
        </div>
      )}
      <span className="source-badge">{item.source_type}</span>
    </div>
  );
}

export default MediaCard;
