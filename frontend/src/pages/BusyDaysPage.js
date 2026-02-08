import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link, useSearchParams } from 'react-router-dom';
import {
  normalizeBooleanFlagParam,
  normalizeNumberEnumParam,
  readBooleanFlagParam,
  readNumberEnumParam,
  withBooleanFlagParam,
  withParam,
} from '../utils/urlState';

const MIN_COUNT_OPTIONS = [10, 50, 100, 300, 500];
const MIN_COUNT_DEFAULT = 300;

function BusyDaysPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const minCount = readNumberEnumParam(searchParams, 'minCount', MIN_COUNT_OPTIONS, MIN_COUNT_DEFAULT);
  const onlyCamera = readBooleanFlagParam(searchParams, 'onlyCamera', '1');

  useEffect(() => {
    let next = normalizeNumberEnumParam(searchParams, 'minCount', MIN_COUNT_OPTIONS, MIN_COUNT_DEFAULT);
    if (!next) next = normalizeBooleanFlagParam(searchParams, 'onlyCamera', '1');
    if (next) setSearchParams(next, { replace: true });
  }, [minCount, onlyCamera, searchParams, setSearchParams]);

  const updateMinCount = (value) => {
    const next = withParam(searchParams, 'minCount', value, { defaultValue: MIN_COUNT_DEFAULT });
    setSearchParams(next, { replace: true });
  };

  const updateOnlyCamera = (enabled) => {
    const next = withBooleanFlagParam(searchParams, 'onlyCamera', enabled, '1');
    setSearchParams(next, { replace: true });
  };

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

  return (
    <div className="gallery-container busy-days-page">
      <h2>高产日期</h2>

      <div className="busy-days-toolbar">
        <label>
          最小数量
          <select value={minCount} onChange={(e) => updateMinCount(Number(e.target.value))}>
            {MIN_COUNT_OPTIONS.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>

        <label className="busy-days-check">
          <input
            type="checkbox"
            checked={onlyCamera}
            onChange={(e) => updateOnlyCamera(e.target.checked)}
          />
          仅相机拍摄
        </label>
      </div>

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
