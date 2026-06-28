import { useEffect, useState } from 'react'

interface IncidentMapProps {
  incidents: any[]
  onSelect: (id: string) => void
}

export default function IncidentMap({ incidents, onSelect }: IncidentMapProps) {
  const [MapComponents, setMapComponents] = useState<any>(null)

  useEffect(() => {
    // Dynamic import to bypass SSR issues with Leaflet window globals
    Promise.all([
      import('react-leaflet'),
      import('leaflet'),
    ]).then(([ReactLeaflet, L]) => {
      // Fix default marker icon issue in Leaflet
      delete (L.Icon.Default.prototype as any)._getIconUrl
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
        iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
      })
      setMapComponents({ ...ReactLeaflet, L })
    })
  }, [])

  if (!MapComponents) {
    return (
      <div className="w-full h-[400px] flex items-center justify-center bg-slate-950/40 border border-glass-border rounded-xl">
        <span className="text-xs text-slate-500 font-mono animate-pulse">BOOTING TACTICAL SAT-MAP LAYER...</span>
      </div>
    )
  }

  const { MapContainer, TileLayer, Marker, Popup } = MapComponents

  // Center map on the first incident with coordinates, otherwise default
  const incidentWithCoords = incidents.find(i => i.latitude && i.longitude)
  const defaultCenter: [number, number] = incidentWithCoords 
    ? [incidentWithCoords.latitude, incidentWithCoords.longitude] 
    : [20, 0]

  return (
    <div className="w-full h-[400px] rounded-xl overflow-hidden border border-glass-border relative z-0">
      <MapContainer center={defaultCenter} zoom={3} style={{ height: '100%', width: '100%' }} scrollWheelZoom={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        {incidents.map((inc) => {
          if (!inc.latitude || !inc.longitude) return null
          return (
            <Marker key={inc.id} position={[inc.latitude, inc.longitude]}>
              <Popup>
                <div className="p-2 text-slate-900 font-sans">
                  <h3 className="font-bold text-sm leading-tight mb-1">{inc.title}</h3>
                  <div className="flex items-center gap-1.5 mt-1">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${
                      inc.risk_level === 'critical' ? 'bg-red-500 text-white' :
                      inc.risk_level === 'high' ? 'bg-orange-500 text-white' :
                      inc.risk_level === 'medium' ? 'bg-yellow-500 text-slate-900' :
                      inc.risk_level === 'low' ? 'bg-green-500 text-white' :
                      'bg-slate-400 text-white'
                    }`}>{inc.risk_level || 'Pending'}</span>
                    <span className="text-[10px] text-slate-500 font-mono">{inc.incident_type}</span>
                  </div>
                  <button
                    onClick={() => onSelect(inc.id)}
                    className="mt-2 text-xs font-semibold text-brand-blue hover:underline cursor-pointer block w-full text-left"
                  >
                    View Mission Details
                  </button>
                </div>
              </Popup>
            </Marker>
          )
        })}
      </MapContainer>
    </div>
  )
}
