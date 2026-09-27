import { useEffect, useMemo, useRef } from 'react'
import L from 'leaflet'
import { MapContainer, Marker, Polyline, TileLayer, useMap } from 'react-leaflet'
import type { HistoricalTelemetry } from '../types/history'

interface HistoricalTripMapProps {
  telemetry: HistoricalTelemetry[]
}

function HistoricalViewport({ points }: { points: [number, number][] }) {
  const map = useMap()
  const fittedPointsRef = useRef<string>('')
  const pointsKey = points.map(([latitude, longitude]) => `${latitude},${longitude}`).join('|')

  useEffect(() => {
    if (points.length === 0 || pointsKey === fittedPointsRef.current) return
    fittedPointsRef.current = pointsKey
    map.fitBounds(L.latLngBounds(points), { padding: [36, 36], maxZoom: 15 })
  }, [map, points, pointsKey])

  return null
}

const startIcon = L.divIcon({
  className: 'history-marker-icon',
  html: '<span class="history-marker history-marker-start"></span>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})

const endIcon = L.divIcon({
  className: 'history-marker-icon',
  html: '<span class="history-marker history-marker-end"></span>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})

export function HistoricalTripMap({ telemetry }: HistoricalTripMapProps) {
  const points = useMemo(
    () => telemetry
      .filter((item) => Number.isFinite(item.latitude) && Number.isFinite(item.longitude))
      .map((item) => [item.latitude, item.longitude] as [number, number]),
    [telemetry],
  )

  return (
    <div className="historical-map-frame">
      <MapContainer className="historical-map" center={[20, 0]} zoom={3} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <HistoricalViewport points={points} />
        {points.length > 1 && <Polyline positions={points} pathOptions={{ color: '#e7795b', weight: 4 }} />}
        {points[0] && <Marker position={points[0]} icon={startIcon} />}
        {points.length > 1 && <Marker position={points[points.length - 1]} icon={endIcon} />}
      </MapContainer>
      {points.length === 0 && <div className="history-map-empty">No valid GPS points for this trip.</div>}
    </div>
  )
}