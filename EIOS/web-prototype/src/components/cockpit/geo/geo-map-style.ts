import type { MapProps } from '@vis.gl/react-google-maps';

/**
 * A muted light basemap (the cockpit's `cx-*` greys) so the evidence layers carry the colour: no roads, places,
 * transit, cities or ocean names; country borders and country names only. Applied as client-side styles to a raster
 * map. Google ignores client styles on a map that has a Map ID, which then brings its own cloud style instead.
 */
export const MUTED_LIGHT_STYLE: NonNullable<MapProps['styles']> = [
  { elementType: 'geometry', stylers: [{ color: '#f5f8fa' }] },
  { elementType: 'labels.icon', stylers: [{ visibility: 'off' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#9aabb7' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#f5f8fa' }] },
  { featureType: 'administrative.country', elementType: 'geometry.stroke', stylers: [{ color: '#ced9e0' }, { weight: 0.8 }] },
  { featureType: 'administrative.country', elementType: 'labels.text.fill', stylers: [{ color: '#7d909f' }] },
  { featureType: 'administrative.province', stylers: [{ visibility: 'off' }] },
  { featureType: 'administrative.locality', stylers: [{ visibility: 'off' }] },
  { featureType: 'administrative.neighborhood', stylers: [{ visibility: 'off' }] },
  { featureType: 'administrative.land_parcel', stylers: [{ visibility: 'off' }] },
  { featureType: 'poi', stylers: [{ visibility: 'off' }] },
  { featureType: 'road', stylers: [{ visibility: 'off' }] },
  { featureType: 'transit', stylers: [{ visibility: 'off' }] },
  { featureType: 'landscape', elementType: 'labels', stylers: [{ visibility: 'off' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#e1e8ed' }] },
  { featureType: 'water', elementType: 'labels', stylers: [{ visibility: 'off' }] },
];
