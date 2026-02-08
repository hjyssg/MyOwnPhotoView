import React, { useEffect, useRef, useState } from 'react';

const IMAGE_PLACEHOLDER =
  'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect width=%22200%22 height=%22200%22 fill=%22%23161616%22/%3E%3C/svg%3E';
const IMAGE_FALLBACK =
  'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect width=%22200%22 height=%22200%22 fill=%22%23222%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dominant-baseline=%22middle%22 fill=%22%23555%22 font-family=%22system-ui%22 font-size=%2214%22%3ENo Preview%3C/text%3E%3C/svg%3E';

function LazyImage({ src, alt, className, style }) {
  const [shouldLoad, setShouldLoad] = useState(false);
  const [failed, setFailed] = useState(false);
  const imgRef = useRef(null);
  const loadTimerRef = useRef(null);

  useEffect(() => {
    setShouldLoad(false);
    setFailed(false);
  }, [src]);

  useEffect(() => {
    const node = imgRef.current;
    if (!node) return undefined;

    const clearLoadTimer = () => {
      if (!loadTimerRef.current) return;
      clearTimeout(loadTimerRef.current);
      loadTimerRef.current = null;
    };

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (!entry) return;

        if (entry.isIntersecting) {
          if (!loadTimerRef.current) {
            loadTimerRef.current = setTimeout(() => {
              setShouldLoad(true);
              clearLoadTimer();
              observer.disconnect();
            }, 120);
          }
        } else {
          clearLoadTimer();
        }
      },
      { root: null, rootMargin: '80px 0px', threshold: 0.15 }
    );

    observer.observe(node);
    return () => {
      clearLoadTimer();
      observer.disconnect();
    };
  }, []);

  return (
    <img
      ref={imgRef}
      src={failed ? IMAGE_FALLBACK : shouldLoad ? src : IMAGE_PLACEHOLDER}
      alt={alt}
      className={className}
      style={style}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
    />
  );
}

export default LazyImage;
