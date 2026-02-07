import React from 'react';

function ScanControls({ scanPath, setScanPath, isScanning, scanMessage, onScan }) {
  return (
    <div className="scan-controls">
      <input
        type="text"
        value={scanPath}
        onChange={(e) => setScanPath(e.target.value)}
        placeholder="Input media path..."
      />
      <button onClick={onScan} disabled={isScanning}>
        {isScanning ? 'Scanning...' : 'Start Scan'}
      </button>
      {scanMessage && <div className="scan-feedback">{scanMessage}</div>}
    </div>
  );
}

export default ScanControls;
