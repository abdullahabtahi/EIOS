'use client';

import * as React from 'react';
import { useMap } from '@vis.gl/react-google-maps';
import { GoogleMapsOverlay } from '@deck.gl/google-maps';
import type { Layer } from '@deck.gl/core';

/**
 * Renders deck.gl layers over the Google map; draws no DOM. Interleaved on a vector map, overlaid on a raster one
 * (the overlay detects which). A fresh overlay per mount, finalized on cleanup, and attached one tick late: Google
 * attaches an overlay asynchronously, so React StrictMode's discarded first mount (mount, cleanup, mount) would
 * otherwise be finalized before its `onAdd` runs, and deck.gl then reads a null map or projection.
 */
export function GeoDeckOverlay({ layers }: { readonly layers: readonly Layer[] }) {
  const map = useMap();
  const overlayRef = React.useRef<GoogleMapsOverlay | null>(null);
  const latest = React.useRef<readonly Layer[]>(layers);
  latest.current = layers;

  React.useEffect(() => {
    if (!map) return;
    const overlay = new GoogleMapsOverlay({ interleaved: true });
    const attach = window.setTimeout(() => {
      overlay.setMap(map);
      overlay.setProps({ layers: [...latest.current] });
      overlayRef.current = overlay;
    }, 0);
    return () => {
      window.clearTimeout(attach);
      overlayRef.current = null;
      overlay.finalize();
    };
  }, [map]);

  React.useEffect(() => {
    overlayRef.current?.setProps({ layers: [...layers] });
  }, [map, layers]);

  return null;
}
