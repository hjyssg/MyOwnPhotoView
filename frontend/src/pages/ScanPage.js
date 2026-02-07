import React, { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';

function ScanPage({ onScanCompleted, showToast }) {
  const [folderItems, setFolderItems] = useState([]);
  const [newFolder, setNewFolder] = useState('');
  const [isSyncingConfig, setIsSyncingConfig] = useState(false);
  const [scanStatus, setScanStatus] = useState({
    is_running: false,
    directory: null,
    message: 'idle',
    error: null,
  });

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

  useEffect(() => {
    loadFolders();
    loadScanStatus();
  }, [loadFolders, loadScanStatus]);

  useEffect(() => {
    if (!scanStatus?.is_running) return undefined;
    const timer = setInterval(loadScanStatus, 1500);
    return () => clearInterval(timer);
  }, [scanStatus?.is_running, loadScanStatus]);

  const saveFolders = async (nextFolders, toastMessage = 'Scan folders updated') => {
    setIsSyncingConfig(true);
    try {
      const res = await axios.put('/api/scan/folders', { folders: nextFolders });
      const savedFolders = Array.isArray(res.data?.folders) ? res.data.folders : [];
      // 保存后重新读取，拿到 has_scanned/scanned_count 状态
      const details = await axios.get('/api/scan/folders');
      const items = Array.isArray(details.data?.items)
        ? details.data.items
        : savedFolders.map((path) => ({ path, has_scanned: false, scanned_count: 0 }));
      setFolderItems(items);
      showToast?.(toastMessage, 'success');
    } catch (error) {
      console.error('Failed to save scan folders', error);
      showToast?.('Update scan folders failed', 'error');
    } finally {
      setIsSyncingConfig(false);
    }
  };

  const addFolder = async () => {
    const value = newFolder.trim();
    if (!value) return;

    const existing = folderItems.map((item) => item.path);
    if (existing.some((p) => p.toLowerCase() === value.toLowerCase())) {
      showToast?.('Folder already exists', 'error');
      return;
    }

    await saveFolders([...existing, value], 'Folder added to config');
    setNewFolder('');
  };

  const removeFolder = async (path) => {
    const next = folderItems
      .map((item) => item.path)
      .filter((p) => p.toLowerCase() !== path.toLowerCase());
    await saveFolders(next, 'Folder removed from config');
  };

  const runSingleScan = async (folder) => {
    try {
      await axios.post(`/api/scan?directory=${encodeURIComponent(folder)}`);
      showToast?.('Scan started', 'success');
      await loadScanStatus();
      await loadFolders();
      await onScanCompleted?.();
    } catch (error) {
      console.error('Scan failed', error);
      showToast?.('Scan failed', 'error');
    }
  };

  const runAllScan = async () => {
    try {
      await axios.post('/api/scan/all');
      showToast?.('Scan all started', 'success');
      await loadScanStatus();
      await loadFolders();
      await onScanCompleted?.();
    } catch (error) {
      console.error('Scan all failed', error);
      showToast?.('Scan all failed', 'error');
    }
  };

  const statusText = useMemo(() => {
    if (scanStatus?.is_running) return `Running: ${scanStatus.message || scanStatus.directory || ''}`;
    if (scanStatus?.message === 'completed') return 'Last scan completed';
    if (scanStatus?.message === 'failed') return `Failed: ${scanStatus.error || 'unknown error'}`;
    return 'Idle';
  }, [scanStatus]);

  return (
    <div className="gallery-container">
      <h2>Scan Folders</h2>

      <div className="scan-page-panel">
        <div className="scan-add-row">
          <input
            type="text"
            value={newFolder}
            onChange={(e) => setNewFolder(e.target.value)}
            placeholder="Input folder path..."
          />
          <button onClick={addFolder} disabled={isSyncingConfig || scanStatus?.is_running}>
            {isSyncingConfig ? 'Updating...' : 'Add'}
          </button>
          <button onClick={runAllScan} disabled={scanStatus?.is_running || folderItems.length === 0}>
            Scan All
          </button>
        </div>

        <div className="scan-status">Status: {statusText}</div>

        {folderItems.length === 0 ? (
          <div className="empty-state">No scan folders configured</div>
        ) : (
          <ul className="scan-folder-list">
            {folderItems.map((item, idx) => (
              <li key={`${item.path}-${idx}`} className="scan-folder-item">
                <span title={item.path}>{item.path}</span>
                <span className="scan-folder-meta" style={{ marginLeft: 8, fontSize: 12, opacity: 0.85 }}>
                  {item.has_scanned ? `已扫描 (${item.scanned_count})` : '未扫描（需手动触发）'}
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
      </div>
    </div>
  );
}

export default ScanPage;
