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

/** [ASSUMPTION] zoom is reported in half steps: labels are thinned by it, and a smooth pinch should not rebuild the layers every frame. */
const ZOOM_STEP = 0.5;

/** Tells the page the map's zoom, so the labels can be thinned to fit it. */
function ZoomWatcher({ onZoom }: { readonly onZoom: (zoom: number) => void }) {
  const map = useMap();
  React.useEffect(() => {
    if (!map) return;
    const report = () => {
      const zoom = map.getZoom();
      if (zoom !== undefined) onZoom(Math.round(zoom / ZOOM_STEP) * ZOOM_STEP);
    };
    report();
    const listener = map.addListener('zoom_changed', report);
    return () => listener.remove();
  }, [map, onZoom]);
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
  readonly onZoom?: (zoom: number) => void;
}

/** Google basemap with the deck.gl evidence layers; labelled unavailable, never blank, when no key is configured. */
export function GeoMap({ layers, focus = null, target = null, onZoom }: GeoMapProps) {
  const config = readMapsConfig();
  if (!config) {
    return (
      <div role="status" className="flex h-full items-center justify-center bg-cx-sub text-cx-muted">
        <div className="max-w-xs text-center space-y-1">
          <Icon icon="map" size="lg" className="text-cx-faint" />
          <p className="text-sm font-semibold text-cx-ink">Map unavailable</p>
          <p className="text-xs">
            No Google Maps key is configured (<span>NEXT_PUBLIC_GOOGLE_MAPS_API_KEY</span>).
          </p>
        </div>
      </div>
    );
  }
  return (
    <APIProvider apiKey={config.apiKey}>
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
        {onZoom && <ZoomWatcher onZoom={onZoom} />}
        <GeoDeckOverlay layers={layers} />
      </Map>
    </APIProvider>
  );
}
