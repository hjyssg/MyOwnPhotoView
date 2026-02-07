import React from 'react';
import LazyImage from '../components/LazyImage';

function AlbumsPage({ smartAlbums }) {
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
            className="album-link"
          >
            <div className="album-card">
              {items.length > 0 ? (
                <LazyImage
                  src={items[0].thumbnail_path ? `/${items[0].thumbnail_path}` : `/api/media/image/${items[0].id}`}
                  alt=""
                  className="album-cover"
                />
              ) : (
                <div className="album-cover album-empty" />
              )}
              <div className="album-overlay">
                <span className="album-name">{name.toUpperCase()}</span>
                <span className="album-count">{items.length} items</span>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

export default AlbumsPage;
