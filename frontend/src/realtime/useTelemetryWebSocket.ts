import { useEffect, useRef, useState } from 'react'
import { API_BASE_URL } from '../api/client'
import type { TelemetryEvent } from '../types/telemetry'

export type WebSocketStatus = 'CONNECTING' | 'CONNECTED' | 'RECONNECTING' | 'DISCONNECTED'

const reconnectDelays = [1000, 2000, 4000, 8000]

function websocketUrl(token: string) {
  const baseUrl = API_BASE_URL.replace(/^http/, 'ws')
  return `${baseUrl}/ws/telemetry?token=${encodeURIComponent(token)}`
}

function isTelemetryEvent(value: unknown): value is TelemetryEvent {
  if (!value || typeof value !== 'object') return false
  const event = value as Partial<TelemetryEvent>
  return event.event === 'telemetry'
    && Number.isInteger(event.vehicle_id)
    && typeof event.device_id === 'string'
    && Number.isInteger(event.trip_id)
    && Number.isInteger(event.organization_id)
    && typeof event.recorded_at === 'string'
    && [event.temperature, event.humidity, event.dew_point, event.elevation, event.latitude, event.longitude]
      .every((number) => typeof number === 'number' && Number.isFinite(number))
}

async function parseTelemetryEvent(data: unknown): Promise<TelemetryEvent | null> {
  let parsed: unknown
  try {
    if (typeof data === 'string') {
      parsed = JSON.parse(data)
    } else if (data instanceof Blob) {
      parsed = JSON.parse(await data.text())
    } else if (typeof data === 'object' && data !== null) {
      parsed = data
    } else {
      return null
    }
  } catch {
    return null
  }

  return isTelemetryEvent(parsed) ? parsed : null
}

export function useTelemetryWebSocket(
  token: string | null,
  onTelemetry: (event: TelemetryEvent) => void,
  organizationId: number | null,
) {
  const [status, setStatus] = useState<WebSocketStatus>('DISCONNECTED')
  const socketRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const stoppedRef = useRef(false)
  const reconnectAttemptRef = useRef(0)
  const callbackRef = useRef(onTelemetry)
  callbackRef.current = onTelemetry

  useEffect(() => {
    if (!token) {
      setStatus('DISCONNECTED')
      return
    }

    stoppedRef.current = false
    reconnectAttemptRef.current = 0

    const clearReconnectTimer = () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }
    }

    const connect = () => {
      if (stoppedRef.current || socketRef.current) return
      setStatus(reconnectAttemptRef.current === 0 ? 'CONNECTING' : 'RECONNECTING')
      const socket = new WebSocket(websocketUrl(token))
      socketRef.current = socket

      socket.onopen = () => {
        reconnectAttemptRef.current = 0
        setStatus('CONNECTED')
      }

      socket.onmessage = async (message) => {
        if (import.meta.env.DEV) console.debug('[telemetry] WebSocket message received', message.data)
        const parsed = await parseTelemetryEvent(message.data)
        if (!parsed) {
          if (import.meta.env.DEV) console.debug('[telemetry] ignored malformed event')
          return
        }
        if (organizationId !== null && Number(parsed.organization_id) !== Number(organizationId)) {
          if (import.meta.env.DEV) console.debug('[telemetry] ignored organization mismatch', parsed.organization_id, organizationId)
          return
        }
        if (import.meta.env.DEV) console.debug('[telemetry] applying event', parsed.vehicle_id, parsed.device_id)
        callbackRef.current(parsed)
      }

      socket.onerror = () => {
        socket.close()
      }

      socket.onclose = () => {
        socketRef.current = null
        if (stoppedRef.current) return
        setStatus('RECONNECTING')
        const delay = reconnectDelays[Math.min(reconnectAttemptRef.current, reconnectDelays.length - 1)]
        reconnectAttemptRef.current += 1
        reconnectTimerRef.current = setTimeout(connect, delay)
      }
    }

    connect()

    return () => {
      stoppedRef.current = true
      clearReconnectTimer()
      reconnectAttemptRef.current = 0
      socketRef.current?.close()
      socketRef.current = null
      setStatus('DISCONNECTED')
    }
  }, [token, organizationId])

  return status
}

export { websocketUrl }