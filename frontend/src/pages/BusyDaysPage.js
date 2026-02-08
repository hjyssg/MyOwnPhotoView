import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

function BusyDaysPage() {
  const [items, setItems] = useState([]);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [minCount, setMinCount] = useState(30);
  const [onlyCamera, setOnlyCamera] = useState(false);

  useEffect(() => {
    let canceled = false;
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const res = await axios.get('/api/stats/busy-days', {
          params: {
            order: 'asc',
            min_count: minCount,
            only_camera: onlyCamera,
            limit: 500,
          },
        });
        if (canceled) return;
        setItems(res.data?.items || []);
        setMeta(res.data?.meta || null);
      } catch (e) {
        if (!canceled) {
          setError('加载高产日期失败，请稍后重试');
        }
      } finally {
        if (!canceled) setLoading(false);
      }
    };

    load();
    return () => {
      canceled = true;
    };
  }, [minCount, onlyCamera]);

  const thresholdText = useMemo(() => {
    if (!meta?.thresholds) return '';
    const t = meta.thresholds;
    return `阈值：绝对下限 ${t.abs_floor}；相对阈值 ${t.relative}（中位数 × 2.5）；异常阈值 ${t.outlier}（Q3 + 1.5×IQR）`;
  }, [meta]);

  return (
    <div className="gallery-container busy-days-page">
      <h2>高产日期</h2>

      <div className="busy-days-toolbar">
        <label>
          最小数量
          <select value={minCount} onChange={(e) => setMinCount(Number(e.target.value))}>
            {[20, 30, 50, 80, 100].map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>

        <label className="busy-days-check">
          <input
            type="checkbox"
            checked={onlyCamera}
            onChange={(e) => setOnlyCamera(e.target.checked)}
          />
          仅相机拍摄
        </label>
      </div>

      {thresholdText && <div className="busy-days-note">{thresholdText}</div>}

      {loading ? (
        <div className="loading-indicator">
          <span className="loading-spinner" aria-label="Loading" />
        </div>
      ) : error ? (
        <div className="empty-state">{error}</div>
      ) : items.length === 0 ? (
        <div className="empty-state">没有命中“高产日”，可以降低最小数量再试。</div>
      ) : (
        <div className="busy-days-list">
          {items.map((row) => (
            <Link key={row.date_key} to={`/date/day/${row.date_key}`} className="busy-day-row">
              <div className="busy-day-main">
                <div className="busy-day-date">{row.date_key}</div>
                <div className="busy-day-city">{row.top_location_city || '—'}</div>
                <div className="busy-day-count">{row.count} items</div>
              </div>

              <div className="busy-day-thumbs" aria-label="当天预览">
                {(row.preview_items || []).slice(0, 5).map((preview) => {
                  const src = preview.thumbnail_path
                    ? `/${preview.thumbnail_path}`
                    : `/api/media/image/${preview.id}`;
                  return (
                    <div key={preview.id} className="busy-day-thumb">
                      <img src={src} alt="" loading="lazy" />
                    </div>
                  );
                })}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default BusyDaysPage;
