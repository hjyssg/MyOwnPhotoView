import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import axios from 'axios';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import './App.css';
import Lightbox from './Lightbox';
import MapView from './MapView';

const Navigation = () => {
  const location = useLocation();
  return (
    <nav className="nav-bar">
      <Link to="/" className={location.pathname === '/' ? 'active' : ''}>时间轴</Link>
      <Link to="/map" className={location.pathname === '/map' ? 'active' : ''}>地图足迹</Link>
      <Link to="/albums" className={location.pathname === '/albums' ? 'active' : ''}>智能相册</Link>
    </nav>
  );
};

function AppContent() {
  const [media, setMedia] = useState([]);
  const [displayedMedia, setDisplayedMedia] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [scanPath, setScanPath] = useState('C:\\Users\\Administrator\\Desktop\\test');
  const [isScanning, setIsScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState('');
  const [page, setPage] = useState(1);
  const loader = useRef(null);
  const ITEMS_PER_PAGE = 50;
  const navigate = useNavigate();

  // 过滤状态
  const [activeFilter, setActiveFilter] = useState(null); // { name: string, items: [] }

  const smartAlbums = useMemo(() => {
    return {
      camera: media.filter(m => m.source_type === 'camera'),
      screenshot: media.filter(m => m.source_type === 'screenshot'),
      web: media.filter(m => m.source_type === 'web'),
      video: media.filter(m => m.media_type === 'video'),
    };
  }, [media]);

  const fetchMedia = async () => {
    try {
      const response = await axios.get('/api/media');
      setMedia(response.data);
      if (!activeFilter) {
        setDisplayedMedia(response.data.slice(0, ITEMS_PER_PAGE));
      } else {
        // 如果有滤镜，同步更新滤镜数据
        const filteredItems = response.data.filter(m => {
          if (activeFilter.name === 'video') return m.media_type === 'video';
          return m.source_type === activeFilter.name;
        });
        setActiveFilter({ ...activeFilter, items: filteredItems });
      }
      setPage(1);
    } catch (error) {
      console.error("Error fetching media:", error);
    }
  };

  useEffect(() => {
    fetchMedia();
  }, []);

  const loadMore = useCallback(() => {
    const nextPage = page + 1;
    const end = nextPage * ITEMS_PER_PAGE;
    const sourceList = activeFilter ? activeFilter.items : media;
    setDisplayedMedia(sourceList.slice(0, end));
    setPage(nextPage);
  }, [page, media, activeFilter]);

  useEffect(() => {
    if (activeFilter) {
      setDisplayedMedia(activeFilter.items.slice(0, ITEMS_PER_PAGE));
      setPage(1);
    } else {
      setDisplayedMedia(media.slice(0, ITEMS_PER_PAGE));
      setPage(1);
    }
  }, [activeFilter, media]);

  useEffect(() => {
    const options = { root: null, rootMargin: '100px', threshold: 0.1 };
    const observer = new IntersectionObserver((entities) => {
      const target = entities[0];
      const totalLength = activeFilter ? activeFilter.items.length : media.length;
      if (target.isIntersecting && displayedMedia.length < totalLength) {
        loadMore();
      }
    }, options);

    if (loader.current) observer.observe(loader.current);
    return () => {
      if (loader.current) observer.unobserve(loader.current);
    };
  }, [loadMore, displayedMedia.length, media.length, activeFilter]);

  const openLightbox = (item, index) => {
    setSelectedItem(item);
    setCurrentIndex(index);
  };

  const closeLightbox = () => setSelectedItem(null);

  const showNext = () => {
    const nextIndex = (currentIndex + 1) % displayedMedia.length;
    setSelectedItem(displayedMedia[nextIndex]);
    setCurrentIndex(nextIndex);
  };

  const showPrev = () => {
    const prevIndex = (currentIndex - 1 + displayedMedia.length) % displayedMedia.length;
    setSelectedItem(displayedMedia[prevIndex]);
    setCurrentIndex(prevIndex);
  };

  const handleScan = async () => {
    setIsScanning(true);
    setScanMessage('正在扫描...');
    try {
      await axios.post(`/api/scan?directory=${encodeURIComponent(scanPath)}`);
      setScanMessage('扫描完成');
      fetchMedia();
    } catch (error) {
      console.error("扫描出错:", error);
      setScanMessage(error.response?.data?.detail || '扫描失败');
    } finally {
      setIsScanning(false);
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const TimelineView = () => (
    <div className="gallery-container">
      {activeFilter && (
        <div className="filter-info">
          <span>📂 正在查看：{activeFilter.name.toUpperCase()} ({activeFilter.items.length})</span>
          <button onClick={() => setActiveFilter(null)}>清除筛选 ✕</button>
        </div>
      )}
      {displayedMedia.length === 0 ? (
        <div className="empty-state">没有发现媒体内容</div>
      ) : (
        Object.entries(
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
                return (
                  <div key={item.id} className="gallery-item" onClick={() => {
                    const idx = displayedMedia.findIndex(m => m.id === item.id);
                    openLightbox(item, idx);
                  }}>
                    <img
                      src={item.thumbnail_path ? `/${item.thumbnail_path}` : `/api/media/image/${item.id}`}
                      alt=""
                      loading="lazy"
                    />
                    {item.media_type === 'video' && (
                      <div className="video-overlay">
                        <span className="play-icon">▶</span>
                        <span className="duration">{formatDuration(item.duration)}</span>
                      </div>
                    )}
                    <span className="source-badge">{item.source_type}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ))
      )}
      {displayedMedia.length < (activeFilter ? activeFilter.items.length : media.length) && (
        <div ref={loader} className="loading-indicator">加载更多...</div>
      )}
    </div>
  );

  const AlbumsView = () => (
    <div className="albums-container">
      <h2>智能分类</h2>
      <div className="gallery-grid">
        {Object.entries(smartAlbums).map(([name, items]) => (
          <div
            key={name}
            className="gallery-item album-card"
            onClick={() => {
              setActiveFilter({ name, items });
              navigate('/');
            }}
          >
            {items.length > 0 && (
              <img
                src={items[0].thumbnail_path ? `/${items[0].thumbnail_path}` : `/api/media/image/${items[0].id}`}
                alt=""
                style={{ filter: 'brightness(0.5)' }}
              />
            )}
            <div className="album-overlay">
              <span className="album-name">{name.toUpperCase()}</span>
              <span className="album-count">{items.length} 项</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-left">
          <h1>Local Smart Gallery</h1>
          <Navigation />
        </div>
        <div className="scan-controls">
          <input
            type="text"
            value={scanPath}
            onChange={(e) => setScanPath(e.target.value)}
            placeholder="输入媒体路径..."
          />
          <button onClick={handleScan} disabled={isScanning}>
            {isScanning ? '扫描中...' : '开始扫描'}
          </button>
          {scanMessage && <div className="scan-feedback">{scanMessage}</div>}
        </div>
      </header>

      <Routes>
        <Route path="/" element={<TimelineView />} />
        <Route path="/map" element={<MapView media={media} openLightbox={openLightbox} />} />
        <Route path="/albums" element={<AlbumsView />} />
      </Routes>

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

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
