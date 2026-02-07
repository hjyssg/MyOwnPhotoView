import React from 'react';
import MediaCard from './MediaCard';

function MediaGrid({ items, onItemClick, formatDuration, imageStyle, className = '' }) {
  return (
    <div className={`gallery-grid ${className}`.trim()}>
      {items.map((item, index) => (
        <MediaCard
          key={item.id}
          item={item}
          onClick={() => onItemClick(item, index)}
          formatDuration={formatDuration}
          imageStyle={imageStyle}
        />
      ))}
    </div>
  );
}

export default MediaGrid;
