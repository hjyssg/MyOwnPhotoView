import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { BrowserRouter as Router, Route, Routes, Link, useLocation, useNavigate } from 'react-router-dom';
import './App.css';
import Lightbox from './components/lightbox/Lightbox';
import MapView from './components/map/MapView';
import Navigation from './components/Navigation';
import TimelinePage from './pages/TimelinePage';
import AlbumsPage from './pages/AlbumsPage';
import DateDetailPage from './pages/DateDetailPage';
import AlbumDetailPage from './pages/AlbumDetailPage';
import LocationDetailPage from './pages/LocationDetailPage';
import SettingsPage from './pages/SettingsPage';
import BusyDaysPage from './pages/BusyDaysPage';
import {
  normalizeCsvEnumSetParam,
  readCsvEnumSetParam,
  withCsvEnumSetParam,
} from './utils/urlState';

const AVAILABLE_FILTER_KEYS = ['camera', 'screenshot', 'video', 'etc'];

function AppContent() {
  const matchesFilter = useCallback((item, filterKey) => {
    if (filterKey === 'video') return item.media_type === 'video';
    if (filterKey === 'camera') return item.source_type === 'camera';
    if (filterKey === 'screenshot') return item.source_type === 'screenshot';
    if (filterKey === 'etc') {
      const source = item.source_type;
      return item.media_type !== 'video' && source !== 'camera' && source !== 'screenshot';
    }
    return false;
  }, []);

  const location = useLocation();
  const navigate = useNavigate();
  const [media, setMedia] = useState([]);
  const [mediaLoading, setMediaLoading] = useState(true);
  const [displayedMedia, setDisplayedMedia] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [lightboxItems, setLightboxItems] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [toast, setToast] = useState(null);
  const [expandedDates, setExpandedDates] = useState(new Set());

  const loaderRef = useRef(null);
  const toastTimerRef = useRef(null);
  const hasShownSetupToastRef = useRef(false);
  const pageRef = useRef(1);
  const itemsPerPage = 3000;

  const showToast = useCallback((message, type = 'success') => {
    setToast({ message, type });
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => {
      setToast(null);
    }, 2600);
  }, []);

  const smartAlbums = useMemo(
    () => ({
      all: media,
      camera: media.filter((m) => m.source_type === 'camera'),
      screenshot: media.filter((m) => m.source_type === 'screenshot'),
      web: media.filter((m) => m.source_type === 'web'),
      video: media.filter((m) => m.media_type === 'video'),
      etc: media.filter(
        (m) => m.media_type !== 'video' && m.source_type !== 'camera' && m.source_type !== 'screenshot'
      ),
    }),
    [media]
  );

  const activeFilters = useMemo(() => {
    if (location.pathname !== '/') return new Set();

    const params = new URLSearchParams(location.search);
    return new Set(readCsvEnumSetParam(params, 'filters', AVAILABLE_FILTER_KEYS));
  }, [location.pathname, location.search]);

  useEffect(() => {
    if (location.pathname !== '/') return;

    const next = normalizeCsvEnumSetParam(
      new URLSearchParams(location.search),
      'filters',
      AVAILABLE_FILTER_KEYS
    );
    if (!next) return;

    navigate(
      {
        pathname: location.pathname,
        search: next.toString() ? `?${next.toString()}` : '',
      },
      { replace: true }
    );
  }, [location.pathname, location.search, navigate]);

  const filteredSourceMedia = useMemo(() => {
    if (!activeFilters.size) return media;
    return media.filter((item) => {
      for (const key of activeFilters) {
        if (matchesFilter(item, key)) return true;
      }
      return false;
    });
  }, [media, activeFilters, matchesFilter]);

  const fetchMedia = useCallback(async () => {
    setMediaLoading(true);
    try {
      const response = await axios.get('/api/media');
      setMedia(response.data);
    } catch (error) {
      console.error('Error fetching media:', error);
    } finally {
      setMediaLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMedia();
  }, [fetchMedia]);

  useEffect(() => {
    if (location.pathname !== '/') return;
    if (hasShownSetupToastRef.current) return;
    if (media.length > 0) return;

    let cancelled = false;
    const checkScanSetup = async () => {
      try {
        const res = await axios.get('/api/scan/folders');
        if (cancelled) return;

        const items = Array.isArray(res.data?.items) ? res.data.items : [];
        const hasConfiguredFolders = items.length > 0;
        const hasAnyScanned = items.some((item) => !!item?.has_scanned);

        if (!hasConfiguredFolders || !hasAnyScanned) {
          hasShownSetupToastRef.current = true;
          showToast('Please go to Settings to add folders and run Scan.', 'error');
        }
      } catch (_) {
        // ignore guidance toast failure
      }
    };

    checkScanSetup();
    return () => {
      cancelled = true;
    };
  }, [media, location.pathname, showToast]);

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
  }, []);

  useEffect(() => {
    pageRef.current = 1;
    setDisplayedMedia(filteredSourceMedia.slice(0, itemsPerPage));
  }, [filteredSourceMedia]);

  const loadMore = useCallback(() => {
    pageRef.current += 1;
    setDisplayedMedia(filteredSourceMedia.slice(0, pageRef.current * itemsPerPage));
  }, [filteredSourceMedia]);

  useEffect(() => {
    if (!loaderRef.current || displayedMedia.length >= filteredSourceMedia.length) return undefined;

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
  }, [displayedMedia.length, filteredSourceMedia.length, loadMore]);

  const openLightboxWithList = useCallback((items, index) => {
    if (!items?.length) return;
    setLightboxItems(items);
    setCurrentIndex(index);
    setSelectedItem(items[index]);
  }, []);

  const closeLightbox = () => setSelectedItem(null);

  const handleTrashItem = useCallback(
    async (itemId) => {
      if (!itemId) return false;
      try {
        await axios.post(`/api/media/${itemId}/trash`);
      } catch (error) {
        const message =
          error?.response?.data?.detail ||
          error?.message ||
          'Move to recycle bin failed.';
        showToast(message, 'error');
        return false;
      }

      const removedItem = lightboxItems.find((it) => it.id === itemId) || media.find((it) => it.id === itemId);
      const filename =
        (removedItem?.filepath || '').split(/[\\/]/).pop() ||
        removedItem?.filepath ||
        'file';

      setMedia((prev) => prev.filter((m) => m.id !== itemId));

      const idx = lightboxItems.findIndex((m) => m.id === itemId);
      if (idx < 0) {
        showToast(`Moved to recycle bin: ${filename}`);
        return true;
      }

      const nextItems = lightboxItems.filter((m) => m.id !== itemId);
      if (!nextItems.length) {
        setLightboxItems([]);
        setSelectedItem(null);
        setCurrentIndex(0);
      } else {
        const nextIndex = idx >= nextItems.length ? 0 : idx;
        setLightboxItems(nextItems);
        setCurrentIndex(nextIndex);
        setSelectedItem(nextItems[nextIndex]);
      }

      showToast(`Moved to recycle bin: ${filename}`);
      return true;
    },
    [lightboxItems, media, showToast]
  );

  const handleToggleFilter = useCallback(
    (filterKey) => {
      if (location.pathname !== '/') return;

      const current = new Set(activeFilters);

      if (filterKey === 'all') {
        current.clear();
      } else if (AVAILABLE_FILTER_KEYS.includes(filterKey)) {
        if (current.has(filterKey)) current.delete(filterKey);
        else current.add(filterKey);
      }

      const nextFilters = Array.from(current);
      const next = withCsvEnumSetParam(new URLSearchParams(location.search), 'filters', nextFilters);

      navigate(
        {
          pathname: location.pathname,
          search: next.toString() ? `?${next.toString()}` : '',
        },
        { replace: true }
      );
    },
    [activeFilters, location.pathname, location.search, navigate]
  );

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

  const currentSourceList = filteredSourceMedia;
  const hasMore = displayedMedia.length < currentSourceList.length;

  useEffect(() => {
    const appName = 'Local Smart Gallery';
    const { pathname } = location;

    const decodePathPart = (value) => {
      try {
        return decodeURIComponent(value || '');
      } catch (_) {
        return value || '';
      }
    };

    const pathParts = pathname.split('/').filter(Boolean);
    let pageTitle = 'Timeline';

    if (pathname === '/') pageTitle = 'Timeline';
    else if (pathname === '/map') pageTitle = 'Map';
    else if (pathname === '/albums') pageTitle = 'Albums';
    else if (pathname === '/busy-days') pageTitle = 'Busy Days';
    else if (pathname === '/settings' || pathname === '/scan') pageTitle = 'Settings';
    else if (pathParts[0] === 'album' && pathParts[1]) {
      pageTitle = `Album · ${decodePathPart(pathParts[1])}`;
    } else if (pathParts[0] === 'location' && pathParts[1]) {
      pageTitle = `Location · ${decodePathPart(pathParts[1])}`;
    } else if (pathParts[0] === 'date' && pathParts[1]) {
      if (pathParts[1] === 'day' && pathParts[2]) pageTitle = `Date · ${decodePathPart(pathParts[2])}`;
      else if (pathParts[1] === 'month' && pathParts[2]) pageTitle = `Month · ${decodePathPart(pathParts[2])}`;
      else if (pathParts[1] === 'year' && pathParts[2]) pageTitle = `Year · ${decodePathPart(pathParts[2])}`;
      else pageTitle = `Date · ${decodePathPart(pathParts[1])}`;
    }

    document.title = `${pageTitle} | ${appName}`;
  }, [location]);

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-left">
          <h1>
            <Link to="/" className="home-link">Local Smart Gallery</Link>
          </h1>
          <Navigation />
        </div>
      </header>

      <Routes>
        <Route
          path="/"
          element={
            <TimelinePage
              sourceMedia={currentSourceList}
              displayedMedia={displayedMedia}
              mediaLoading={mediaLoading}
              activeFilters={activeFilters}
              onToggleFilter={handleToggleFilter}
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
          element={<MapView />}
        />
        <Route
          path="/albums"
          element={<AlbumsPage smartAlbums={smartAlbums} formatDuration={formatDuration} />}
        />
        <Route
          path="/busy-days"
          element={<BusyDaysPage />}
        />
        <Route
          path="/date/day/:dateKey"
          element={
            <DateDetailPage
              allMedia={media}
              openLightboxWithList={openLightboxWithList}
              formatDuration={formatDuration}
              granularity="day"
              matchesFilter={matchesFilter}
            />
          }
        />
        <Route
          path="/date/month/:dateKey"
          element={
            <DateDetailPage
              allMedia={media}
              openLightboxWithList={openLightboxWithList}
              formatDuration={formatDuration}
              granularity="month"
              matchesFilter={matchesFilter}
            />
          }
        />
        <Route
          path="/date/year/:dateKey"
          element={
            <DateDetailPage
              allMedia={media}
              openLightboxWithList={openLightboxWithList}
              formatDuration={formatDuration}
              granularity="year"
              matchesFilter={matchesFilter}
            />
          }
        />
        <Route
          path="/date/:dateKey"
          element={
            <DateDetailPage
              allMedia={media}
              openLightboxWithList={openLightboxWithList}
              formatDuration={formatDuration}
              granularity="day"
              matchesFilter={matchesFilter}
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
        <Route
          path="/location/:locationKey"
          element={
            <LocationDetailPage
              allMedia={media}
              openLightboxWithList={openLightboxWithList}
              formatDuration={formatDuration}
            />
          }
        />
        <Route
          path="/settings"
          element={<SettingsPage onScanCompleted={fetchMedia} showToast={showToast} />}
        />
        <Route
          path="/scan"
          element={<SettingsPage onScanCompleted={fetchMedia} showToast={showToast} />}
        />
      </Routes>

      {selectedItem && (
        <Lightbox
          item={selectedItem}
          items={lightboxItems}
          currentIndex={currentIndex}
          onClose={closeLightbox}
          onTrashItem={handleTrashItem}
        />
      )}

      {toast && <div className={`toast toast-${toast.type}`}>{toast.message}</div>}
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
