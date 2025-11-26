import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import Lightbox from './Lightbox';

function App() {
  const [media, setMedia] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [scanPath, setScanPath] = useState('backend/media');

  useEffect(() => {
    const fetchMedia = async () => {
      try {
        const response = await axios.get('/api/media');
        setMedia(response.data);
      } catch (error) {
        console.error("Error fetching media:", error);
      }
    };
    fetchMedia();
  }, []);

  const openLightbox = (item, index) => {
    setSelectedItem(item);
    setCurrentIndex(index);
  };

  const closeLightbox = () => {
    setSelectedItem(null);
  };

  const showNext = () => {
    const nextIndex = (currentIndex + 1) % media.length;
    setSelectedItem(media[nextIndex]);
    setCurrentIndex(nextIndex);
  };

  const showPrev = () => {
    const prevIndex = (currentIndex - 1 + media.length) % media.length;
    setSelectedItem(media[prevIndex]);
    setCurrentIndex(prevIndex);
  };

  const formatDuration = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs < 10 ? '0' : ''}${secs}`;
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Local Smart Gallery</h1>
        <div className="scan-controls">
          <input
            type="text"
            value={scanPath}
            onChange={(e) => setScanPath(e.target.value)}
            placeholder="Enter path to scan"
          />
          <button onClick={() => axios.post(`/api/scan?directory=${scanPath}`)}>Scan Media</button>
        </div>
      </header>
      <div className="gallery-grid">
        {media.map((item, index) => (
          <div key={item.id} className="gallery-item" onClick={() => openLightbox(item, index)}>
            <img
              src={item.media_type === 'video' ? `/${item.thumbnail_path}` : `/${item.filepath}`}
              alt={item.filepath}
            />
            {item.media_type === 'video' && (
              <div className="video-overlay">
                <span className="play-icon">▶️</span>
                <span className="duration">{formatDuration(item.duration)}</span>
              </div>
            )}
          </div>
        ))}
      </div>
      {selectedItem && (
        <Lightbox
          item={selectedItem}
          onClose={closeLightbox}
          onNext={showNext}
          onPrev={showPrev}
        />
      )}
    </div>
  );
}

export default App;
