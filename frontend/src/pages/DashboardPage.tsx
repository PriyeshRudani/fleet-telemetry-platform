import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { exportTripTelemetry, getTripTelemetry } from '../api/history'
import { getTripRoute, getTripRouteStatus, isMissingRouteError, uploadTripRoute } from '../api/routes'
import { getTrips, startTrip, stopTrip } from '../api/trips'
import { getVehicles } from '../api/vehicles'
import { useAuth } from '../auth/AuthContext'
import { FleetMap, type VehicleView } from '../components/FleetMap'
import { HistoricalTripMap } from '../components/HistoricalTripMap'
import { TemperatureChart } from '../components/TemperatureChart'
import { useTelemetryWebSocket, type WebSocketStatus } from '../realtime/useTelemetryWebSocket'
import type { TelemetryEvent } from '../types/telemetry'
import type { HistoricalTelemetry } from '../types/history'
import type { PlannedRoute, RouteDeviationStatus } from '../types/route'
import type { Trip } from '../types/trip'
import type { Vehicle } from '../types/vehicle'

const VEHICLE_OFFLINE_THRESHOLD_MS = 15_000

function formatTimestamp(value: string | null) {
  if (!value) return 'No telemetry yet'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function formatNumber(value: number | null, digits = 1) {
  return value === null ? '—' : value.toFixed(digits)
}

function hasRecentTelemetry(timestamp: string | null, now: number) {
  if (!timestamp) return false
  const recordedAt = Date.parse(timestamp)
  return Number.isFinite(recordedAt) && now - recordedAt <= VEHICLE_OFFLINE_THRESHOLD_MS
}

function connectionLabel(status: WebSocketStatus) {
  return status === 'CONNECTED' ? 'Connected' : status === 'RECONNECTING' ? 'Reconnecting' : status === 'CONNECTING' ? 'Connecting' : 'Disconnected'
}

export function DashboardPage() {
  const { currentUser, token, logout } = useAuth()
  const navigate = useNavigate()
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [trips, setTrips] = useState<Trip[]>([])
  const [liveTelemetry, setLiveTelemetry] = useState<Record<number, TelemetryEvent>>({})
  const [selectedVehicleId, setSelectedVehicleId] = useState<number | null>(null)
  const [centerRequest, setCenterRequest] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [actionError, setActionError] = useState('')
  const [actionVehicleId, setActionVehicleId] = useState<number | null>(null)
  const [statusClock, setStatusClock] = useState(() => Date.now())
  const [historyVehicleId, setHistoryVehicleId] = useState<number | null>(null)
  const [historyTripId, setHistoryTripId] = useState<number | null>(null)
  const [historicalTelemetry, setHistoricalTelemetry] = useState<HistoricalTelemetry[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState('')
  const [historyExporting, setHistoryExporting] = useState(false)
  const [historyExportError, setHistoryExportError] = useState('')
  const [plannedRoute, setPlannedRoute] = useState<PlannedRoute | null>(null)
  const [routeStatus, setRouteStatus] = useState<RouteDeviationStatus | null>(null)
  const [routeFile, setRouteFile] = useState<File | null>(null)
  const [routeLoading, setRouteLoading] = useState(false)
  const [routeError, setRouteError] = useState('')

  useEffect(() => {
    const timer = window.setInterval(() => setStatusClock(Date.now()), 5000)
    return () => window.clearInterval(timer)
  }, [])

  function handleUnauthorized() {
    logout()
    navigate('/login', { replace: true })
  }

  async function refreshFleet() {
    if (!token) return
    setLoadError('')
    try {
      const [nextVehicles, nextTrips] = await Promise.all([getVehicles(token), getTrips(token)])
      setVehicles(nextVehicles)
      setTrips(nextTrips)
      setSelectedVehicleId((current) => current ?? nextVehicles[0]?.id ?? null)
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        handleUnauthorized()
      } else {
        setLoadError(error instanceof ApiError ? error.message : 'The fleet data is unavailable right now.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void refreshFleet()
  }, [token])

  useEffect(() => {
    setHistoryTripId(null)
    setHistoricalTelemetry([])
    setHistoryError('')
    setHistoryExportError('')
  }, [historyVehicleId])

  useEffect(() => {
    if (!token || historyTripId === null) return

    let active = true
    setHistoryLoading(true)
    setHistoryError('')
    setHistoricalTelemetry([])
    getTripTelemetry(token, historyTripId)
      .then((telemetry) => {
        if (active) setHistoricalTelemetry(telemetry)
      })
      .catch((error) => {
        if (!active) return
        if (error instanceof ApiError && error.status === 401) {
          handleUnauthorized()
        } else {
          setHistoryError(error instanceof ApiError ? error.message : 'Unable to load historical telemetry.')
        }
      })
      .finally(() => {
        if (active) setHistoryLoading(false)
      })

    return () => {
      active = false
    }
  }, [historyTripId, token])

  function handleTelemetry(event: TelemetryEvent) {
    setLiveTelemetry((current) => ({ ...current, [event.vehicle_id]: event }))
  }

  const websocketStatus = useTelemetryWebSocket(
    token,
    handleTelemetry,
    currentUser?.organization_id ?? null,
  )

  const activeTrips = trips.filter((trip) => trip.status === 'ACTIVE')
  const activeTripByVehicle = new Map(activeTrips.map((trip) => [trip.vehicle_id, trip]))
  const vehicleViews: VehicleView[] = vehicles.map((vehicle) => {
    const live = liveTelemetry[vehicle.id]
    const lastSeenAt = live?.recorded_at ?? vehicle.last_seen_at
    const isOnline = live
      ? hasRecentTelemetry(live.recorded_at, statusClock)
      : vehicle.is_online && hasRecentTelemetry(vehicle.last_seen_at, statusClock)
    return {
      ...vehicle,
      is_online: isOnline,
      last_seen_at: lastSeenAt,
      activeTrip: activeTripByVehicle.get(vehicle.id),
      latitude: live?.latitude ?? vehicle.latest_latitude,
      longitude: live?.longitude ?? vehicle.latest_longitude,
      temperature: live?.temperature ?? null,
      humidity: live?.humidity ?? null,
      dew_point: live?.dew_point ?? null,
      elevation: live?.elevation ?? null,
      liveRecordedAt: live?.recorded_at ?? null,
    }
  })
  const selectedVehicle = vehicleViews.find((vehicle) => vehicle.id === selectedVehicleId) ?? null
  const selectedActiveTripId = selectedVehicle?.activeTrip?.id ?? null

  useEffect(() => {
    setPlannedRoute(null)
    setRouteStatus(null)
    setRouteFile(null)
    setRouteError('')
    if (!token || selectedActiveTripId === null) return

    let active = true
    setRouteLoading(true)
    Promise.all([
      getTripRoute(token, selectedActiveTripId).catch((error) => {
        if (isMissingRouteError(error)) return null
        throw error
      }),
      getTripRouteStatus(token, selectedActiveTripId),
    ])
      .then(([route, status]) => {
        if (!active) return
        setPlannedRoute(route)
        setRouteStatus(status)
      })
      .catch((error) => {
        if (!active) return
        if (error instanceof ApiError && error.status === 401) {
          handleUnauthorized()
        } else {
          setRouteError('Unable to load planned route status.')
        }
      })
      .finally(() => {
        if (active) setRouteLoading(false)
      })

    return () => {
      active = false
    }
  }, [selectedActiveTripId, token])

  const historicalTrips = historyVehicleId === null
    ? []
    : trips.filter((trip) => trip.vehicle_id === historyVehicleId && trip.status === 'COMPLETED')
  const historicalVehicle = vehicles.find((vehicle) => vehicle.id === historyVehicleId)
  const historicalTrip = trips.find((trip) => trip.id === historyTripId)

  async function handleHistoryExport() {
    if (!token || historyTripId === null || historyExporting) return
    setHistoryExporting(true)
    setHistoryExportError('')
    try {
      const { blob, filename } = await exportTripTelemetry(token, historyTripId)
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = filename ?? `trip-${historyTripId}-telemetry.csv`
      link.click()
      URL.revokeObjectURL(objectUrl)
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        handleUnauthorized()
      } else {
        setHistoryExportError('Unable to export telemetry.')
      }
    } finally {
      setHistoryExporting(false)
    }
  }

  async function handleRouteUpload() {
    if (!token || selectedActiveTripId === null || !routeFile || routeLoading) return
    setRouteLoading(true)
    setRouteError('')
    try {
      const route = await uploadTripRoute(token, selectedActiveTripId, routeFile)
      const status = await getTripRouteStatus(token, selectedActiveTripId)
      setPlannedRoute(route)
      setRouteStatus(status)
      setRouteFile(null)
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        handleUnauthorized()
      } else {
        setRouteError(error instanceof ApiError ? error.message : 'Unable to upload planned route.')
      }
    } finally {
      setRouteLoading(false)
    }
  }

  async function handleTripAction(vehicle: VehicleView) {
    if (!token) return
    setActionError('')
    setActionVehicleId(vehicle.id)
    try {
      if (vehicle.activeTrip) {
        await stopTrip(token, vehicle.activeTrip.id)
      } else {
        await startTrip(token, vehicle.id)
      }
      await refreshFleet()
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        handleUnauthorized()
      } else {
        setActionError(error instanceof ApiError ? error.message : 'The trip action could not be completed.')
      }
    } finally {
      setActionVehicleId(null)
    }
  }

  const organizationLabel = currentUser?.organization_id === null
    ? 'All organizations'
    : `Organization ${currentUser?.organization_id}`

  return (
    <main className="dashboard-shell live-dashboard">
      <header className="topbar">
        <div className="topbar-brand">
          <div className="brand-mark brand-mark-small">FT</div>
          <div>
            <p className="topbar-title">Fleet Telemetry Platform</p>
            <p className="topbar-subtitle">Live operations</p>
          </div>
        </div>
        <div className="account-area">
          <div className="account-copy">
            <strong>{currentUser?.email ?? 'Authenticated operator'}</strong>
            <span>{currentUser?.role} · {organizationLabel}</span>
          </div>
          <button className="button-quiet" type="button" onClick={() => { logout(); navigate('/login', { replace: true }) }}>Log out</button>
        </div>
      </header>

      <section className="dashboard-content live-content">
        <div className="dashboard-heading live-heading">
          <div>
            <p className="eyebrow">Fleet control room</p>
            <h1>Live fleet view</h1>
            <p className="dashboard-copy">The map reflects real vehicle data and authorized telemetry as it arrives.</p>
          </div>
          <div className={`session-badge ws-${websocketStatus.toLowerCase()}`}><span /> WebSocket {connectionLabel(websocketStatus)}</div>
        </div>

        <div className="summary-grid" aria-label="Fleet summary">
          <div className="summary-item"><span>Total vehicles</span><strong>{vehicles.length}</strong></div>
          <div className="summary-item"><span>Backend online</span><strong>{vehicleViews.filter((vehicle) => vehicle.is_online).length}</strong></div>
          <div className="summary-item"><span>Backend offline</span><strong>{vehicleViews.filter((vehicle) => !vehicle.is_online).length}</strong></div>
          <div className="summary-item"><span>Active trips</span><strong>{activeTrips.length}</strong></div>
        </div>

        {loadError && <div className="dashboard-alert" role="alert">{loadError}</div>}
        {isLoading ? (
          <div className="dashboard-loading">Loading fleet data...</div>
        ) : (
          <div className="operations-grid">
            <section className="map-panel panel-surface">
              <div className="section-heading">
                <div><p className="card-label">Live map</p><h2>Vehicles in motion</h2></div>
                <span className="map-count">{vehicleViews.filter((vehicle) => vehicle.latitude !== null && vehicle.longitude !== null).length} located</span>
              </div>
              <FleetMap
                vehicles={vehicleViews}
                selectedVehicleId={selectedVehicleId}
                centerRequest={centerRequest}
                onSelectVehicle={setSelectedVehicleId}
                plannedRoute={plannedRoute}
              />
            </section>

            <section className="vehicle-panel panel-surface">
              <div className="section-heading"><div><p className="card-label">Fleet list</p><h2>Vehicles</h2></div></div>
              {vehicleViews.length === 0 ? (
                <p className="empty-state">No vehicles are visible for this account.</p>
              ) : (
                <div className="vehicle-list">
                  {vehicleViews.map((vehicle) => (
                    <button
                      className={`vehicle-card ${selectedVehicleId === vehicle.id ? 'is-selected' : ''}`}
                      key={vehicle.id}
                      type="button"
                      onClick={() => setSelectedVehicleId(vehicle.id)}
                    >
                      <span className={`vehicle-dot ${vehicle.is_online ? 'is-online' : ''}`} />
                      <span className="vehicle-card-copy"><strong>{vehicle.name}</strong><span>{vehicle.device_id}</span></span>
                      <span className="vehicle-card-meta">{vehicle.activeTrip ? `Trip #${vehicle.activeTrip.id}` : 'No active trip'}</span>
                    </button>
                  ))}
                </div>
              )}
            </section>

            <section className="details-panel panel-surface">
              <div className="section-heading"><div><p className="card-label">Selected vehicle</p><h2>{selectedVehicle?.name ?? 'Choose a vehicle'}</h2></div></div>
              {!selectedVehicle ? (
                <p className="empty-state">Select a vehicle to inspect its live state.</p>
              ) : (
                <div className="details-layout">
                  <div className="detail-identity"><span>{selectedVehicle.device_id}</span><strong className={selectedVehicle.is_online ? 'status-online' : 'status-offline'}>{selectedVehicle.is_online ? 'Backend online' : 'Backend offline'}</strong><small>Last telemetry: {formatTimestamp(selectedVehicle.liveRecordedAt ?? selectedVehicle.last_seen_at)}</small></div>
                  <div className="metric-grid">
                    <div><span>Latitude</span><strong>{formatNumber(selectedVehicle.latitude, 5)}</strong></div>
                    <div><span>Longitude</span><strong>{formatNumber(selectedVehicle.longitude, 5)}</strong></div>
                    <div><span>Temperature</span><strong>{formatNumber(selectedVehicle.temperature)}°</strong></div>
                    <div><span>Humidity</span><strong>{formatNumber(selectedVehicle.humidity)}%</strong></div>
                    <div><span>Dew point</span><strong>{formatNumber(selectedVehicle.dew_point)}°</strong></div>
                    <div><span>Elevation</span><strong>{formatNumber(selectedVehicle.elevation)} m</strong></div>
                  </div>
                  <div className="trip-actions">
                    <div><span className="trip-state-label">Trip state</span><strong>{selectedVehicle.activeTrip ? `Active · #${selectedVehicle.activeTrip.id}` : 'No active trip'}</strong></div>
                    {selectedVehicle.activeTrip && (
                      <div className="route-control">
                        <span className="trip-state-label">Planned route</span>
                        <strong className={routeStatus?.currently_deviated ? 'status-offline' : 'status-online'}>
                          {routeLoading ? 'Loading route...' : plannedRoute ? (routeStatus?.currently_deviated ? 'Deviation detected' : 'On route') : 'Not configured'}
                        </strong>
                        {routeStatus?.currently_deviated && routeStatus.last_distance_meters !== null && (
                          <small>{routeStatus.last_distance_meters.toFixed(1)}m from route / {routeStatus.threshold_meters.toFixed(0)}m threshold</small>
                        )}
                        <input type="file" accept=".kml" onChange={(event) => setRouteFile(event.target.files?.[0] ?? null)} />
                        <button className="button-secondary" type="button" onClick={() => void handleRouteUpload()} disabled={!routeFile || routeLoading}>
                          {routeLoading ? 'Uploading...' : 'Upload KML route'}
                        </button>
                      </div>
                    )}
                    <div className="trip-action-buttons">
                      <button className="button-secondary" type="button" onClick={() => setCenterRequest((value) => value + 1)} disabled={selectedVehicle.latitude === null || selectedVehicle.longitude === null}>Center on vehicle</button>
                      <button className="button-primary" type="button" onClick={() => void handleTripAction(selectedVehicle)} disabled={actionVehicleId !== null}>
                        {actionVehicleId === selectedVehicle.id ? 'Saving...' : selectedVehicle.activeTrip ? 'Stop trip' : 'Start trip'}
                      </button>
                    </div>
                  </div>
                  {actionError && <p className="form-error" role="alert">{actionError}</p>}
                  {routeError && <p className="form-error" role="alert">{routeError}</p>}
                </div>
              )}
            </section>
          </div>
        )}

        <section className="history-section panel-surface">
          <div className="history-heading">
            <div>
              <p className="card-label">Historical analysis</p>
              <h2>Historical Trip Analysis</h2>
              <p className="history-copy">Review stored telemetry from a completed trip without changing the live fleet view.</p>
            </div>
            <div className="history-selectors">
              <label>
                Vehicle
                <select
                  value={historyVehicleId ?? ''}
                  onChange={(event) => setHistoryVehicleId(event.target.value ? Number(event.target.value) : null)}
                >
                  <option value="">Select vehicle</option>
                  {vehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.name} · {vehicle.device_id}</option>)}
                </select>
              </label>
              <label>
                Trip
                <select
                  value={historyTripId ?? ''}
                  disabled={historyVehicleId === null || historicalTrips.length === 0}
                  onChange={(event) => setHistoryTripId(event.target.value ? Number(event.target.value) : null)}
                >
                  <option value="">Select trip</option>
                  {historicalTrips.map((trip) => <option key={trip.id} value={trip.id}>Trip #{trip.id} · {trip.status}</option>)}
                </select>
              </label>
              <button
                className="button-primary history-export-button"
                type="button"
                disabled={historyTripId === null || historyExporting}
                onClick={() => void handleHistoryExport()}
              >
                {historyExporting ? 'Exporting...' : 'Export CSV'}
              </button>
            </div>
          </div>

          {historyVehicleId === null && <p className="history-state">Select a vehicle to view historical trips.</p>}
          {historyVehicleId !== null && historicalTrips.length === 0 && <p className="history-state">No historical trips available.</p>}
          {historyVehicleId !== null && historicalTrips.length > 0 && historyTripId === null && <p className="history-state">Select a trip to view historical telemetry.</p>}
          {historyLoading && <p className="history-state">Loading trip telemetry...</p>}
          {historyError && <p className="form-error" role="alert">{historyError}</p>}
          {historyExportError && <p className="form-error" role="alert">{historyExportError}</p>}

          {historyTripId !== null && historicalTrip && !historyLoading && !historyError && (
            <div className="history-content">
              <div className="history-summary">
                <div><span>Vehicle</span><strong>{historicalVehicle?.name ?? `Vehicle ${historicalTrip.vehicle_id}`}</strong></div>
                <div><span>Trip</span><strong>#{historicalTrip.id}</strong></div>
                <div><span>Status</span><strong>{historicalTrip.status}</strong></div>
                <div><span>Started</span><strong>{formatTimestamp(historicalTrip.started_at)}</strong></div>
                <div><span>Ended</span><strong>{formatTimestamp(historicalTrip.ended_at)}</strong></div>
                <div><span>Telemetry points</span><strong>{historicalTelemetry.length}</strong></div>
              </div>
              {historicalTelemetry.length === 0 ? (
                <p className="history-state">No telemetry recorded for this trip.</p>
              ) : (
                <div className="history-visuals">
                  <section className="history-card">
                    <div className="history-card-heading"><p className="card-label">Sensor history</p><h3>Temperature vs time</h3></div>
                    <TemperatureChart telemetry={historicalTelemetry} />
                  </section>
                  <section className="history-card">
                    <div className="history-card-heading"><p className="card-label">GPS trail</p><h3>Recorded route</h3></div>
                    <HistoricalTripMap telemetry={historicalTelemetry} />
                  </section>
                </div>
              )}
            </div>
          )}
        </section>
      </section>
    </main>
  )
}
