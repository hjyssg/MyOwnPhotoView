import React, { useEffect, useRef, useState } from 'react';

const IMAGE_FALLBACK =
  'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect width=%22200%22 height=%22200%22 fill=%22%23222%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dominant-baseline=%22middle%22 fill=%22%23555%22 font-family=%22system-ui%22 font-size=%2214%22%3ENo Preview%3C/text%3E%3C/svg%3E';

const MAX_CONCURRENT = 6;

// ---------------------------------------------------------------------------
// Global concurrency limiter with LIFO semantics + cancellation awareness
// ---------------------------------------------------------------------------
let activeCount = 0;
const waitQueue = []; // { resolve, isCanceled }

function acquireSlot(isCanceled) {
  return new Promise((resolve) => {
    if (activeCount < MAX_CONCURRENT) {
      activeCount += 1;
      resolve();
      return;
    }
    waitQueue.push({ resolve, isCanceled });
  });
}

function releaseSlot() {
  if (activeCount > 0) activeCount -= 1;

  // Drain canceled entries from the back (LIFO) and wake the first live one
  while (waitQueue.length > 0) {
    const entry = waitQueue.pop();
    if (entry.isCanceled()) continue;
    activeCount += 1;
    entry.resolve();
    return;
  }
}

// ---------------------------------------------------------------------------
// LazyImage component
// ---------------------------------------------------------------------------
function LazyImage({ src, alt, className, style }) {
  const [blobUrl, setBlobUrl] = useState(null);
  const [failed, setFailed] = useState(false);
  const containerRef = useRef(null);
  const abortRef = useRef(null);
  const loadedRef = useRef(false); // tracks if current src is already loaded

  // Reset when src changes
  useEffect(() => {
    loadedRef.current = false;

    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }

    setBlobUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
    setFailed(false);
  }, [src]);

  // Main loading effect — driven by IntersectionObserver
  useEffect(() => {
    const node = containerRef.current;
    if (!node || !src) return undefined;

    let canceled = false;
    const isCanceled = () => canceled;

    const startLoad = async () => {
      if (loadedRef.current || canceled) return;

      const controller = new AbortController();
      abortRef.current = controller;

      await acquireSlot(isCanceled);

      if (canceled) {
        releaseSlot();
        return;
      }

      try {
        const resp = await fetch(src, { signal: controller.signal });
        if (!resp.ok) throw new Error(resp.statusText);
        const blob = await resp.blob();

        if (canceled) return; // finally will releaseSlot

        const url = URL.createObjectURL(blob);
        loadedRef.current = true;
        setBlobUrl(url);
      } catch (err) {
        if (err.name !== 'AbortError' && !canceled) {
          setFailed(true);
        }
      } finally {
        releaseSlot();
      }
    };

    const cancel = () => {
      canceled = true;
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
    };

    let observer;
    if (typeof IntersectionObserver !== 'undefined') {
      observer = new IntersectionObserver(
        (entries) => {
          const entry = entries[0];
          if (!entry) return;

          if (entry.isIntersecting) {
            if (!loadedRef.current && canceled) {
              // Re-entered viewport after being canceled — allow retry
              canceled = false;
            }
            startLoad();
          } else if (!loadedRef.current) {
            // Left viewport before load finished — abort
            cancel();
          }
        },
        { root: null, rootMargin: '200px 0px', threshold: 0.01 }
      );
      observer.observe(node);
    } else {
      startLoad();
    }

    return () => {
      cancel();
      observer?.disconnect();
    };
  }, [src]);

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
      setBlobUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
    };
  }, []);

  if (!blobUrl) {
    return (
      <div
        ref={containerRef}
        className={className}
        style={{ ...style, backgroundColor: '#161616' }}
        role="img"
        aria-label={alt}
      />
    );
  }

  return (
    <img
      ref={containerRef}
      src={failed ? IMAGE_FALLBACK : blobUrl}
      alt={alt}
      className={className}
      style={style}
      decoding="async"
    />
  );
}

export default LazyImage;
