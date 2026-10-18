'use client';

import * as React from 'react';
import { APIProvider, Map, useMap } from '@vis.gl/react-google-maps';
import type { Layer } from '@deck.gl/core';
import { Icon } from '@/components/ui/icon';
import { GeoDeckOverlay } from './geo-deck-overlay';
import { readMapsConfig } from './geo-config';
import { MUTED_LIGHT_STYLE } from './geo-map-style';
import type { MapFocus } from './geo-focus';
import type { CameraTarget } from './geo-camera';

const WORLD_CENTER = { lat: 22, lng: 20 };
const WORLD_ZOOM = 2;

/** Moves the camera to the data once, when it first arrives; the analyst's own panning is never overridden afterwards. */
function InitialView({ focus }: { readonly focus: MapFocus | null }) {
  const map = useMap();
  const done = React.useRef(false);
  React.useEffect(() => {
    if (!map || !focus || done.current) return;
    done.current = true;
    map.moveCamera({ center: focus.center, zoom: focus.zoom });
  }, [map, focus]);
  return null;
}

const FIT_PADDING = { top: 96, right: 64, bottom: 96, left: 64 };

/** Moves the camera when the analyst picks a lead; a new target object (not a new value) is a new request. */
function CameraTo({ target }: { readonly target: CameraTarget | null }) {
  const map = useMap();
  React.useEffect(() => {
    if (!map || !target) return;
    if (target.kind === 'point') map.moveCamera({ center: target.center, zoom: target.zoom });
    else map.fitBounds({ north: target.north, south: target.south, east: target.east, west: target.west }, FIT_PADDING);
  }, [map, target]);
  return null;
}

export interface GeoMapProps {
  readonly layers: readonly Layer[];
  readonly focus?: MapFocus | null;
  readonly target?: CameraTarget | null;
}

function MapUnavailable({ title, detail, retry = false }: { readonly title: string; readonly detail: React.ReactNode; readonly retry?: boolean }) {
  return (
    <div role="status" className="flex h-full items-center justify-center bg-cx-sub text-cx-muted">
      <div className="max-w-xs space-y-1.5 px-4 text-center">
        <Icon icon="map" size="lg" className="text-cx-faint" />
        <p className="text-sm font-semibold text-cx-ink">{title}</p>
        <p className="text-xs">{detail}</p>
        {retry && (
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-1 cursor-pointer text-xs font-semibold text-cx-accent outline-none hover:text-cx-accent-strong focus-visible:ring-2 focus-visible:ring-cx-accent">
            Reload the page
          </button>
        )}
      </div>
    </div>
  );
}

/** Google basemap with the deck.gl evidence layers; labelled unavailable, never blank, when no key is configured. */
export function GeoMap({ layers, focus = null, target = null }: GeoMapProps) {
  const config = readMapsConfig();
  const [failed, setFailed] = React.useState(false);
  // Google reports a rejected key (referrer, billing, quota) through this global, and paints its own "Oops" over the map.
  React.useEffect(() => {
    const w = window as unknown as { gm_authFailure?: () => void };
    const previous = w.gm_authFailure;
    w.gm_authFailure = () => setFailed(true);
    return () => {
      w.gm_authFailure = previous;
    };
  }, []);
  if (!config) return <MapUnavailable title="Map unavailable" detail={<>No Google Maps key is configured (<span>NEXT_PUBLIC_GOOGLE_MAPS_API_KEY</span>).</>} />;
  if (failed) return <MapUnavailable title="The map could not load" detail="Google Maps refused or failed the request. The ranked list, figures and assistant still work." retry />;
  return (
    <APIProvider apiKey={config.apiKey} onError={() => setFailed(true)}>
      <Map
        {...(config.mapId ? { mapId: config.mapId } : { styles: MUTED_LIGHT_STYLE })}
        defaultCenter={WORLD_CENTER}
        defaultZoom={WORLD_ZOOM}
        minZoom={2}
        colorScheme="LIGHT"
        gestureHandling="greedy"
        disableDefaultUI
        zoomControl
        className="h-full w-full">
        <InitialView focus={focus} />
        <CameraTo target={target} />
        <GeoDeckOverlay layers={layers} />
      </Map>
    </APIProvider>
  );
}
