import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import './App.css';
import Lightbox from './Lightbox';
import MapView from './MapView';
import Navigation from './components/Navigation';
import ScanControls from './components/ScanControls';
import TimelinePage from './pages/TimelinePage';
import AlbumsPage from './pages/AlbumsPage';
import DateDetailPage from './pages/DateDetailPage';
import AlbumDetailPage from './pages/AlbumDetailPage';

function AppContent() {
  const [media, setMedia] = useState([]);
  const [displayedMedia, setDisplayedMedia] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [lightboxItems, setLightboxItems] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [scanPath, setScanPath] = useState('C:\\Users\\Administrator\\Desktop\\test');
  const [isScanning, setIsScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState('');
  const [activeFilter, setActiveFilter] = useState(null);
  const [expandedDates, setExpandedDates] = useState(new Set());

  const loaderRef = useRef(null);
  const pageRef = useRef(1);
  const itemsPerPage = 50;

  const smartAlbums = useMemo(
    () => ({
      all: media,
      camera: media.filter((m) => m.source_type === 'camera'),
      screenshot: media.filter((m) => m.source_type === 'screenshot'),
      web: media.filter((m) => m.source_type === 'web'),
      video: media.filter((m) => m.media_type === 'video'),
    }),
    [media]
  );

  const fetchMedia = useCallback(async () => {
    try {
      const response = await axios.get('/api/media');
      setMedia(response.data);
    } catch (error) {
      console.error('Error fetching media:', error);
    }
  }, []);

  useEffect(() => {
    fetchMedia();
  }, [fetchMedia]);

  useEffect(() => {
    pageRef.current = 1;
    if (activeFilter) {
      setDisplayedMedia(activeFilter.items.slice(0, itemsPerPage));
    } else {
      setDisplayedMedia(media.slice(0, itemsPerPage));
    }
  }, [activeFilter, media]);

  const loadMore = useCallback(() => {
    const sourceList = activeFilter ? activeFilter.items : media;
    pageRef.current += 1;
    setDisplayedMedia(sourceList.slice(0, pageRef.current * itemsPerPage));
  }, [activeFilter, media]);

  useEffect(() => {
    const sourceList = activeFilter ? activeFilter.items : media;
    if (!loaderRef.current || displayedMedia.length >= sourceList.length) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          loadMore();
        }
      },
      { root: null, rootMargin: '100px', threshold: 0.1 }
    );

    const currentLoader = loaderRef.current;
    observer.observe(currentLoader);
    return () => observer.unobserve(currentLoader);
  }, [displayedMedia.length, media, activeFilter, loadMore]);

  const openLightboxWithList = useCallback((items, index) => {
    if (!items?.length) return;
    setLightboxItems(items);
    setCurrentIndex(index);
    setSelectedItem(items[index]);
  }, []);

  const closeLightbox = () => setSelectedItem(null);

  const showNext = useCallback(() => {
    if (!lightboxItems.length) return;
    const nextIndex = (currentIndex + 1) % lightboxItems.length;
    setCurrentIndex(nextIndex);
    setSelectedItem(lightboxItems[nextIndex]);
  }, [currentIndex, lightboxItems]);

  const showPrev = useCallback(() => {
    if (!lightboxItems.length) return;
    const prevIndex = (currentIndex - 1 + lightboxItems.length) % lightboxItems.length;
    setCurrentIndex(prevIndex);
    setSelectedItem(lightboxItems[prevIndex]);
  }, [currentIndex, lightboxItems]);

  const handleScan = async () => {
    setIsScanning(true);
    setScanMessage('Scanning...');
    try {
      await axios.post(`/api/scan?directory=${encodeURIComponent(scanPath)}`);
      setScanMessage('Scan completed');
      await fetchMedia();
    } catch (error) {
      console.error('Scan failed:', error);
      setScanMessage('Scan failed');
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

  const toggleDate = (dateKey) => {
    const next = new Set(expandedDates);
    if (next.has(dateKey)) next.delete(dateKey);
    else next.add(dateKey);
    setExpandedDates(next);
  };

  const currentSourceList = activeFilter ? activeFilter.items : media;
  const hasMore = displayedMedia.length < currentSourceList.length;

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-left">
          <h1>Local Smart Gallery</h1>
          <Navigation />
        </div>
        <ScanControls
          scanPath={scanPath}
          setScanPath={setScanPath}
          isScanning={isScanning}
          scanMessage={scanMessage}
          onScan={handleScan}
        />
      </header>

      <Routes>
        <Route
          path="/"
          element={
            <TimelinePage
              displayedMedia={displayedMedia}
              activeFilter={activeFilter}
              setActiveFilter={setActiveFilter}
              smartAlbums={smartAlbums}
              expandedDates={expandedDates}
              toggleDate={toggleDate}
              openLightboxWithList={openLightboxWithList}
              formatDuration={formatDuration}
              loaderRef={loaderRef}
              hasMore={hasMore}
            />
          }
        />
        <Route
          path="/map"
          element={
            <MapView
              media={media}
              openLightbox={(item, index) => openLightboxWithList(media, index)}
            />
          }
        />
        <Route
          path="/albums"
          element={<AlbumsPage smartAlbums={smartAlbums} formatDuration={formatDuration} />}
        />
        <Route
          path="/date/:dateKey"
          element={
            <DateDetailPage
              allMedia={media}
              openLightboxWithList={openLightboxWithList}
              formatDuration={formatDuration}
            />
          }
        />
        <Route
          path="/album/:albumName"
          element={
            <AlbumDetailPage
              allMedia={media}
              openLightboxWithList={openLightboxWithList}
              formatDuration={formatDuration}
            />
          }
        />
      </Routes>

      {selectedItem && (
        <Lightbox item={selectedItem} onClose={closeLightbox} onNext={showNext} onPrev={showPrev} />
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
