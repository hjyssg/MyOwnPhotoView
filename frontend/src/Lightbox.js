import React, { useEffect, useRef } from 'react';
import './Lightbox.css';

const Lightbox = ({ item, onClose, onNext, onPrev }) => {
  const videoRef = useRef(null);

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
        <button className="prev-btn" onClick={onPrev}>‹</button>
        <button className="next-btn" onClick={onNext}>›</button>

        {item.media_type === 'image' ? (
          <img 
            src={`/api/media/image/${item.id}`} 
            alt={item.filepath}
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
