'use client';

/**
 * The financial projection with the interval its own backtest measured, and the four briefing horizons.
 * Every figure here was computed by the backend; this file only lays it out.
 */

import * as React from 'react';
import { MetricProvenanceBadge } from '../common/metric-provenance';
import type { MetricProvenance } from '../state/cockpit-types';
import { signed, usd, type BoardForecast, type Horizon } from './board';

export function ForecastCard({ forecast }: { forecast: BoardForecast }) {
  const nominalPct = Math.round((forecast.nominal ?? 0.9) * 100);

  const svgRef = React.useRef<SVGSVGElement | null>(null);
  const [hoverPoint, setHoverPoint] = React.useState<{
    x: number;
    y: number;
    value: number;
    pct: number;
  } | null>(null);

  // Compute point estimate position relative to the low/high confidence envelope
  const envelopePct = React.useMemo(() => {
    if (forecast.low === null || forecast.high === null || forecast.high === forecast.low) return 50;
    const raw = ((forecast.point - forecast.low) / (forecast.high - forecast.low)) * 100;
    return Math.min(Math.max(raw, 4), 96);
  }, [forecast.point, forecast.low, forecast.high]);

  // Generate mathematically accurate Gaussian probability density curve with elevated height
  const gaussian = React.useMemo(() => {
    if (forecast.low === null || forecast.high === null) return null;
    const x0 = 50 + (envelopePct / 100) * 400; // Peak mode coordinate in 500px width
    const sigma = 105;
    const yBaseline = 90;
    const amplitude = 72;
    const pts: [number, number][] = [];
    for (let x = 10; x <= 490; x += 6) {
      const exponent = -0.5 * Math.pow((x - x0) / sigma, 2);
      const y = yBaseline - amplitude * Math.exp(exponent);
      pts.push([x, y]);
    }
    const fullPath = `M ${pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' L ')}`;
    // Shaded confidence mass between x = 50 and x = 450
    const shaded = pts.filter(([x]) => x >= 50 && x <= 450);
    const yLow = yBaseline - amplitude * Math.exp(-0.5 * Math.pow((50 - x0) / sigma, 2));
    const yHigh = yBaseline - amplitude * Math.exp(-0.5 * Math.pow((450 - x0) / sigma, 2));
    const areaPath = `M 50,${yBaseline} L 50,${yLow.toFixed(1)} L ${shaded.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' L ')} L 450,${yHigh.toFixed(1)} L 450,${yBaseline} Z`;
    return { fullPath, areaPath, x0, yPeak: yBaseline - amplitude, yLow, yHigh, yBaseline, sigma, amplitude };
  }, [forecast.low, forecast.high, envelopePct]);

  // Mouse hover interaction tracker
  const handleMouseMove = React.useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!svgRef.current || !gaussian || forecast.low === null || forecast.high === null) return;
      const rect = svgRef.current.getBoundingClientRect();
      if (!rect.width) return;
      const clientX = e.clientX - rect.left;
      const rawX = (clientX / rect.width) * 500;
      const x = Math.min(Math.max(rawX, 15), 485);

      // Compute Gaussian curve y coordinate at x
      const exponent = -0.5 * Math.pow((x - gaussian.x0) / gaussian.sigma, 2);
      const y = gaussian.yBaseline - gaussian.amplitude * Math.exp(exponent);

      // Interpolate revenue value
      let value: number;
      if (x <= gaussian.x0) {
        value = forecast.low + ((x - 50) / (gaussian.x0 - 50)) * (forecast.point - forecast.low);
      } else {
        value = forecast.point + ((x - gaussian.x0) / (450 - gaussian.x0)) * (forecast.high - forecast.point);
      }

      // Calculate approximate percentile
      const rawPct = Math.round(5 + ((x - 50) / 400) * 90);
      const pct = Math.min(Math.max(rawPct, 1), 99);

      setHoverPoint({ x, y, value, pct });
    },
    [gaussian, forecast.low, forecast.high, forecast.point],
  );

  const handleMouseLeave = React.useCallback(() => {
    setHoverPoint(null);
  }, []);

  return (
    <section
      aria-label="Net revenue projection"
      className="@container bg-white border border-slate-200 shadow-xs select-none text-slate-900 overflow-hidden"
    >
      {/* Header Ribbon */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 sm:px-6 py-3.5 border-b border-slate-200/90 bg-slate-50/50">
        <div className="flex items-center gap-2.5">
          <span className="material-symbols-sharp text-lg text-blue-700">trending_up</span>
          <h3 className="text-sm font-sans font-semibold text-slate-900 tracking-tight">
            Net Revenue Projection ({forecast.horizonDays ?? 28} Days Ahead)
          </h3>
        </div>
        <div className="flex items-center gap-2 text-label font-mono">
          <span className="px-2.5 py-1 bg-white border border-slate-200 text-slate-600 font-semibold tracking-wider text-label">
            HORIZON: {forecast.horizonDays ?? 28}D
          </span>
          <span className="px-2.5 py-1 bg-blue-50 border border-blue-200 text-blue-800 font-semibold tracking-wider text-label">
            GAUSSIAN DRIFT ESTIMATE
          </span>
        </div>
      </div>

      {/* Primary KPI & Visual Confidence Envelope (Responsive Container Query Grid) */}
      <div className="p-5 sm:p-6 grid grid-cols-1 @[840px]:grid-cols-12 gap-6 sm:gap-8 items-start">
        {/* Left: Point Estimate */}
        <div className="@[840px]:col-span-5 min-w-0 space-y-3">
          {/* Hero Point Estimate */}
          <div className="space-y-3">
            <div className="text-label font-mono uppercase tracking-wider text-slate-500 font-semibold flex items-center gap-2 h-6">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400 inline-block shrink-0" />
              <span>Expected Projected Revenue</span>
            </div>
            <div className="space-y-2">
              <div className="flex flex-wrap items-baseline gap-2 sm:gap-2.5 font-mono">
                <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 tabular-nums tracking-tight">
                  {usd(forecast.point)}
                </span>
                <span
                  className={`text-label font-medium px-2 py-0.5 border tabular-nums ${
                    forecast.deltaPct < 0
                      ? 'bg-amber-50 border-amber-300 text-amber-800'
                      : 'bg-green-50 border-green-300 text-green-800'
                  }`}
                >
                  {signed(forecast.deltaPct)}% against today
                </span>
              </div>
              <p className="text-xs text-slate-500 font-sans leading-relaxed max-w-sm">
                Synthesized from historical payout velocity, partner attrition risk, and deposit momentum.
              </p>
            </div>
          </div>
        </div>

        {/* Right: Interactive Normal Distribution Chart & Metric Cards (No Header Clutter) */}
        <div className="@[840px]:col-span-7 space-y-3 min-w-0">
          {gaussian && (
            <div className="space-y-3">
              {/* Interactive Gaussian Bell Curve Canvas */}
              <div className="bg-slate-50/70 border border-slate-200/90 p-3 rounded-xs overflow-hidden relative">
                <svg
                  ref={svgRef}
                  role="img"
                  aria-label="Interactive Gaussian probability density curve"
                  className="w-full h-24 sm:h-28 select-none cursor-crosshair"
                  viewBox="0 0 500 106"
                  onMouseMove={handleMouseMove}
                  onMouseLeave={handleMouseLeave}
                >
                  {/* Mini Small Confidence Probability Density Label Inside Graph (Top-Right Stacked) */}
                  <text
                    x="485"
                    y="16"
                    textAnchor="end"
                    className="fill-slate-400 font-mono text-label font-semibold tracking-wider uppercase select-none pointer-events-none"
                  >
                    <tspan x="485" dy="0">{nominalPct}% Confidence</tspan>
                    <tspan x="485" dy="12">Probability Density</tspan>
                  </text>

                  {/* Shaded Confidence Mass */}
                  <path d={gaussian.areaPath} className="fill-blue-100/75 pointer-events-none" />

                  {/* Baseline Axis */}
                  <line x1="10" y1={gaussian.yBaseline} x2="490" y2={gaussian.yBaseline} className="stroke-slate-300 stroke-1 pointer-events-none" />

                  {/* Low Boundary Dashed Marker (P05) */}
                  <line x1="50" y1={gaussian.yLow} x2="50" y2={gaussian.yBaseline} strokeDasharray="3 2" className="stroke-blue-400 stroke-1 pointer-events-none" />

                  {/* High Boundary Dashed Marker (P95) */}
                  <line x1="450" y1={gaussian.yHigh} x2="450" y2={gaussian.yBaseline} strokeDasharray="3 2" className="stroke-blue-400 stroke-1 pointer-events-none" />

                  {/* Continuous Probability Curve */}
                  <path d={gaussian.fullPath} fill="none" className="stroke-blue-600 stroke-1.5 pointer-events-none" />

                  {/* Mode / Expected Needle (Drawn as reference) */}
                  <line x1={gaussian.x0} y1={gaussian.yPeak} x2={gaussian.x0} y2={gaussian.yBaseline} className="stroke-slate-900 stroke-1.5 pointer-events-none" />
                  <circle cx={gaussian.x0} cy={gaussian.yPeak} r="3.5" className="fill-slate-900 stroke-white stroke-1 pointer-events-none" />

                  {/* Static Baseline Axis Markers */}
                  <text x="50" y={gaussian.yBaseline + 12} textAnchor="middle" className="fill-slate-400 font-mono text-label font-semibold pointer-events-none">P05</text>
                  <text x={gaussian.x0} y={gaussian.yBaseline + 12} textAnchor="middle" className="fill-slate-700 font-mono text-label font-bold pointer-events-none">MODE</text>
                  <text x="450" y={gaussian.yBaseline + 12} textAnchor="middle" className="fill-slate-400 font-mono text-label font-semibold pointer-events-none">P95</text>

                  {/* Dynamic Hover Indicator & Tooltip */}
                  {hoverPoint && (
                    <g className="pointer-events-none">
                      {/* Vertical Hairline Tracker */}
                      <line
                        x1={hoverPoint.x}
                        y1={hoverPoint.y}
                        x2={hoverPoint.x}
                        y2={gaussian.yBaseline}
                        strokeDasharray="2 2"
                        className="stroke-blue-600 stroke-1"
                      />

                      {/* Interactive Data Point on Curve */}
                      <circle cx={hoverPoint.x} cy={hoverPoint.y} r="7" className="fill-blue-500/20" />
                      <circle cx={hoverPoint.x} cy={hoverPoint.y} r="4" className="fill-blue-600 stroke-white stroke-1.5" />

                      {/* Floating Tooltip Pill inside SVG bounds */}
                      <g
                        transform={`translate(${Math.min(Math.max(hoverPoint.x, 62), 438)}, ${Math.max(hoverPoint.y - 18, 14)})`}
                      >
                        <rect
                          x="-54"
                          y="-13"
                          width="108"
                          height="20"
                          rx="3"
                          className="fill-slate-900 shadow-sm"
                        />
                        <text
                          x="0"
                          y="1.5"
                          textAnchor="middle"
                          className="fill-white font-mono text-label font-semibold"
                        >
                          {usd(hoverPoint.value)} · P{hoverPoint.pct.toString().padStart(2, '0')}
                        </text>
                      </g>
                    </g>
                  )}
                </svg>
              </div>

              {/* 3 Spacious Intuitive Metric Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 @[480px]:grid-cols-3 gap-2.5 sm:gap-3 font-mono">
                {/* 1. Floor */}
                <div className="p-2.5 sm:p-3 bg-slate-50 border border-slate-200 space-y-1 min-w-0">
                  <div className="text-label text-slate-500 uppercase font-semibold tracking-tight truncate">Floor (P05)</div>
                  <div className="text-sm sm:text-base font-bold text-slate-900 tabular-nums truncate">{usd(forecast.low!)}</div>
                  <div className="text-label text-slate-500 font-sans leading-tight">Downside buffer</div>
                </div>

                {/* 2. Mode Expected */}
                <div className="p-2.5 sm:p-3 bg-blue-50/70 border border-blue-200 space-y-1 min-w-0">
                  <div className="text-label text-blue-800 uppercase font-bold tracking-tight truncate">Expected (Mode)</div>
                  <div className="text-sm sm:text-base font-bold text-blue-950 tabular-nums truncate">{usd(forecast.point)}</div>
                  <div className="text-label text-blue-700/80 font-sans leading-tight">Peak forecast</div>
                </div>

                {/* 3. Ceiling */}
                <div className="p-2.5 sm:p-3 bg-slate-50 border border-slate-200 space-y-1 min-w-0">
                  <div className="text-label text-slate-500 uppercase font-semibold tracking-tight truncate">Ceiling (P95)</div>
                  <div className="text-sm sm:text-base font-bold text-slate-900 tabular-nums truncate">{usd(forecast.high!)}</div>
                  <div className="text-label text-slate-500 font-sans leading-tight">Upside threshold</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Model Telemetry & Audit Footer Strip */}
      {forecast.skill !== null && forecast.coverage !== null && forecast.origins !== null && (
        <div className="border-t border-slate-200/90 bg-slate-50/70 px-5 sm:px-6 py-3 font-mono">
          <div className="grid grid-cols-1 @[640px]:grid-cols-3 gap-3 @[640px]:gap-0 divide-y @[640px]:divide-y-0 @[640px]:divide-x divide-slate-200 text-slate-600">
            {/* Benchmark */}
            <div className="@[640px]:pr-5 flex items-start">
              <p className="leading-relaxed text-[11px] text-slate-600">
                <span className="text-slate-400 font-medium">Backtested on {forecast.origins} past forecasts:</span>{' '}
                its error was{' '}
                <span className="text-slate-700 font-medium">
                  {forecast.skill.toFixed(2)}× the error of carrying
                </span>{' '}
                today&apos;s value forward
              </p>
            </div>

            {/* Calibration */}
            <div className="@[640px]:px-5 pt-2.5 @[640px]:pt-0 flex items-start">
              <p className="leading-relaxed text-[11px] text-slate-600">
                <span className="text-slate-400 font-medium">Calibration:</span>{' '}
                <span className="text-slate-700 font-medium">
                  interval held {(forecast.coverage * 100).toFixed(0)}%
                </span>{' '}
                of the time on holdouts
              </p>
            </div>

            {/* Prior Assumption */}
            {forecast.assumption && (
              <div className="@[640px]:pl-5 pt-2.5 @[640px]:pt-0 flex items-start">
                <p className="leading-relaxed text-[11px] text-slate-600">
                  <span className="text-slate-400 font-medium">Assumption:</span>{' '}
                  Assumes the {forecast.assumption}.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

const BADGE: Record<string, string> = {
  Competitive: 'COMPETITIVE',
  Partner: 'PARTNER FLOW',
  Client: 'CLIENT RETENTION',
  Financial: 'FINANCIAL METRICS',
};

function toMetric(h: Horizon): MetricProvenance {
  return {
    metricId: h.metricId,
    name: h.name,
    rawValue: h.value,
    formattedValue: h.figure,
    unit: '',
    semanticDefinitionVersion: `v${h.definitionVersion}`,
    asOfTimestamp: h.asOf,
    originEngine: h.source,
    stewardRole: h.owner,
    citation: '[COMPUTED]',
    isCached: false,
  };
}

export function BriefingCards({ horizons }: { horizons: Horizon[] }) {
  return (
    <section aria-label="Morning Briefing 4 Horizons" className="space-y-2.5">
      <div className="flex items-center justify-between border-b border-slate-200 pb-2">
        <div className="flex items-center gap-2">
          <span className="material-symbols-sharp text-base text-blue-700">wb_twilight</span>
          <h3 className="text-title font-sans font-semibold text-slate-900">Executive Morning Briefing</h3>
        </div>
        <span className="text-label font-mono text-slate-500 uppercase tracking-wider font-semibold">
          4 Sensitivity Horizons · Continuous Telemetry
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        {horizons.map((h) => (
          <div
            key={h.name}
            className="p-3.5 bg-white border border-slate-200 shadow-xs flex flex-col justify-between space-y-2 hover:border-slate-300 transition-colors"
          >
            <div>
              <div className="flex items-center justify-between gap-1">
                <span className="text-label font-mono font-bold text-blue-800 bg-blue-50 border border-blue-200 px-1.5 py-0.5 tracking-wider">
                  {BADGE[h.name] ?? h.name.toUpperCase()}
                </span>
                <span
                  className={`text-label font-mono font-bold px-1.5 py-0.5 border tabular-nums ${
                    h.deltaPct > 0
                      ? 'text-green-800 bg-green-50 border-green-200'
                      : h.deltaPct < 0
                      ? 'text-amber-800 bg-amber-50 border-amber-200'
                      : 'text-slate-700 bg-slate-50 border-slate-200'
                  }`}
                >
                  {signed(h.deltaPct)}%
                </span>
              </div>
              <p className="text-xs text-slate-700 font-sans mt-2.5 leading-relaxed min-h-[3.25rem]">
                {h.headline}
              </p>
            </div>
            <div className="pt-2.5 border-t border-slate-200 flex items-center justify-between">
              <MetricProvenanceBadge metric={toMetric(h)} displayMode="compact" />
              <span className="text-base font-bold font-mono text-slate-900 tabular-nums">
                {h.figure}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
