import React, { useEffect, useRef, useState } from 'react';
import './Lightbox.css';

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

const Lightbox = ({ item, items = [], currentIndex = 0, onClose, onNext, onPrev }) => {
  const videoRef = useRef(null);
  const preloadRef = useRef({ timer: null, img: null });
  const [showInfo, setShowInfo] = useState(false);
  const [isCurrentImageLoaded, setIsCurrentImageLoaded] = useState(false);

  useEffect(() => {
    setShowInfo(false);
    setIsCurrentImageLoaded(false);
  }, [item?.id]);

  useEffect(() => {
    if (!item || item.media_type !== 'image' || !items.length || !isCurrentImageLoaded) return;

    const clearPreload = () => {
      if (preloadRef.current.timer) {
        clearTimeout(preloadRef.current.timer);
      }
      if (preloadRef.current.img) {
        preloadRef.current.img.src = '';
      }
      preloadRef.current = { timer: null, img: null };
    };

    const preload = (mediaItem) => {
      if (!mediaItem || mediaItem.media_type !== 'image') return;
      const img = new Image();
      img.decoding = 'async';
      img.fetchPriority = 'low';
      img.src = `/api/media/image/${mediaItem.id}`;
      preloadRef.current.img = img;
    };

    let offset = 1;
    let nextImage = null;
    while (offset < items.length) {
      const idx = (currentIndex + offset) % items.length;
      if (items[idx]?.media_type === 'image') {
        nextImage = items[idx];
        break;
      }
      offset += 1;
    }

    preloadRef.current.timer = setTimeout(() => preload(nextImage), 120);

    return clearPreload;
  }, [item, items, currentIndex, isCurrentImageLoaded]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowRight') {
        onNext();
      } else if (e.key === 'ArrowLeft') {
        onPrev();
      } else if (e.key === ' ' && videoRef.current) {
        e.preventDefault();
        if (videoRef.current.paused) {
          videoRef.current.play();
        } else {
          videoRef.current.pause();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [onClose, onNext, onPrev]);

  return (
    <div className="lightbox-backdrop" onClick={onClose}>
      <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>×</button>
        <button
          className="info-btn"
          onClick={() => setShowInfo((v) => !v)}
          aria-label="显示信息"
          title="显示信息"
        >
          i
        </button>
        <button className="prev-btn" onClick={onPrev}>‹</button>
        <button className="next-btn" onClick={onNext}>›</button>

        {showInfo && (
          <div className="lightbox-info-panel">
            <div className="meta-row"><strong>Path:</strong> {item.filepath || 'Unknown'}</div>
            <div className="meta-row"><strong>Time:</strong> {formatDateTime(item.created_at)}</div>
            <div className="meta-row">
              <strong>Type:</strong> {item.media_type || 'unknown'} · {item.source_type || 'unknown'}
            </div>
            <div className="meta-row"><strong>Size:</strong> {formatFileSize(item.size)}</div>
            {!!item.location_name && <div className="meta-row"><strong>Location:</strong> {item.location_name}</div>}
            {item.media_type === 'video' && (
              <div className="meta-row"><strong>Duration:</strong> {Math.floor(item.duration || 0)}s</div>
            )}
          </div>
        )}

        {item.media_type === 'image' ? (
          <img 
            src={`/api/media/image/${item.id}`} 
            alt={item.filepath}
            decoding="auto"
            loading="eager"
            fetchPriority="high"
            onLoad={() => setIsCurrentImageLoaded(true)}
            onError={(e) => {
              console.error('大图加载失败:', item.id);
            }}
          />
        ) : (
          <video
            ref={videoRef}
            src={`/api/media/stream/${item.id}`}
            controls
            autoPlay
            controlsList="nodownload"
            onError={(e) => {
              console.error('视频加载失败:', item.id, e);
            }}
          />
        )}
      </div>
    </div>
  );
};

export default Lightbox;
