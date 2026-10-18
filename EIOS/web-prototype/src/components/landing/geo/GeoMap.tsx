"use client";

import React, { useEffect, useRef, useState } from "react";
import type { Deck, MapView, TransitionInterpolator } from "@deck.gl/core";
import type * as DeckLayers from "@deck.gl/layers";
import { COUNTRY_NAMES, type Corridor, type Gateway } from "../data/geo";
import type { RecordedTurn } from "../data/turns";
import { useReducedMotion } from "../hooks";
import { buildLayers, viewFor, type Basis, type CountryFeature, type Lens } from "./geoLayers";

interface GeoMapProps {
  readonly lens: Lens;
  readonly basis: Basis;
  readonly focus: RecordedTurn["focus"] | null;
}

type Status = "idle" | "loading" | "ready" | "failed";

interface Runtime {
  readonly deck: Deck<MapView>;
  readonly L: typeof DeckLayers;
  readonly FlyTo: new (opts?: { speed?: number }) => TransitionInterpolator;
  readonly countries: readonly CountryFeature[];
}

const usd = (n: number): string => `$${n.toLocaleString("en-US")}`;
const name = (iso: string): string => COUNTRY_NAMES[iso] ?? iso;

function tooltip(info: { object?: unknown; layer?: { id: string } | null }): { html: string; className: string } | null {
  const o = info.object;
  if (!o || !info.layer) return null;
  if (info.layer.id === "corridors") {
    const c = o as Corridor;
    return { className: "fde-map-tip", html: `<b>${name(c[0])} → ${name(c[1])}</b><br/>${usd(c[2])} · ${c[3]} accounts · ${c[4]} tier` };
  }
  if (info.layer.id === "exits") {
    const g = o as Gateway;
    return { className: "fde-map-tip", html: `<b>${g.id}</b> · ${name(g.iso2)}<br/>${g.accounts} accounts · ${g.jumps} impossible jumps` };
  }
  if (info.layer.id === "countries") {
    const p = (o as CountryFeature).properties;
    const lists = [
      p.fatf ? `FATF ${p.fatf.replace(/_/g, " ")}` : null,
      p.eu ? "EU high-risk list" : null,
      p.baselScore != null ? `Basel AML ${p.baselScore.toFixed(2)} (${p.basel})` : null,
    ].filter(Boolean);
    return { className: "fde-map-tip", html: `<b>${p.name}</b><br/>${lists.length ? lists.join(" · ") : "No listing or score held"}` };
  }
  return null;
}

export function GeoMap({ lens, basis, focus }: GeoMapProps) {
  const host = useRef<HTMLDivElement>(null);
  const rt = useRef<Runtime | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const reduced = useReducedMotion();

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    let cancelled = false;
    const start = async () => {
      setStatus("loading");
      try {
        const [core, L, res] = await Promise.all([
          import("@deck.gl/core"),
          import("@deck.gl/layers"),
          fetch("/landing/geo/countries.json"),
        ]);
        if (!res.ok) throw new Error(`countries.json ${res.status}`);
        const geo = (await res.json()) as { features: CountryFeature[] };
        if (cancelled) return;
        const deck = new core.Deck({
          parent: el,
          views: new core.MapView({ repeat: false }),
          initialViewState: viewFor(null),
          controller: { scrollZoom: false, dragRotate: false, touchRotate: false, doubleClickZoom: true, dragPan: true },
          getTooltip: tooltip as never,
          style: { position: "absolute", inset: "0" },
        });
        rt.current = { deck, L, FlyTo: core.FlyToInterpolator, countries: geo.features };
        setStatus("ready");
      } catch (err) {
        console.error("landing map failed to start", err);
        if (!cancelled) setStatus("failed");
      }
    };
    if (typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          io.disconnect();
          void start();
        }
      },
      { rootMargin: "60% 0px" },
    );
    io.observe(el);
    return () => {
      cancelled = true;
      io.disconnect();
      rt.current?.deck.finalize();
      rt.current = null;
    };
  }, []);

  useEffect(() => {
    const r = rt.current;
    if (status !== "ready" || !r) return;
    r.deck.setProps({ layers: buildLayers({ L: r.L, countries: r.countries, lens, basis, focus }) });
  }, [status, lens, basis, focus]);

  useEffect(() => {
    const r = rt.current;
    if (status !== "ready" || !r) return;
    r.deck.setProps({
      initialViewState: {
        ...viewFor(focus),
        transitionDuration: reduced ? 0 : 1400,
        transitionInterpolator: reduced ? undefined : new r.FlyTo({ speed: 1.4 }),
      },
    });
  }, [status, focus, reduced]);

  return (
    <div className="fde-map" ref={host} aria-label="World map of the book's corridors, shared exits and jurisdiction lists" role="img">
      {status !== "ready" && (
        <p className="fde-map-status">{status === "failed" ? "The map needs WebGL, which this browser did not provide." : "Loading the map…"}</p>
      )}
    </div>
  );
}
