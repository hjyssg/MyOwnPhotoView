import React, { useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

// 修复 Leaflet 默认图标加载问题
let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

const MapView = ({ media, openLightbox }) => {
    const mediaWithLocation = useMemo(() => {
        return media.filter(m => m.latitude && m.longitude);
    }, [media]);

    const center = mediaWithLocation.length > 0
        ? [mediaWithLocation[0].latitude, mediaWithLocation[0].longitude]
        : [35.6895, 139.6917]; // 默认东京

    return (
        <div style={{ height: 'calc(100vh - 80px)', width: '100%', borderRadius: '12px', overflow: 'hidden' }}>
            <MapContainer center={center} zoom={5} style={{ height: '100%', width: '100%' }}>
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                {mediaWithLocation.map((item, index) => {
                    // 找到原始列表中的 index 以便打开 Lightbox
                    const globalIndex = media.findIndex(m => m.id === item.id);
                    return (
                        <Marker key={item.id} position={[item.latitude, item.longitude]}>
                            <Popup>
                                <div style={{ width: '150px', cursor: 'pointer' }} onClick={() => openLightbox(item, globalIndex)}>
                                    <img
                                        src={`/thumbnails/${item.id}.jpg`}
                                        alt="location"
                                        style={{ width: '100%', borderRadius: '8px' }}
                                        onError={(e) => e.target.src = `/api/media/image/${item.id}`} // 回退
                                    />
                                    <p style={{ margin: '5px 0 0', fontSize: '12px', textAlign: 'center' }}>
                                        {new Date(item.created_at).toLocaleDateString()}
                                    </p>
                                </div>
                            </Popup>
                        </Marker>
                    );
                })}
            </MapContainer>
        </div>
    );
};

export default MapView;
