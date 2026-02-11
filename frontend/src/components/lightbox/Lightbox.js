import React, { useCallback, useMemo, useState } from 'react';
import YARLightbox from 'yet-another-react-lightbox';
import Video from 'yet-another-react-lightbox/plugins/video';
import Zoom from 'yet-another-react-lightbox/plugins/zoom';
import 'yet-another-react-lightbox/styles.css';
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

function InfoButton({ onClick }) {
  return (
    <button
      type="button"
      className="yarl__button yarl-info-btn"
      onClick={onClick}
      aria-label="显示信息"
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
      </svg>
    </button>
  );
}

function TrashButton({ onClick }) {
  return (
    <button
      type="button"
      className="yarl__button yarl-trash-btn"
      onClick={onClick}
      aria-label="删除"
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polyline points="3 6 5 6 21 6" />
        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      </svg>
    </button>
  );
}

function InfoPanel({ item }) {
  if (!item) return null;
  return (
    <div className="yarl-info-panel">
      <div className="meta-row"><strong>Path:</strong> {item.filepath || 'Unknown'}</div>
      <div className="meta-row"><strong>Time:</strong> {formatDateTime(item.created_at)}</div>
      <div className="meta-row">
        <strong>Type:</strong> {item.media_type || 'unknown'} · {item.source_type || 'unknown'}
      </div>
      <div className="meta-row"><strong>Size:</strong> {formatFileSize(item.size)}</div>
      {!!item.location_name && (
        <div className="meta-row"><strong>Location:</strong> {item.location_name}</div>
      )}
      {item.media_type === 'video' && item.duration != null && (
        <div className="meta-row"><strong>Duration:</strong> {Math.floor(item.duration)}s</div>
      )}
    </div>
  );
}

const Lightbox = ({ item, items = [], currentIndex = 0, onClose, onTrashItem }) => {
  const [showInfo, setShowInfo] = useState(false);
  const [viewIndex, setViewIndex] = useState(currentIndex);

  const slides = useMemo(() =>
    items.map((mediaItem) => {
      if (mediaItem.media_type === 'video') {
        return {
          type: 'video',
          sources: [{ src: `/api/media/stream/${mediaItem.id}`, type: 'video/mp4' }],
          autoPlay: true,
          controls: true,
          controlsList: 'nodownload',
          width: 1920,
          height: 1080,
        };
      }
      return {
        src: `/api/media/image/${mediaItem.id}`,
        alt: mediaItem.filepath || '',
      };
    }),
    [items]
  );

  const currentMediaItem = items[viewIndex] || item;

  const handleTrash = useCallback(async () => {
    if (!currentMediaItem || !onTrashItem) return;
    const filename = (currentMediaItem.filepath || '').split(/[\\/]/).pop() || currentMediaItem.id;
    const confirmed = window.confirm(`确定要将此文件移到回收站吗？\n\n${filename}`);
    if (!confirmed) return;
    await onTrashItem(currentMediaItem.id);
  }, [currentMediaItem, onTrashItem]);

  const toggleInfo = useCallback(() => {
    setShowInfo((v) => !v);
  }, []);

  if (!item) return null;

  return (
    <YARLightbox
      open
      close={onClose}
      index={currentIndex}
      slides={slides}
      plugins={[Video, Zoom]}
      on={{
        view: ({ index }) => {
          setViewIndex(index);
          setShowInfo(false);
        },
      }}
      video={{
        autoPlay: true,
        controls: true,
        controlsList: 'nodownload',
        playsInline: true,
      }}
      carousel={{
        preload: 2,
      }}
      animation={{
        fade: 300,
      }}
      controller={{
        closeOnBackdropClick: true,
      }}
      toolbar={{
        buttons: [
          <InfoButton key="info" onClick={toggleInfo} />,
          <TrashButton key="trash" onClick={handleTrash} />,
          'close',
        ],
      }}
      render={{
        slideFooter: () =>
          showInfo ? <InfoPanel item={currentMediaItem} /> : null,
      }}
    />
  );
};

export default Lightbox;
