import { useEffect, useRef } from 'react'
import L from 'leaflet'
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import type { Vehicle } from '../types/vehicle'
import type { Trip } from '../types/trip'
import type { PlannedRoute } from '../types/route'

export interface VehicleView extends Vehicle {
  activeTrip: Trip | undefined
  latitude: number | null
  longitude: number | null
  temperature: number | null
  humidity: number | null
  dew_point: number | null
  elevation: number | null
  liveRecordedAt: string | null
}

interface FleetMapProps {
  vehicles: VehicleView[]
  selectedVehicleId: number | null
  centerRequest: number
  onSelectVehicle: (vehicleId: number) => void
  plannedRoute?: PlannedRoute | null
}

function MapViewport({ vehicles, selectedVehicleId, centerRequest }: Pick<FleetMapProps, 'vehicles' | 'selectedVehicleId' | 'centerRequest'>) {
  const map = useMap()
  const hasFittedRef = useRef(false)
  const lastCenterRequestRef = useRef(0)
  const positionedVehicles = vehicles.filter(
    (vehicle) => vehicle.latitude !== null && vehicle.longitude !== null,
  )

  useEffect(() => {
    if (hasFittedRef.current || positionedVehicles.length === 0) return
    const bounds = L.latLngBounds(
      positionedVehicles.map((vehicle) => [vehicle.latitude!, vehicle.longitude!] as [number, number]),
    )
    map.fitBounds(bounds, { padding: [48, 48], maxZoom: 14 })
    hasFittedRef.current = true
  }, [map, positionedVehicles])

  useEffect(() => {
    if (centerRequest === 0 || centerRequest === lastCenterRequestRef.current || selectedVehicleId === null) return
    lastCenterRequestRef.current = centerRequest
    const selected = vehicles.find((vehicle) => vehicle.id === selectedVehicleId)
    if (selected && selected.latitude !== null && selected.longitude !== null) {
      map.flyTo([selected.latitude!, selected.longitude!], Math.max(map.getZoom(), 13), {
        duration: 0.6,
      })
    }
  }, [centerRequest, map, selectedVehicleId, vehicles])

  return null
}

function markerIcon(isSelected: boolean, isOnline: boolean) {
  return L.divIcon({
    className: 'vehicle-marker-icon',
    html: `<span class="vehicle-marker ${isSelected ? 'is-selected' : ''} ${isOnline ? 'is-online' : ''}"></span>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  })
}

function formatCoordinate(value: number | null) {
  return value === null ? 'No location' : value.toFixed(5)
}

export function FleetMap({
  vehicles,
  selectedVehicleId,
  centerRequest,
  onSelectVehicle,
  plannedRoute,
}: FleetMapProps) {
  return (
    <div className="map-frame">
      <MapContainer className="fleet-map" center={[20, 0]} zoom={3} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapViewport
          vehicles={vehicles}
          selectedVehicleId={selectedVehicleId}
          centerRequest={centerRequest}
        />
        {plannedRoute && plannedRoute.points.length > 1 && (
          <Polyline
            positions={plannedRoute.points.map((point) => [point.latitude, point.longitude] as [number, number])}
            pathOptions={{ color: '#236b8e', weight: 4, dashArray: '8 8' }}
          />
        )}
        {vehicles.map((vehicle) => {
          if (vehicle.latitude === null || vehicle.longitude === null) return null
          const isSelected = vehicle.id === selectedVehicleId
          return (
            <Marker
              key={vehicle.id}
              position={[vehicle.latitude, vehicle.longitude]}
              icon={markerIcon(isSelected, vehicle.is_online)}
              eventHandlers={{ click: () => onSelectVehicle(vehicle.id) }}
            >
              <Popup>
                <div className="map-popup">
                  <strong>{vehicle.name}</strong>
                  <span>{vehicle.device_id}</span>
                  <span className={vehicle.is_online ? 'status-online' : 'status-offline'}>
                    {vehicle.is_online ? 'Backend online' : 'Backend offline'}
                  </span>
                  <span>Lat {formatCoordinate(vehicle.latitude)}</span>
                  <span>Lng {formatCoordinate(vehicle.longitude)}</span>
                  {vehicle.activeTrip && <span>Trip #{vehicle.activeTrip.id}</span>}
                </div>
              </Popup>
            </Marker>
          )
        })}
      </MapContainer>
      {vehicles.every((vehicle) => vehicle.latitude === null || vehicle.longitude === null) && (
        <div className="map-empty">Waiting for vehicle coordinates</div>
      )}
    </div>
  )
}