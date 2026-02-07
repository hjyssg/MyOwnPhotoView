import React from 'react';

function ScanControls({ scanPath, setScanPath, isScanning, onScan }) {
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
    </div>
  );
}

export default ScanControls;
