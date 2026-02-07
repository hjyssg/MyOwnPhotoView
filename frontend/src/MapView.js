import React, { useEffect, useMemo, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMapEvents } from 'react-leaflet';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
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

function getClusterCellByZoom(zoom) {
    if (zoom <= 4) return 2.5;
    if (zoom <= 6) return 1.0;
    if (zoom <= 8) return 0.4;
    if (zoom <= 10) return 0.15;
    return 0.06;
}

function ClusteredLocationMarkers({ locations }) {
    const navigate = useNavigate();
    const [zoom, setZoom] = useState(5);

    useMapEvents({
        zoomend(e) {
            setZoom(e.target.getZoom());
        },
    });

    const clusters = useMemo(() => {
        const cell = getClusterCellByZoom(zoom);
        const map = new Map();

        locations.forEach((loc) => {
            const lat = Number(loc.center_latitude);
            const lon = Number(loc.center_longitude);
            if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

            const latBucket = Math.floor(lat / cell);
            const lonBucket = Math.floor(lon / cell);
            const key = `${latBucket}:${lonBucket}`;

            if (!map.has(key)) {
                map.set(key, {
                    key,
                    sumLat: 0,
                    sumLon: 0,
                    locationCount: 0,
                    mediaCount: 0,
                    items: [],
                });
            }

            const bucket = map.get(key);
            bucket.sumLat += lat;
            bucket.sumLon += lon;
            bucket.locationCount += 1;
            bucket.mediaCount += Number(loc.count || 0);
            bucket.items.push(loc);
        });

        return Array.from(map.values()).map((c) => ({
            ...c,
            centerLat: c.sumLat / c.locationCount,
            centerLon: c.sumLon / c.locationCount,
        }));
    }, [locations, zoom]);

    return (
        <>
            {clusters.map((cluster) => {
                const single = cluster.locationCount === 1;
                const first = cluster.items[0];
                const iconForCluster =
                    single
                        ? DefaultIcon
                        : L.divIcon({
                            className: 'map-cluster-icon',
                            html: `<div class="cluster-badge">${cluster.locationCount}</div>`,
                            iconSize: [34, 34],
                            iconAnchor: [17, 17],
                        });

                return (
                    <Marker
                        key={cluster.key}
                        position={[cluster.centerLat, cluster.centerLon]}
                        icon={iconForCluster}
                    >
                        <Popup>
                            {single ? (
                                <div className="map-popup">
                                    <div className="map-popup-title">{first.location_city || '未知地点'}</div>
                                    <div className="map-popup-sub">{first.count} 张照片</div>
                                    <button
                                        className="map-popup-btn"
                                        onClick={() => navigate(`/location/${encodeURIComponent(first.location_key)}`)}
                                    >
                                        打开地点页
                                    </button>
                                </div>
                            ) : (
                                <div className="map-popup">
                                    <div className="map-popup-title">已聚合 {cluster.locationCount} 个地点</div>
                                    <div className="map-popup-sub">共 {cluster.mediaCount} 张照片</div>
                                    <div className="map-popup-sub">继续放大地图可拆分</div>
                                </div>
                            )}
                        </Popup>
                    </Marker>
                );
            })}
        </>
    );
}

const MapView = () => {
    const [locations, setLocations] = useState([]);

    useEffect(() => {
        let canceled = false;
        const load = async () => {
            try {
                const res = await axios.get('/api/locations');
                if (!canceled) setLocations(res.data || []);
            } catch (e) {
                if (!canceled) setLocations([]);
            }
        };
        load();
        return () => {
            canceled = true;
        };
    }, []);

    const center = locations.length > 0
        ? [locations[0].center_latitude, locations[0].center_longitude]
        : [31.2304, 121.4737];

    return (
        <div className="map-page-shell">
            <div className="map-frame">
                <MapContainer center={center} zoom={5} style={{ height: '100%', width: '100%' }}>
                    <TileLayer
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    <ClusteredLocationMarkers locations={locations} />
                </MapContainer>
            </div>
        </div>
    );
};

export default MapView;
