import React from 'react';
import MediaCard from '../components/MediaCard';

function AlbumsPage({ smartAlbums, formatDuration }) {
  const albums = Object.entries(smartAlbums).filter(([name]) => name !== 'all');

  return (
    <div className="albums-container">
      <h2>Smart Albums</h2>
      <div className="gallery-grid">
        {albums.map(([name, items]) => (
          <a
            key={name}
            href={`/album/${name}`}
            target="_blank"
            rel="noreferrer"
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            {items.length > 0 ? (
              <MediaCard
                item={items[0]}
                onClick={() => {}}
                formatDuration={formatDuration}
                imageStyle={{ filter: 'brightness(0.5)' }}
              />
            ) : (
              <div className="gallery-item" />
            )}
            <div className="album-overlay">
              <span className="album-name">{name.toUpperCase()}</span>
              <span className="album-count">{items.length} items</span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

export default AlbumsPage;
