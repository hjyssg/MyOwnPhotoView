import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';

function SettingsPage({ onScanCompleted, showToast }) {
  const [folderItems, setFolderItems] = useState([]);
  const [newFolder, setNewFolder] = useState('');
  const [isAddFormOpen, setIsAddFormOpen] = useState(false);
  const [isSyncingConfig, setIsSyncingConfig] = useState(false);
  const [isSyncingSettings, setIsSyncingSettings] = useState(false);
  const [isPurgingSoftDeleted, setIsPurgingSoftDeleted] = useState(false);
  const [isCleaningUnusedThumbnails, setIsCleaningUnusedThumbnails] = useState(false);
  const [appSettings, setAppSettings] = useState({
    auto_scan_on_startup: false,
    scan_mode: 'incremental',
  });
  const [scanStatus, setScanStatus] = useState({
    is_running: false,
    directory: null,
    message: 'idle',
    error: null,
  });
  const prevRunningRef = useRef(false);

  const loadFolders = useCallback(async () => {
    try {
      const res = await axios.get('/api/scan/folders');
      const items = Array.isArray(res.data?.items)
        ? res.data.items
        : (Array.isArray(res.data?.folders) ? res.data.folders : []).map((path) => ({
            path,
            has_scanned: false,
            scanned_count: 0,
          }));
      setFolderItems(items);
    } catch (error) {
      console.error('Failed to load scan folders', error);
      showToast?.('Load scan folders failed', 'error');
    }
  }, [showToast]);

  const loadScanStatus = useCallback(async () => {
    try {
      const res = await axios.get('/api/scan/status');
      setScanStatus(res.data || {});
    } catch (error) {
      console.error('Failed to load scan status', error);
    }
  }, []);

  const loadSettings = useCallback(async () => {
    try {
      const res = await axios.get('/api/settings');
      const next = {
        auto_scan_on_startup: !!res.data?.auto_scan_on_startup,
        scan_mode: res.data?.scan_mode === 'force' ? 'force' : 'incremental',
      };
      setAppSettings(next);
    } catch (error) {
      console.error('Failed to load settings', error);
      showToast?.('Load settings failed', 'error');
    }
  }, [showToast]);

  useEffect(() => {
    loadFolders();
    loadScanStatus();
    loadSettings();
  }, [loadFolders, loadScanStatus, loadSettings]);

  useEffect(() => {
    if (!scanStatus?.is_running) return undefined;
    const timer = setInterval(loadScanStatus, 1500);
    return () => clearInterval(timer);
  }, [scanStatus?.is_running, loadScanStatus]);

  useEffect(() => {
    const wasRunning = prevRunningRef.current;
    const isRunning = !!scanStatus?.is_running;

    if (wasRunning && !isRunning) {
      loadFolders();
      onScanCompleted?.();
    }

    prevRunningRef.current = isRunning;
  }, [scanStatus?.is_running, loadFolders, onScanCompleted]);

  const saveFolders = async (nextFolders, toastMessage = 'Scan folders updated') => {
    setIsSyncingConfig(true);
    try {
      const res = await axios.put('/api/scan/folders', { folders: nextFolders });
      const savedFolders = Array.isArray(res.data?.folders) ? res.data.folders : [];
      const softDeletedCount = Number(res.data?.soft_deleted_count || 0);
      const details = await axios.get('/api/scan/folders');
      const items = Array.isArray(details.data?.items)
        ? details.data.items
        : savedFolders.map((path) => ({ path, has_scanned: false, scanned_count: 0 }));
      setFolderItems(items);
      if (softDeletedCount > 0) {
        showToast?.(`${toastMessage}（已软删除 ${softDeletedCount} 条）`, 'success');
      } else {
        showToast?.(toastMessage, 'success');
      }
      onScanCompleted?.();
    } catch (error) {
      console.error('Failed to save scan folders', error);
      showToast?.('Update scan folders failed', 'error');
    } finally {
      setIsSyncingConfig(false);
    }
  };

  const saveSettings = async (nextSettings, toastMessage = 'Settings updated') => {
    setIsSyncingSettings(true);
    try {
      const payload = {
        auto_scan_on_startup: !!nextSettings.auto_scan_on_startup,
        scan_mode: nextSettings.scan_mode === 'force' ? 'force' : 'incremental',
      };
      const res = await axios.put('/api/settings', payload);
      setAppSettings({
        auto_scan_on_startup: !!res.data?.auto_scan_on_startup,
        scan_mode: res.data?.scan_mode === 'force' ? 'force' : 'incremental',
      });
      showToast?.(toastMessage, 'success');
    } catch (error) {
      console.error('Failed to save settings', error);
      showToast?.('Save settings failed', 'error');
    } finally {
      setIsSyncingSettings(false);
    }
  };

  const addFolder = async () => {
    const value = newFolder.trim();
    if (!value) {
      showToast?.('Please input folder path', 'error');
      return;
    }

    const existing = folderItems.map((item) => item.path);
    if (existing.some((p) => p.toLowerCase() === value.toLowerCase())) {
      showToast?.('Folder already exists', 'error');
      return;
    }

    await saveFolders([...existing, value], 'Folder added to config');
    setNewFolder('');
    setIsAddFormOpen(false);
  };

  const cancelAddFolder = () => {
    setNewFolder('');
    setIsAddFormOpen(false);
  };

  const removeFolder = async (path) => {
    const next = folderItems
      .map((item) => item.path)
      .filter((p) => p.toLowerCase() !== path.toLowerCase());
    await saveFolders(next, 'Folder removed from config');
  };

  const runSingleScan = async (folder) => {
    try {
      const res = await axios.post(`/api/scan?directory=${encodeURIComponent(folder)}`);
      if (res.data?.status === 'running') {
        showToast?.('已有扫描任务正在运行', 'error');
      } else {
        showToast?.('Scan started', 'success');
      }
      await loadScanStatus();
    } catch (error) {
      console.error('Scan failed', error);
      showToast?.('Scan failed', 'error');
    }
  };

  const runAllScan = async () => {
    try {
      const res = await axios.post('/api/scan/all');
      if (res.data?.status === 'running') {
        showToast?.('已有扫描任务正在运行', 'error');
      } else {
        showToast?.('Scan all started', 'success');
      }
      await loadScanStatus();
    } catch (error) {
      console.error('Scan all failed', error);
      showToast?.('Scan all failed', 'error');
    }
  };

  const purgeSoftDeletedItems = async () => {
    const confirmed = window.confirm('确定要彻底删除已软删除的数据吗？该操作不可恢复。');
    if (!confirmed) return;

    setIsPurgingSoftDeleted(true);
    try {
      const res = await axios.post('/api/maintenance/purge-soft-deleted');
      const deletedItems = Number(res.data?.deleted_media_items || 0);
      const deletedThumbs = Number(res.data?.deleted_thumbnails || 0);
      showToast?.(`Purge done: media ${deletedItems}, thumbnails ${deletedThumbs}`, 'success');
      await loadFolders();
      onScanCompleted?.();
    } catch (error) {
      console.error('Purge soft-deleted items failed', error);
      showToast?.('Purge soft-deleted items failed', 'error');
    } finally {
      setIsPurgingSoftDeleted(false);
    }
  };

  const cleanupUnusedThumbnails = async () => {
    const confirmed = window.confirm('确定要删除未使用的缩略图吗？');
    if (!confirmed) return;

    setIsCleaningUnusedThumbnails(true);
    try {
      const res = await axios.post('/api/thumbnails/cleanup-unused');
      const deleted = Number(res.data?.deleted_thumbnails || 0);
      const kept = Number(res.data?.kept_thumbnails || 0);
      showToast?.(`Cleanup done: deleted ${deleted}, kept ${kept}`, 'success');
    } catch (error) {
      console.error('Cleanup unused thumbnails failed', error);
      showToast?.('Cleanup unused thumbnails failed', 'error');
    } finally {
      setIsCleaningUnusedThumbnails(false);
    }
  };

  const statusText = useMemo(() => {
    if (scanStatus?.is_running) {
      return '扫描中';
    }
    if (scanStatus?.message === 'completed') return 'Last scan completed';
    if (scanStatus?.message === 'failed') return `Failed: ${scanStatus.error || 'unknown error'}`;
    return 'Idle';
  }, [scanStatus]);

  const etaText = useMemo(() => {
    if (!scanStatus?.is_running) return '';

    const startedAtMs = Date.parse(scanStatus?.started_at || '');
    const processed = Number(scanStatus?.processed_files || 0);
    const total = Number(scanStatus?.total_files || 0);

    if (!Number.isFinite(startedAtMs) || startedAtMs <= 0) {
      return '预计完成时间：计算中...';
    }

    if (!(total > 0) || processed <= 0 || processed >= total) {
      return '预计完成时间：计算中...';
    }

    const elapsedSec = Math.max(1, (Date.now() - startedAtMs) / 1000);
    const speed = processed / elapsedSec;
    if (!(speed > 0)) {
      return '预计完成时间：计算中...';
    }

    const remainingSec = Math.max(1, Math.round((total - processed) / speed));
    const etaDate = new Date(Date.now() + remainingSec * 1000);

    const hh = String(etaDate.getHours()).padStart(2, '0');
    const mm = String(etaDate.getMinutes()).padStart(2, '0');
    const ss = String(etaDate.getSeconds()).padStart(2, '0');

    const remMin = Math.floor(remainingSec / 60);
    const remSec = remainingSec % 60;
    return `预计完成时间：${hh}:${mm}:${ss}（约 ${remMin} 分 ${remSec} 秒后）`;
  }, [scanStatus]);

  const folderMetaText = useCallback(
    (item) => {
      const isCurrentFolder =
        !!scanStatus?.is_running &&
        !!scanStatus?.current_folder &&
        item.path.toLowerCase() === String(scanStatus.current_folder).toLowerCase();

      if (isCurrentFolder) {
        const processed = Number(scanStatus?.processed_files || 0);
        const total = Number(scanStatus?.total_files || 0);
        return total > 0 ? `扫描中 ${processed}/${total}` : '扫描中...';
      }

      if (item.has_scanned) {
        return `已扫描 (${item.scanned_count})`;
      }

      return '未扫描（需手动触发）';
    },
    [scanStatus]
  );

  return (
    <div className="gallery-container">
      <h2>Settings</h2>

      <div className="scan-page-panel">
        <div className="scan-status" style={{ marginBottom: 8, fontWeight: 700, color: 'var(--text-primary)' }}>
          Scan Behavior
        </div>

        <div className="scan-status" style={{ marginBottom: 10 }}>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <input
              type="checkbox"
              checked={appSettings.auto_scan_on_startup}
              onChange={(e) =>
                saveSettings(
                  { ...appSettings, auto_scan_on_startup: e.target.checked },
                  'Auto scan setting updated'
                )
              }
              disabled={isSyncingSettings || scanStatus?.is_running}
            />
            Auto scan all folders on startup
          </label>
        </div>

        <div className="scan-status" style={{ marginBottom: 14 }}>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            Scan mode:
            <select
              value={appSettings.scan_mode}
              onChange={(e) =>
                saveSettings({ ...appSettings, scan_mode: e.target.value }, 'Scan mode updated')
              }
              disabled={isSyncingSettings || scanStatus?.is_running}
              style={{
                background: 'rgba(255, 255, 255, 0.75)',
                border: '1px solid var(--line)',
                color: 'var(--text-primary)',
                padding: '0.56rem 0.7rem',
                borderRadius: 9,
                outline: 'none',
              }}
            >
              <option value="incremental">Incremental (skip unchanged files)</option>
              <option value="force">Force rescan (rescan all files)</option>
            </select>
          </label>
        </div>

        <div className="scan-status" style={{ marginTop: 4, marginBottom: 10, fontWeight: 700, color: 'var(--text-primary)' }}>
          Folder Management
        </div>

        {/* <div className="scan-status">Status: {statusText}</div> */}
        {!!etaText && <div className="scan-status" style={{ opacity: 0.9 }}>{etaText}</div>}

        {folderItems.length === 0 ? (
          <div className="empty-state">No scan folders configured</div>
        ) : (
          <ul className="scan-folder-list">
            {folderItems.map((item, idx) => (
              <li key={`${item.path}-${idx}`} className="scan-folder-item">
                <span title={item.path}>{item.path}</span>
                <span className="scan-folder-meta" style={{ marginLeft: 8, fontSize: 12, opacity: 0.85 }}>
                  {folderMetaText(item)}
                </span>
                <div className="scan-folder-actions">
                  <button onClick={() => runSingleScan(item.path)} disabled={scanStatus?.is_running}>
                    {item.has_scanned ? 'Rescan' : 'Scan'}
                  </button>
                  <button
                    onClick={() => removeFolder(item.path)}
                    disabled={scanStatus?.is_running || isSyncingConfig}
                  >
                    Remove
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}

        <div className="scan-add-row" style={{ marginTop: 12, marginBottom: 10 }}>
          <button
            onClick={() => setIsAddFormOpen(true)}
            disabled={isSyncingConfig || scanStatus?.is_running || isAddFormOpen}
          >
            Add New
          </button>
          <button onClick={runAllScan} disabled={scanStatus?.is_running || folderItems.length === 0}>
            Scan All
          </button>
        </div>

        {isAddFormOpen && (
          <div className="scan-add-row" style={{ marginBottom: 0 }}>
            <input
              type="text"
              value={newFolder}
              onChange={(e) => setNewFolder(e.target.value)}
              placeholder="Input folder path..."
            />
            <button onClick={addFolder} disabled={isSyncingConfig || scanStatus?.is_running}>
              {isSyncingConfig ? 'Saving...' : 'Save'}
            </button>
            <button onClick={cancelAddFolder} disabled={isSyncingConfig || scanStatus?.is_running}>
              Cancel
            </button>
          </div>
        )}

        <div className="scan-status" style={{ marginTop: 16, marginBottom: 8, fontWeight: 700, color: 'var(--text-primary)' }}>
          Maintenance
        </div>
        <div className="scan-add-row" style={{ marginTop: 0, marginBottom: 0 }}>
          <button
            onClick={cleanupUnusedThumbnails}
            disabled={
              scanStatus?.is_running ||
              isCleaningUnusedThumbnails ||
              isPurgingSoftDeleted
            }
          >
            {isCleaningUnusedThumbnails ? 'Cleaning...' : 'Delete unused thumbnails'}
          </button>
          <button
            onClick={purgeSoftDeletedItems}
            disabled={
              scanStatus?.is_running ||
              isPurgingSoftDeleted ||
              isCleaningUnusedThumbnails
            }
          >
            {isPurgingSoftDeleted ? 'Purging...' : 'Permanently delete soft-deleted items'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;