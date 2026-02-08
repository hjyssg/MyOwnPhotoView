import React, { useEffect, useRef, useState } from 'react';

const IMAGE_PLACEHOLDER =
  'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect width=%22200%22 height=%22200%22 fill=%22%23161616%22/%3E%3C/svg%3E';
const IMAGE_FALLBACK =
  'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect width=%22200%22 height=%22200%22 fill=%22%23222%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dominant-baseline=%22middle%22 fill=%22%23555%22 font-family=%22system-ui%22 font-size=%2214%22%3ENo Preview%3C/text%3E%3C/svg%3E';
const MOUNT_DELAY_MS = 260;
const MAX_CONCURRENT_IMAGE_LOADS = 6;

let activeImageLoads = 0;
const pendingSlotResolvers = [];

function acquireImageLoadSlot() {
  return new Promise((resolve) => {
    if (activeImageLoads < MAX_CONCURRENT_IMAGE_LOADS) {
      activeImageLoads += 1;
      resolve(() => releaseImageLoadSlot());
      return;
    }

    pendingSlotResolvers.push(resolve);
  });
}

function releaseImageLoadSlot() {
  if (activeImageLoads > 0) {
    activeImageLoads -= 1;
  }

  if (pendingSlotResolvers.length > 0 && activeImageLoads < MAX_CONCURRENT_IMAGE_LOADS) {
    activeImageLoads += 1;
    // 后来者优先：使用 LIFO（栈）而不是 FIFO（队列）
    const nextResolve = pendingSlotResolvers.pop();
    nextResolve(() => releaseImageLoadSlot());
  }
}

function LazyImage({ src, alt, className, style }) {
  const [readyToMountImage, setReadyToMountImage] = useState(false);
  const [shouldRenderImage, setShouldRenderImage] = useState(false);
  const [failed, setFailed] = useState(false);
  const placeholderRef = useRef(null);
  const loadTimerRef = useRef(null);
  const releaseSlotRef = useRef(null);

  useEffect(() => {
    if (releaseSlotRef.current) {
      releaseSlotRef.current();
      releaseSlotRef.current = null;
    }

    setReadyToMountImage(false);
    setShouldRenderImage(false);
    setFailed(false);
  }, [src]);

  useEffect(() => {
    if (readyToMountImage) return undefined;

    const node = placeholderRef.current;
    if (!node) return undefined;
    let observer;

    const clearLoadTimer = () => {
      if (!loadTimerRef.current) return;
      clearTimeout(loadTimerRef.current);
      loadTimerRef.current = null;
    };

    const scheduleRenderImage = () => {
      if (loadTimerRef.current) return;
      loadTimerRef.current = setTimeout(() => {
        setReadyToMountImage(true);
        clearLoadTimer();
        observer?.disconnect();
      }, MOUNT_DELAY_MS);
    };

    if (typeof IntersectionObserver === 'undefined') {
      scheduleRenderImage();
    } else {
      observer = new IntersectionObserver(
        (entries) => {
          const entry = entries[0];
          if (!entry) return;

          if (entry.isIntersecting) {
            scheduleRenderImage();
          } else {
            clearLoadTimer();
          }
        },
        { root: null, rootMargin: '20px 0px', threshold: 0.25 }
      );

      observer.observe(node);
    }

    return () => {
      clearLoadTimer();
      observer?.disconnect();
    };
  }, [readyToMountImage, src]);

  useEffect(() => {
    if (!readyToMountImage || shouldRenderImage) return undefined;

    let canceled = false;

    acquireImageLoadSlot().then((release) => {
      if (canceled) {
        release();
        return;
      }

      releaseSlotRef.current = release;
      setShouldRenderImage(true);
    });

    return () => {
      canceled = true;
    };
  }, [readyToMountImage, shouldRenderImage]);

  useEffect(
    () => () => {
      if (!releaseSlotRef.current) return;
      releaseSlotRef.current();
      releaseSlotRef.current = null;
    },
    []
  );

  const finishCurrentLoad = () => {
    if (!releaseSlotRef.current) return;
    releaseSlotRef.current();
    releaseSlotRef.current = null;
  };

  if (!shouldRenderImage) {
    return (
      <div
        ref={placeholderRef}
        className={className}
        style={{
          ...style,
          backgroundColor: '#161616',
        }}
        role="img"
        aria-label={alt}
      />
    );
  }

  return (
    <img
      src={failed ? IMAGE_FALLBACK : src || IMAGE_PLACEHOLDER}
      alt={alt}
      className={className}
      style={style}
      loading="lazy"
      decoding="async"
      onLoad={finishCurrentLoad}
      onError={() => {
        setFailed(true);
        finishCurrentLoad();
      }}
    />
  );
}

export default LazyImage;
