import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import './App.css';
import Lightbox from './Lightbox';

function App() {
  const [media, setMedia] = useState([]);
  const [displayedMedia, setDisplayedMedia] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [scanPath, setScanPath] = useState('backend/media');
  const [isScanning, setIsScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState('');
  const [page, setPage] = useState(1);
  const loader = useRef(null);
  const ITEMS_PER_PAGE = 50;

  useEffect(() => {
    const fetchMedia = async () => {
      try {
        const response = await axios.get('/api/media');
        setMedia(response.data);
        setDisplayedMedia(response.data.slice(0, ITEMS_PER_PAGE));
        setPage(1);
      } catch (error) {
        console.error("Error fetching media:", error);
      }
    };
    fetchMedia();
  }, []);

  // 懒加载更多项目
  const loadMore = useCallback(() => {
    const nextPage = page + 1;
    const start = 0;
    const end = nextPage * ITEMS_PER_PAGE;
    setDisplayedMedia(media.slice(start, end));
    setPage(nextPage);
  }, [page, media]);

  // Intersection Observer for infinite scroll
  useEffect(() => {
    const options = {
      root: null,
      rootMargin: '100px',
      threshold: 0.1
    };

    const observer = new IntersectionObserver((entities) => {
      const target = entities[0];
      if (target.isIntersecting && displayedMedia.length < media.length) {
        loadMore();
      }
    }, options);

    if (loader.current) {
      observer.observe(loader.current);
    }

    return () => {
      if (loader.current) {
        observer.unobserve(loader.current);
      }
    };
  }, [loadMore, displayedMedia.length, media.length]);

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

  const handleScan = async () => {
    setIsScanning(true);
    setScanMessage('正在扫描...');
    try {
      const response = await axios.post(`/api/scan?directory=${encodeURIComponent(scanPath)}`);
      setScanMessage(response.data.message || '扫描完成');
      // 重新获取媒体列表
      const mediaResponse = await axios.get('/api/media');
      setMedia(mediaResponse.data);
      setDisplayedMedia(mediaResponse.data.slice(0, ITEMS_PER_PAGE));
      setPage(1);
    } catch (error) {
      console.error("扫描出错:", error);
      setScanMessage(error.response?.data?.detail || '扫描失败，请检查路径');
    } finally {
      setIsScanning(false);
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds || seconds === 0) return '0:00';
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
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
            placeholder="输入要扫描的路径，如 E:\_Photo2"
          />
          <button onClick={handleScan} disabled={isScanning}>
            {isScanning ? '扫描中...' : '扫描媒体文件'}
          </button>
          {scanMessage && <span className="scan-message">{scanMessage}</span>}
        </div>
      </header>
      <div className="gallery-container">
        {Object.entries(
          displayedMedia.reduce((groups, item) => {
            const date = new Date(item.created_at).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });
            if (!groups[date]) groups[date] = [];
            groups[date].push(item);
            return groups;
          }, {})
        ).sort((a, b) => new Date(b[0]) - new Date(a[0])).map(([date, items]) => (
          <div key={date} className="date-group">
            <h2 className="group-title">{date}</h2>
            <div className="gallery-grid">
              {items.map((item) => {
                const globalIndex = displayedMedia.findIndex(m => m.id === item.id);
                return (
                  <div key={item.id} className="gallery-item" onClick={() => openLightbox(item, globalIndex)}>
                    <img
                      src={item.thumbnail_path ? `/${item.thumbnail_path}` : `/api/media/image/${item.id}`}
                      alt={item.filepath}
                      loading="lazy"
                      onError={(e) => {
                        console.error('加载失败:', item.id);
                        e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect width="200" height="200" fill="%23333"/><text x="50%" y="50%" text-anchor="middle" fill="white">加载失败</text></svg>';
                      }}
                    />
                    {item.media_type === 'video' && (
                      <div className="video-overlay">
                        <span className="play-icon">▶</span>
                        <span className="duration">{formatDuration(item.duration)}</span>
                      </div>
                    )}
                    <div className="item-info">
                      <span className="file-name">{item.filepath.split(/[\\/]/).pop()}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      {displayedMedia.length < media.length && (
        <div ref={loader} className="loading-indicator">
          <p>加载更多...</p>
        </div>
      )}
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
