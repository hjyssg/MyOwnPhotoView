import React, { useEffect } from 'react';
import './Lightbox.css';

const Lightbox = ({ item, onClose, onNext, onPrev }) => {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowRight') onNext();
      if (e.key === 'ArrowLeft') onPrev();
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
          <img src={`/${item.filepath}`} alt={item.filepath} />
        ) : (
          <video
            src={`/api/media/stream/${item.id}`}
            controls
            autoPlay
            onKeyDown={(e) => {
              if (e.key === ' ') {
                e.preventDefault();
                e.currentTarget.paused ? e.currentTarget.play() : e.currentTarget.pause();
              }
            }}
          />
        )}
      </div>
    </div>
  );
};

export default Lightbox;
