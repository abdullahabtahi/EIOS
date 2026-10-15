'use client';

import * as React from 'react';
import { APIProvider, Map } from '@vis.gl/react-google-maps';
import type { Layer } from '@deck.gl/core';
import { Icon } from '@/components/ui/icon';
import { GeoDeckOverlay } from './geo-deck-overlay';
import { readMapsConfig } from './geo-config';
import { MUTED_LIGHT_STYLE } from './geo-map-style';

const WORLD_CENTER = { lat: 22, lng: 20 };
const WORLD_ZOOM = 2;

/** Google basemap with the deck.gl evidence layers; labelled unavailable, never blank, when no key is configured. */
export function GeoMap({ layers }: { readonly layers: readonly Layer[] }) {
  const config = readMapsConfig();
  if (!config) {
    return (
      <div role="status" className="flex h-full items-center justify-center bg-cx-sub text-cx-muted">
        <div className="max-w-xs text-center space-y-1">
          <Icon icon="map" size="lg" className="text-cx-faint" />
          <p className="text-sm font-semibold text-cx-ink">Map unavailable</p>
          <p className="text-xs">
            No Google Maps key is configured (<span className="font-mono">NEXT_PUBLIC_GOOGLE_MAPS_API_KEY</span>).
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
        <GeoDeckOverlay layers={layers} />
      </Map>
    </APIProvider>
  );
}
