import React, { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';

function ScanPage({ onScanCompleted, showToast }) {
  const [folders, setFolders] = useState([]);
  const [newFolder, setNewFolder] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [scanStatus, setScanStatus] = useState({
    is_running: false,
    directory: null,
    message: 'idle',
    error: null,
  });

  const loadFolders = useCallback(async () => {
    try {
      const res = await axios.get('/api/scan/folders');
      setFolders(Array.isArray(res.data?.folders) ? res.data.folders : []);
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

  const saveFolders = async (nextFolders) => {
    setIsSaving(true);
    try {
      const res = await axios.put('/api/scan/folders', { folders: nextFolders });
      setFolders(Array.isArray(res.data?.folders) ? res.data.folders : []);
      showToast?.('Scan folders saved', 'success');
    } catch (error) {
      console.error('Failed to save scan folders', error);
      showToast?.('Save scan folders failed', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const addFolder = () => {
    const val = newFolder.trim();
    if (!val) return;
    setFolders((prev) => {
      if (prev.some((p) => p.toLowerCase() === val.toLowerCase())) return prev;
      return [...prev, val];
    });
    setNewFolder('');
  };

  const removeFolder = (idx) => {
    setFolders((prev) => prev.filter((_, i) => i !== idx));
  };

  const runSingleScan = async (folder) => {
    try {
      await axios.post(`/api/scan?directory=${encodeURIComponent(folder)}`);
      showToast?.('Scan started', 'success');
      await loadScanStatus();
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
          <button onClick={addFolder}>Add</button>
          <button onClick={() => saveFolders(folders)} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save'}
          </button>
          <button onClick={runAllScan} disabled={scanStatus?.is_running || folders.length === 0}>
            Scan All
          </button>
        </div>

        <div className="scan-status">Status: {statusText}</div>

        {folders.length === 0 ? (
          <div className="empty-state">No scan folders configured</div>
        ) : (
          <ul className="scan-folder-list">
            {folders.map((folder, idx) => (
              <li key={`${folder}-${idx}`} className="scan-folder-item">
                <span title={folder}>{folder}</span>
                <div className="scan-folder-actions">
                  <button onClick={() => runSingleScan(folder)} disabled={scanStatus?.is_running}>
                    Scan
                  </button>
                  <button onClick={() => removeFolder(idx)} disabled={scanStatus?.is_running}>
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
