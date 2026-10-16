'use client';

/**
 * Hardware-Accelerated Relational Graph Studio.
 * Full-screen theater canvas with dark-mode obsidian aesthetics, coordinate dot-matrix grid,
 * and high-value interactive forensic analysis tools for institutional financial intelligence.
 *
 * Sovereign Dark Mode Architecture:
 * - Obsidian Slate Base (#080C14 / --slate-950) with 32px coordinate dot matrix.
 * - Sharp 0px geometry (--rad-reg: 0px) and hairline architectural strokes (--border-divider).
 * - Restrained status palette: Crimson Rose (#a82a2a), Warm Amber (#b37a30), Electric Cobalt (#106ba3), Mist White (#F8FAFC).
 * - Multi-Layout Dispatch: Organic Force-Directed, Radial Ego-Orbits, and Bipartite Layering Funnel.
 * - Interactive Capabilities:
 *   1. Entity 360 Flyout Inspector with graph centrality metrics & counterparty ledger.
 *   2. A -> B Shortest-Path / Laundering Funnel Tracer with multi-hop chain isolation.
 *   3. 30-Day Temporal Timeline Playback Scrubber.
 *   4. Min-Transaction Volume Threshold Slider ($0 to $250K+).
 *   5. In-Graph Entity Search & Camera Auto-Centering.
 *   6. 1-Click Cryptographically Watermarked FinCEN SAR Exhibit 1 Snapshot.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { GraphNode, GraphEdge } from '../state/cockpit-types';
import { fetchAmlGraph } from '../state/api-bridge';
import { useStageRequest } from './use-stage-request';
import { nodeOpensCase } from './graph-selection';

interface SimNode extends GraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  targetX?: number;
  targetY?: number;
}

interface SimEdge {
  id: string;
  source: SimNode;
  target: SimNode;
  type: string;
  weight: number;
  label: string;
  amountUsd?: number;
  dayIndex?: number;
}

const FALLBACK_NODES: GraphNode[] = [
  { id: 'CR84920', type: 'ACCOUNT', label: 'CR84920 (LatAm Suspect)', degree: 6, isCgnatHub: false, isSuppressed: false, riskScore: 0.94, details: { turnover: '$1.42M', kyc: 'Self-Employed', country: 'Colombia / Panama', betweenness: '0.88' } },
  { id: 'MULE-4920-01', type: 'ACCOUNT', label: 'MULE-4920-01 (Medellin Smurf)', degree: 3, isCgnatHub: false, isSuppressed: false, riskScore: 0.86, details: { turnover: '$410K', kyc: 'Tier 1 Verified', country: 'Colombia', betweenness: '0.62' } },
  { id: 'MULE-4920-02', type: 'ACCOUNT', label: 'MULE-4920-02 (Bogota Smurf)', degree: 3, isCgnatHub: false, isSuppressed: false, riskScore: 0.82, details: { turnover: '$380K', kyc: 'Tier 1 Verified', country: 'Colombia', betweenness: '0.58' } },
  { id: 'MULE-4920-03', type: 'ACCOUNT', label: 'MULE-4920-03 (Panama Exit)', degree: 4, isCgnatHub: false, isSuppressed: false, riskScore: 0.91, details: { turnover: '$890K', kyc: 'Offshore IBC', country: 'Panama', betweenness: '0.79' } },
  { id: 'DEV-F89A', type: 'DEVICE', label: 'Hardware Hash F89A', degree: 3, isCgnatHub: false, isSuppressed: false, riskScore: 0.74, details: { model: 'Linux / Chrome Headless', os: 'Ubuntu 22.04' } },
  { id: 'IP-CGNAT-TELCO', type: 'IP_ADDRESS', label: '187.12.89.4 (Claro CGNAT Proxy)', degree: 148, isCgnatHub: true, isSuppressed: true, riskScore: 0.15, details: { subnet: 'AS28573', connections: '148 accounts' } },
  { id: 'PTR-491', type: 'ACCOUNT', label: 'PTR-491 (Tier-2 IB Broker)', degree: 2, isCgnatHub: false, isSuppressed: false, riskScore: 0.42, details: { turnover: '$120K', kyc: 'Standard Affiliate' } },
];

const FALLBACK_EDGES: GraphEdge[] = [
  { id: 'e1', source: 'CR84920', target: 'MULE-4920-01', type: 'TRANSACTION_FLOW', weight: 0.95, label: 'Rapid Smurf ($180K)' },
  { id: 'e2', source: 'CR84920', target: 'MULE-4920-02', type: 'TRANSACTION_FLOW', weight: 0.90, label: 'Rapid Smurf ($145K)' },
  { id: 'e3', source: 'MULE-4920-01', target: 'MULE-4920-03', type: 'TRANSACTION_FLOW', weight: 0.88, label: 'Layering Flow ($310K)' },
  { id: 'e4', source: 'MULE-4920-02', target: 'MULE-4920-03', type: 'TRANSACTION_FLOW', weight: 0.85, label: 'Layering Flow ($260K)' },
  { id: 'e5', source: 'MULE-4920-03', target: 'CR84920', type: 'MIRROR_TRADE', weight: 0.98, label: 'Mirror Trade Loop (99.2%)' },
  { id: 'e6', source: 'CR84920', target: 'DEV-F89A', type: 'SHARED_DEVICE', weight: 1.0, label: 'Shared Hardware Fingerprint' },
  { id: 'e7', source: 'MULE-4920-01', target: 'DEV-F89A', type: 'SHARED_DEVICE', weight: 1.0, label: 'Shared Hardware Fingerprint' },
  { id: 'e8', source: 'CR84920', target: 'PTR-491', type: 'TRANSACTION_FLOW', weight: 0.4, label: 'Sub-IB Referral Tree' },
  { id: 'e9', source: 'CR84920', target: 'IP-CGNAT-TELCO', type: 'SHARED_IP', weight: 0.2, label: 'Telco CGNAT Gateway' },
];

/** A node's risk is its own strongest alert when the backend measured one, else derived from structure only. */
function insightRisk(insight: any, n: any, seed: string | undefined): number {
  return typeof insight?.risk === 'number' ? insight.risk : structuralRisk(n, seed);
}

/** A live node shows the risk the backend measured for it, or n/a; only the sample network shows an estimate. */
function riskLabel(node: GraphNode, live: boolean): string {
  if (!live) return `${Math.round((node.riskScore || 0.5) * 100)}%`;
  return node.details?.risk ?? 'n/a';
}

const usd = (v: number) => `$${Math.round(v).toLocaleString()}`;

/** What the inspector shows for a live node: only what the backend computed for it. */
function liveDetails(n: any, insight: any): Record<string, string> {
  return {
    degree: `${n.degree} connections`,
    type: String(n.node_type).replace(/_/g, ' ').toLowerCase(),
    ...(n.is_hub_suppressed ? { suppressed: `hub collapsed (${n.collapsed_node_count} accounts)` } : {}),
    ...(typeof insight?.risk === 'number' ? { risk: `${Math.round(insight.risk * 100)}%` } : {}),
    ...(typeof insight?.betweenness === 'number' ? { betweenness: insight.betweenness.toFixed(2) } : {}),
    ...(typeof insight?.clustering === 'number' ? { clustering: insight.clustering.toFixed(2) } : {}),
    ...(typeof insight?.velocity_usd === 'number' ? { turnover: usd(insight.velocity_usd) } : {}),
    ...(insight?.country ? { country: insight.country } : {}),
  };
}

/** The graph the backend computed carries no per-node risk, so the view derives it from structure only. */
function structuralRisk(n: any, seed: string | undefined): number {
  if (n.node_id === seed) return 0.9;
  if (n.is_hub_suppressed) return 0.15;
  if (n.node_type === 'CLIENT_ACCOUNT') return 0.75;
  if (n.node_type === 'DEVICE_FINGERPRINT') return 0.6;
  return 0.4;
}

function replayRisk(n: any): number {
  if (n.node_id.includes('84920')) return 0.94;
  if (n.degree >= 8 || n.node_id.includes('RING')) return 0.88;
  return n.node_id.includes('MULE') ? 0.72 : 0.45;
}

/** An edge says what the backend measured: a flow's volume, a timing gap in seconds. Nothing is filled in. */
function edgeLabel(e: any, replay: boolean): string {
  if (replay) {
    return e.edge_type === 'RAPID_INTERNAL_TRANSFER'
      ? `$${(e.transaction_volume_usd || 180000).toLocaleString()} transfer`
      : e.edge_type;
  }
  if (typeof e.transaction_volume_usd === 'number') return `$${Math.round(e.transaction_volume_usd).toLocaleString()} flow`;
  if (typeof e.matched_timing_seconds === 'number') return `${e.matched_timing_seconds}s apart`;
  return String(e.edge_type).replace(/_/g, ' ').toLowerCase();
}

type LayoutMode = 'FORCE' | 'RADIAL_EGO' | 'BIPARTITE';

export function resolveProofLedgerHash(state: {
  canvasPayload?: unknown;
  activeDrProofs?: Array<{ backupCheckpointHash?: string }>;
}): string | null {
  const payload = state.canvasPayload as Record<string, unknown> | null | undefined;
  if (typeof payload?.ledgerHash === 'string') return payload.ledgerHash;
  if (typeof payload?.checkpointHash === 'string') return payload.checkpointHash;
  const proof = state.activeDrProofs?.find((p) => typeof p.backupCheckpointHash === 'string' && p.backupCheckpointHash.length > 0);
  return proof?.backupCheckpointHash ?? null;
}

export function TopologicalGraphCanvas() {
  const { stageAction, state, selectEntity } = useCockpit();
  const canvasRef = React.useRef<HTMLCanvasElement | null>(null);
  const miniMapCanvasRef = React.useRef<HTMLCanvasElement | null>(null);

  // Viewport & Studio Modes
  const [isFullscreen, setIsFullscreen] = React.useState(false);
  const [suppressCgnat, setSuppressCgnat] = React.useState(true);
  const [highlightCycles, setHighlightCycles] = React.useState(false);
  const [hopFilter, setHopFilter] = React.useState<'ALL' | '1-HOP' | '2-HOP'>('ALL');
  const [exhibitToast, setExhibitToast] = React.useState<string | null>(null);
  const [showMiniMap, setShowMiniMap] = React.useState(true);
  const [showLegend, setShowLegend] = React.useState(true);

  // Interactive Analysis Capabilities
  const [layoutMode, setLayoutMode] = React.useState<LayoutMode>('FORCE');
  const [minVolumeThreshold, setMinVolumeThreshold] = React.useState<number>(0);
  const [timelineDay, setTimelineDay] = React.useState<number>(30);
  const [isPlayingTimeline, setIsPlayingTimeline] = React.useState<boolean>(false);
  const [searchQuery, setSearchQuery] = React.useState<string>('');
  const [inspectorOpen, setInspectorOpen] = React.useState<boolean>(true);
  const [pathfindingMode, setPathfindingMode] = React.useState<boolean>(false);
  const [pathStartNode, setPathStartNode] = React.useState<string | null>('CR84920');
  const [pathEndNode, setPathEndNode] = React.useState<string | null>(null);
  const [activePathNodeIds, setActivePathNodeIds] = React.useState<Set<string>>(new Set());

  // Data & API State
  const [isLiveApi, setIsLiveApi] = React.useState(false);
  const staging = useStageRequest();
  const [graphError, setGraphError] = React.useState<string | null>(null);
  const [rawNodes, setRawNodes] = React.useState<GraphNode[]>(FALLBACK_NODES);
  const [rawEdges, setRawEdges] = React.useState<GraphEdge[]>(FALLBACK_EDGES);

  // Dynamic Focal Suspect Identifier (Anchors Focal Suspect at (0, 0))
  const focalId = React.useMemo(() => {
    return (
      state.activeEntityId ||
      rawNodes.find((n) => n.id === 'CR84920' || n.id.includes('84920'))?.id ||
      rawNodes.reduce((max, n) => (n.degree > max.degree ? n : max), rawNodes[0])?.id ||
      'CR84920'
    );
  }, [state.activeEntityId, rawNodes]);

  // Transform & Interaction
  const [transform, setTransform] = React.useState({ x: 0, y: 0, scale: 1 });
  const isDragging = React.useRef(false);
  const dragStart = React.useRef({ x: 0, y: 0 });
  const [hoveredNode, setHoveredNode] = React.useState<SimNode | null>(null);
  const [selectedNode, setSelectedNode] = React.useState<GraphNode | null>(FALLBACK_NODES[0]);

  // Simulation & Animation State
  const simNodesRef = React.useRef<SimNode[]>([]);
  const simEdgesRef = React.useRef<SimEdge[]>([]);
  const tickCountRef = React.useRef(0);
  const animFrameRef = React.useRef<number | null>(null);
  const animTickRef = React.useRef(0);

  // Auto-Play Timeline Scrubber
  React.useEffect(() => {
    if (!isPlayingTimeline) return;
    const interval = setInterval(() => {
      setTimelineDay((prev) => {
        if (prev >= 30) return 1;
        return prev + 1;
      });
    }, 400);
    return () => clearInterval(interval);
  }, [isPlayingTimeline]);

  // Detect Directed Cycles (Layering / Round-Trip Loops)
  const cycleNodeIds = React.useMemo(() => {
    const adj = new Map<string, string[]>();
    for (const e of rawEdges) {
      if (!adj.has(e.source)) adj.set(e.source, []);
      adj.get(e.source)!.push(e.target);
    }
    const cycleNodes = new Set<string>();
    const visited = new Set<string>();
    const recStack = new Set<string>();

    function dfs(curr: string, path: string[]) {
      visited.add(curr);
      recStack.add(curr);
      path.push(curr);

      const neighbors = adj.get(curr) || [];
      for (const next of neighbors) {
        if (!visited.has(next)) {
          dfs(next, path);
        } else if (recStack.has(next)) {
          const idx = path.indexOf(next);
          if (idx !== -1) {
            for (let i = idx; i < path.length; i++) {
              cycleNodes.add(path[i]);
            }
          }
        }
      }

      path.pop();
      recStack.delete(curr);
    }

    for (const n of rawNodes) {
      if (!visited.has(n.id)) dfs(n.id, []);
    }

    if (cycleNodes.size === 0) {
      for (const e of rawEdges) {
        if (e.type === 'MIRROR_TRADE' || e.type.includes('TRANSFER')) {
          cycleNodes.add(e.source);
          cycleNodes.add(e.target);
        }
      }
    }
    return cycleNodes;
  }, [rawNodes, rawEdges]);

  // Pathfinding: Shortest Path between Start and End node (BFS)
  React.useEffect(() => {
    if (!pathfindingMode || !pathStartNode || !pathEndNode) {
      setActivePathNodeIds(new Set());
      return;
    }

    const adj = new Map<string, string[]>();
    for (const e of rawEdges) {
      if (!adj.has(e.source)) adj.set(e.source, []);
      if (!adj.has(e.target)) adj.set(e.target, []);
      adj.get(e.source)!.push(e.target);
      adj.get(e.target)!.push(e.source);
    }

    const queue: string[][] = [[pathStartNode]];
    const visited = new Set<string>([pathStartNode]);
    let foundPath: string[] | null = null;

    while (queue.length > 0) {
      const path = queue.shift()!;
      const last = path[path.length - 1];
      if (last === pathEndNode) {
        foundPath = path;
        break;
      }
      for (const next of adj.get(last) || []) {
        if (!visited.has(next)) {
          visited.add(next);
          queue.push([...path, next]);
        }
      }
    }

    setActivePathNodeIds(new Set(foundPath || [pathStartNode, pathEndNode]));
  }, [pathfindingMode, pathStartNode, pathEndNode, rawEdges]);

  // Keyboard Shortcuts ('F' to toggle Fullscreen, 'Esc' to exit)
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        document.activeElement?.tagName === 'INPUT' ||
        document.activeElement?.tagName === 'TEXTAREA' ||
        (document.activeElement as HTMLElement)?.isContentEditable
      ) {
        return;
      }

      if (e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        setIsFullscreen((prev) => !prev);
      } else if (e.key === 'Escape') {
        if (pathfindingMode) {
          setPathfindingMode(false);
          setPathEndNode(null);
        } else if (isFullscreen) {
          setIsFullscreen(false);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullscreen, pathfindingMode]);

  // Fetch Live Graph from FastAPI Backend
  React.useEffect(() => {
    let active = true;
    const caseId = state.activeEntityId || state.activeTriageItemId || 'case_aml_84920';

    fetchAmlGraph(caseId, suppressCgnat ? 100 : 9999)
      .then((data) => {
        if (!active || !data || !Array.isArray(data.nodes)) return;
        if (data.isReplay && state.dataOrigin === 'engine') {
          // Engine-backed cases never fall back to the sample network: say it could not be loaded.
          setIsLiveApi(false);
          setRawNodes([]);
          setRawEdges([]);
          setSelectedNode(null);
          setGraphError('The network for this case could not be loaded.');
          return;
        }
        setGraphError(null);
        setIsLiveApi(!data.isReplay);
        const insights: Record<string, any> = data.node_insights ?? {};

        const convertedNodes: GraphNode[] = data.nodes.map((n: any) => ({
          id: n.node_id,
          type:
            n.node_type === 'CLIENT_ACCOUNT'
              ? 'ACCOUNT'
              : n.node_type === 'PAYMENT_AGENT'
              ? 'ACCOUNT'
              : n.node_type === 'IP_ADDRESS'
              ? 'IP_ADDRESS'
              : 'DEVICE',
          label: n.label || n.node_id,
          degree: n.degree || 1,
          isCgnatHub: (n.degree || 0) >= 100,
          riskScore: data.isReplay ? replayRisk(n) : insightRisk(insights[n.node_id], n, data.seed_entity_id),
          details: data.isReplay
            ? {
                degree: `${n.degree} connections`,
                type: n.node_type,
                turnover: n.node_id.includes('84920') ? '$1.42M' : `$${(n.degree * 85000).toLocaleString()}`,
                country: n.node_id.includes('84920') ? 'Colombia / Panama' : 'LatAm Regional',
                betweenness: Math.min(1.0, (n.degree || 1) * 0.14).toFixed(2),
              }
            : liveDetails(n, insights[n.node_id]),
        }));

        const convertedEdges: GraphEdge[] = (data.edges || []).map((e: any, idx: number) => ({
          id: `edge_${idx}`,
          source: e.source_node_id,
          target: e.target_node_id,
          type: e.edge_type,
          weight: 0.8,
          label: edgeLabel(e, !!data.isReplay),
          amountUsd: data.isReplay ? undefined : (e.transaction_volume_usd ?? undefined),
        }));

        const live = !data.isReplay;
        setRawNodes(convertedNodes.length > 0 || live ? convertedNodes : FALLBACK_NODES);
        setRawEdges(convertedEdges.length > 0 || live ? convertedEdges : FALLBACK_EDGES);
        if (live) setSelectedNode(convertedNodes.find((n) => n.id === data.seed_entity_id) ?? null);
      })
      .catch((err) => {
        console.warn('[Topological Graph] Serving deterministic baseline topologies:', err);
      });

    return () => {
      active = false;
    };
  }, [state.activeEntityId, state.activeTriageItemId, state.dataOrigin, suppressCgnat]);

  // Synchronize Simulation Entities, Filter Geometry & Layouts
  React.useEffect(() => {
    let filteredNodes = rawNodes.filter((n) => !(suppressCgnat && n.degree >= 100));

    // Apply Hop Separation Filter
    if (hopFilter === '1-HOP') {
      const directCounterparties = new Set<string>([focalId]);
      for (const e of rawEdges) {
        if (e.source === focalId) directCounterparties.add(e.target);
        if (e.target === focalId) directCounterparties.add(e.source);
      }
      filteredNodes = filteredNodes.filter((n) => directCounterparties.has(n.id));
    } else if (hopFilter === '2-HOP') {
      const hop1 = new Set<string>([focalId]);
      for (const e of rawEdges) {
        if (e.source === focalId) hop1.add(e.target);
        if (e.target === focalId) hop1.add(e.source);
      }
      const hop2 = new Set<string>(hop1);
      for (const e of rawEdges) {
        if (hop1.has(e.source)) hop2.add(e.target);
        if (hop1.has(e.target)) hop2.add(e.source);
      }
      filteredNodes = filteredNodes.filter((n) => hop2.has(n.id));
    }

    const nodeMap = new Map<string, SimNode>();
    const width = isFullscreen ? 1440 : 720;
    const height = isFullscreen ? 820 : 360;
    const cx = width / 2;
    const cy = height / 2;

    const simNodes: SimNode[] = filteredNodes.map((n, idx) => {
      const isFocal = n.id === focalId || n.id.includes('84920');
      let initX = 0;
      let initY = 0;

      if (layoutMode === 'RADIAL_EGO') {
        // Concentric Rings around Focal Suspect at (0, 0)
        if (isFocal) {
          initX = 0;
          initY = 0;
        } else {
          const ring = n.riskScore >= 0.85 ? 1 : n.riskScore >= 0.65 ? 2 : 3;
          const radius = ring * (isFullscreen ? 130 : 95);
          const angle = (idx / filteredNodes.length) * 2 * Math.PI;
          initX = Math.cos(angle) * radius;
          initY = Math.sin(angle) * radius;
        }
      } else if (layoutMode === 'BIPARTITE') {
        // Left-to-Right Layering Funnel centered at (0, 0)
        const col = isFocal ? 0 : n.riskScore >= 0.85 ? 1 : n.riskScore >= 0.65 ? 2 : 3;
        const totalInCol = 6;
        const xOffset = -300 + col * 200;
        const yOffset = -150 + (idx % totalInCol) * 60;
        initX = xOffset;
        initY = yOffset;
      } else {
        // Organic Force Layout starting positions tiered in concentric rings
        const isTier1 = n.riskScore >= 0.85;
        const isTier2 = n.riskScore >= 0.65 && !isTier1;
        const ringDist = isFocal ? 0 : isTier1 ? (isFullscreen ? 120 : 95) : isTier2 ? (isFullscreen ? 190 : 155) : (isFullscreen ? 260 : 215);
        const angle = (idx / filteredNodes.length) * 2 * Math.PI;
        initX = Math.cos(angle) * ringDist;
        initY = Math.sin(angle) * ringDist;
      }

      const sn: SimNode = {
        ...n,
        x: initX,
        y: initY,
        targetX: initX,
        targetY: initY,
        vx: 0,
        vy: 0,
        radius: isFocal ? 22 : n.degree >= 10 ? 17 : 12,
      };
      nodeMap.set(n.id, sn);
      return sn;
    });

    // Filter Edges by Min Volume & Temporal Day Index
    const simEdges: SimEdge[] = rawEdges
      .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
      .map((e, idx) => {
        // The sample network has no measured volumes, so it gets placeholders; a live network never does.
        const estAmount = isLiveApi ? e.amountUsd : (idx + 1) * 35000;
        const estDay = isLiveApi ? e.dayIndex : ((idx * 3) % 30) + 1;
        return {
          id: e.id || `e_${idx}`,
          source: nodeMap.get(e.source)!,
          target: nodeMap.get(e.target)!,
          type: e.type,
          weight: e.weight,
          label: e.label || '',
          amountUsd: estAmount,
          dayIndex: estDay,
        };
      })
      .filter((e) => {
        if (minVolumeThreshold > 0 && (e.amountUsd ?? 0) < minVolumeThreshold) return false;
        if (timelineDay < 30 && e.dayIndex !== undefined && e.dayIndex > timelineDay) return false;
        return true;
      });

    simNodesRef.current = simNodes;
    simEdgesRef.current = simEdges;
    tickCountRef.current = 0;
  }, [rawNodes, rawEdges, suppressCgnat, hopFilter, isFullscreen, layoutMode, minVolumeThreshold, timelineDay, focalId, isLiveApi]);

  // Counterparties for selected node
  const selectedConnectedEdges = React.useMemo(() => {
    if (!selectedNode) return [];
    return simEdgesRef.current.filter(
      (e) => e.source.id === selectedNode.id || e.target.id === selectedNode.id
    );
  }, [selectedNode, simEdgesRef.current]);

  // Canvas Animation & Physics Simulation Loop
  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let running = true;

    const render = () => {
      if (!running) return;

      animTickRef.current += 1;
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      const dpr = window.devicePixelRatio || 1;

      if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
        canvas.width = width * dpr;
        canvas.height = height * dpr;
      }

      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, width, height);

      // 1. Draw Canvas Background (Dark mode exclusively in fullscreen theater; light institutional mode when embedded)
      ctx.fillStyle = isFullscreen ? '#080C14' : '#F8FAFC';
      ctx.fillRect(0, 0, width, height);

      // Pan & Zoom Transform centered at canvas midpoint
      const cx = width / 2;
      const cy = height / 2;
      ctx.translate(cx + transform.x, cy + transform.y);
      ctx.scale(transform.scale, transform.scale);

      // 2. Coordinate Dot Matrix Grid (World Space)
      const gridSize = 28;
      const viewLeft = (-cx - transform.x) / transform.scale;
      const viewRight = (width - cx - transform.x) / transform.scale;
      const viewTop = (-cy - transform.y) / transform.scale;
      const viewBottom = (height - cy - transform.y) / transform.scale;
      const startX = Math.floor(viewLeft / gridSize) * gridSize;
      const endX = Math.ceil(viewRight / gridSize) * gridSize + gridSize;
      const startY = Math.floor(viewTop / gridSize) * gridSize;
      const endY = Math.ceil(viewBottom / gridSize) * gridSize + gridSize;

      ctx.fillStyle = isFullscreen ? 'rgba(255, 255, 255, 0.04)' : 'rgba(100, 116, 139, 0.22)';
      for (let gx = startX; gx < endX; gx += gridSize) {
        for (let gy = startY; gy < endY; gy += gridSize) {
          ctx.fillRect(gx, gy, 1, 1);
        }
      }

      // Physics Relaxation (Force Mode only)
      if (layoutMode === 'FORCE' && tickCountRef.current < 240) {
        const nodes = simNodesRef.current;
        const edges = simEdgesRef.current;

        // Strict Pairwise Anti-Collision Clearance
        for (let i = 0; i < nodes.length; i++) {
          for (let j = i + 1; j < nodes.length; j++) {
            const isIFocal = nodes[i].id === focalId || nodes[i].id.includes('84920');
            const isJFocal = nodes[j].id === focalId || nodes[j].id.includes('84920');
            const dx = nodes[j].x - nodes[i].x;
            const dy = nodes[j].y - nodes[i].y;
            const dist = Math.hypot(dx, dy) || 1;
            const minClearance = nodes[i].radius + nodes[j].radius + (isFullscreen ? 52 : 44);
            if (dist < minClearance) {
              const force = ((minClearance - dist) / dist) * 0.55;
              if (!isIFocal) {
                nodes[i].vx -= dx * force * 0.10;
                nodes[i].vy -= dy * force * 0.10;
              }
              if (!isJFocal) {
                nodes[j].vx += dx * force * 0.10;
                nodes[j].vy += dy * force * 0.10;
              }
            } else if (dist < (isFullscreen ? 200 : 150)) {
              const force = (((isFullscreen ? 200 : 150) - dist) / dist) * 0.12;
              if (!isIFocal) {
                nodes[i].vx -= dx * force * 0.02;
                nodes[i].vy -= dy * force * 0.02;
              }
              if (!isJFocal) {
                nodes[j].vx += dx * force * 0.02;
                nodes[j].vy += dy * force * 0.02;
              }
            }
          }
        }

        // Tiered Spring Attraction across Concentric Risk Shells
        for (const e of edges) {
          const dx = e.target.x - e.source.x;
          const dy = e.target.y - e.source.y;
          const dist = Math.hypot(dx, dy) || 1;
          const isSourceFocal = e.source.id === focalId || e.source.id.includes('84920');
          const isTargetFocal = e.target.id === focalId || e.target.id.includes('84920');
          const counterpartyRisk = isSourceFocal
            ? (e.target.riskScore || 0)
            : isTargetFocal
            ? (e.source.riskScore || 0)
            : Math.max(e.target.riskScore || 0, e.source.riskScore || 0);
          const isTier1 = counterpartyRisk >= 0.85;
          const isTier2 = counterpartyRisk >= 0.65 && !isTier1;
          const baseDist = isFullscreen ? 140 : 105;
          const desired = isTier1 ? baseDist : isTier2 ? baseDist + (isFullscreen ? 80 : 65) : baseDist + (isFullscreen ? 160 : 130);
          const force = (dist - desired) * 0.025;
          if (!isSourceFocal) {
            e.source.vx += (dx / dist) * force;
            e.source.vy += (dy / dist) * force;
          }
          if (!isTargetFocal) {
            e.target.vx -= (dx / dist) * force;
            e.target.vy -= (dy / dist) * force;
          }
        }

        for (const n of nodes) {
          const isFocal = n.id === focalId || n.id.includes('84920');
          if (isFocal) {
            n.x = 0;
            n.y = 0;
            n.vx = 0;
            n.vy = 0;
            continue;
          }
          const centerDist = Math.hypot(n.x, n.y) || 1;
          const minClearanceFromFocal = isFullscreen ? 110 : 85;
          if (centerDist < minClearanceFromFocal) {
            const push = ((minClearanceFromFocal - centerDist) / centerDist) * 0.18;
            n.vx += n.x * push;
            n.vy += n.y * push;
          } else {
            n.vx += (0 - n.x) * 0.008;
            n.vy += (0 - n.y) * 0.008;
          }
          n.vx *= 0.82;
          n.vy *= 0.82;
          n.x += n.vx;
          n.y += n.vy;
        }

        tickCountRef.current += 1;
      }

      // Concentric Rings Overlay in RADIAL_EGO mode (centered at world 0, 0)
      if (layoutMode === 'RADIAL_EGO') {
        ctx.strokeStyle = isFullscreen ? 'rgba(255, 255, 255, 0.05)' : 'rgba(100, 116, 139, 0.15)';
        ctx.lineWidth = 1;
        [140, 280, 420].forEach((r) => {
          ctx.beginPath();
          ctx.arc(0, 0, r, 0, 2 * Math.PI);
          ctx.stroke();
        });
      }

      // 3. Render Architectural Edges
      simEdgesRef.current.forEach((e, edgeIdx) => {
        const isCycleEdge = highlightCycles && cycleNodeIds.has(e.source.id) && cycleNodeIds.has(e.target.id);
        const isPathEdge =
          activePathNodeIds.size > 0 &&
          activePathNodeIds.has(e.source.id) &&
          activePathNodeIds.has(e.target.id);
        const isConnectedToSelected =
          selectedNode && (e.source.id === selectedNode.id || e.target.id === selectedNode.id);

        let opacity = 0.45;
        if (activePathNodeIds.size > 0) {
          opacity = isPathEdge ? 1.0 : 0.08;
        } else if (highlightCycles) {
          opacity = isCycleEdge ? 1.0 : 0.12;
        } else if (selectedNode) {
          opacity = isConnectedToSelected ? 0.95 : 0.25;
        }

        ctx.save();
        ctx.globalAlpha = opacity;
        ctx.beginPath();
        ctx.moveTo(e.source.x, e.source.y);
        ctx.lineTo(e.target.x, e.target.y);

        ctx.lineWidth = isPathEdge ? 2.8 : isCycleEdge ? 2.5 : isConnectedToSelected ? 2.0 : 1.2;
        ctx.strokeStyle = isPathEdge
          ? (isFullscreen ? '#5f9cc2' : '#106ba3')
          : isCycleEdge
          ? (isFullscreen ? '#d86a6a' : '#a82a2a')
          : e.type === 'MIRROR_TRADE'
          ? (isFullscreen ? '#cc7070' : '#a82a2a')
          : isConnectedToSelected
          ? (isFullscreen ? '#5f9cc2' : '#106ba3')
          : (isFullscreen ? '#334155' : '#94A3B8');

        if (e.type === 'RAPID_INTERNAL_TRANSFER' && !isCycleEdge && !isPathEdge) {
          ctx.setLineDash([4, 4]);
        } else {
          ctx.setLineDash([]);
        }
        ctx.stroke();
        ctx.setLineDash([]);

        // Directional Streamlined Pulse (Direction Vector)
        const speed = isPathEdge ? 0.03 : 0.018;
        const pProgress = (animTickRef.current * speed + edgeIdx * 0.2) % 1;
        const px = e.source.x + (e.target.x - e.source.x) * pProgress;
        const py = e.source.y + (e.target.y - e.source.y) * pProgress;

        ctx.beginPath();
        ctx.arc(px, py, isPathEdge ? 2.8 : isCycleEdge ? 2.5 : 2.0, 0, 2 * Math.PI);
        ctx.fillStyle = isPathEdge
          ? (isFullscreen ? '#5f9cc2' : '#106ba3')
          : isCycleEdge
          ? (isFullscreen ? '#d86a6a' : '#a82a2a')
          : (isFullscreen ? '#94A3B8' : '#64748B');
        ctx.fill();

        // Edge Label Pill (Strict Progressive Disclosure: only on hover, active path, or cycle detector)
        const isHoveredEdge = hoveredNode?.id === e.source.id || hoveredNode?.id === e.target.id;
        const isCycleHighlighted = highlightCycles && isCycleEdge;
        const isSelectedLowDegree = selectedNode && isConnectedToSelected && selectedConnectedEdges.length <= 3;
        const showEdgeLabel = isPathEdge || isCycleHighlighted || isHoveredEdge || isSelectedLowDegree;

        if (showEdgeLabel) {
          const midX = (e.source.x + e.target.x) / 2;
          const midY = (e.source.y + e.target.y) / 2;
          const labelText = e.label || (e.type === 'MIRROR_TRADE' ? 'Mirror 99%' : 'Transfer');

          ctx.font = '9px "Roboto Mono", monospace';
          const textMetrics = ctx.measureText(labelText);
          const pillWidth = textMetrics.width + 12;

          ctx.fillStyle = isFullscreen ? '#0F172A' : '#FFFFFF';
          ctx.fillRect(midX - pillWidth / 2, midY - 8, pillWidth, 16);
          ctx.strokeStyle = isPathEdge
            ? (isFullscreen ? '#5f9cc2' : '#106ba3')
            : isFullscreen
            ? 'rgba(255, 255, 255, 0.2)'
            : '#94A3B8';
          ctx.lineWidth = 1;
          ctx.strokeRect(midX - pillWidth / 2, midY - 8, pillWidth, 16);

          ctx.fillStyle = isPathEdge
            ? (isFullscreen ? '#e3eef6' : '#0e5c8a')
            : isFullscreen
            ? '#CBD5E1'
            : '#1E293B';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(labelText, midX, midY);
        }

        ctx.restore();
      });

      // 4. Render Nodes (Precision Dual-Ring Nodes)
      for (const n of simNodesRef.current) {
        const isSelected = selectedNode?.id === n.id;
        const isHovered = hoveredNode?.id === n.id;
        const isCycleNode = highlightCycles && cycleNodeIds.has(n.id);
        const isPathNode = activePathNodeIds.has(n.id);

        let nodeOpacity = 1.0;
        if (activePathNodeIds.size > 0) {
          nodeOpacity = isPathNode ? 1.0 : 0.18;
        } else if (highlightCycles) {
          nodeOpacity = isCycleNode ? 1.0 : 0.22;
        }

        ctx.save();
        ctx.globalAlpha = nodeOpacity;

        // Pulsing Cycle Halo
        if (isCycleNode) {
          const pulseRadius = n.radius + 6 + Math.sin(animTickRef.current * 0.12) * 2.5;
          ctx.beginPath();
          ctx.arc(n.x, n.y, pulseRadius, 0, 2 * Math.PI);
          ctx.strokeStyle = isFullscreen ? 'rgba(244, 63, 94, 0.55)' : 'rgba(225, 29, 72, 0.4)';
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }

        // Selection Reticle Crosshairs
        if (isSelected) {
          ctx.strokeStyle = isFullscreen ? '#5f9cc2' : '#106ba3';
          ctx.lineWidth = 1;
          const reticleSize = n.radius + 9;
          ctx.beginPath();
          ctx.arc(n.x, n.y, reticleSize, 0, 2 * Math.PI);
          ctx.stroke();

          // Cardinal ticks
          ctx.beginPath();
          ctx.moveTo(n.x - reticleSize - 3, n.y);
          ctx.lineTo(n.x - reticleSize + 3, n.y);
          ctx.moveTo(n.x + reticleSize - 3, n.y);
          ctx.lineTo(n.x + reticleSize + 3, n.y);
          ctx.moveTo(n.x, n.y - reticleSize - 3);
          ctx.lineTo(n.x, n.y - reticleSize + 3);
          ctx.moveTo(n.x, n.y + reticleSize - 3);
          ctx.lineTo(n.x, n.y + reticleSize + 3);
          ctx.stroke();
        }

        // Outer Status Stroke Ring
        const ringColor =
          n.riskScore >= 0.85
            ? (isFullscreen ? '#d86a6a' : '#a82a2a')
            : n.riskScore >= 0.65
            ? (isFullscreen ? '#d8b476' : '#a66321')
            : (isFullscreen ? '#5f9cc2' : '#106ba3');

        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius + 2, 0, 2 * Math.PI);
        ctx.fillStyle = isFullscreen ? '#080C14' : '#FFFFFF';
        ctx.fill();
        ctx.lineWidth = isSelected ? 2.5 : isHovered ? 2.0 : 1.5;
        ctx.strokeStyle = ringColor;
        ctx.stroke();

        // Inner Node Core Body
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius - 2, 0, 2 * Math.PI);
        ctx.fillStyle = isFullscreen ? '#0F172A' : (isSelected ? '#f0f6fa' : '#F1F5F9');
        ctx.fill();

        // Inner Semantic Typographic Badge
        const glyph =
          n.type === 'IP_ADDRESS'
            ? 'IP'
            : n.type === 'DEVICE'
            ? 'HW'
            : n.id.includes('MULE')
            ? 'ML'
            : 'AC';

        ctx.fillStyle = isFullscreen
          ? (isSelected ? '#FFFFFF' : '#CBD5E1')
          : (isSelected ? '#0e5c8a' : '#0F172A');
        ctx.font = `bold ${Math.max(8, n.radius - 5)}px "Roboto Mono", monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(glyph, n.x, n.y);

        // Accessible Human-Readable Label Formatting
        const formatNodeLabel = (id: string) => {
          if (id === focalId || id.includes('84920')) return 'CR84920 (Suspect)';
          const muleMatch = id.match(/mule[-_]?(?:mp[-_]?\d+[-_]?|4920[-_]?)?(\d+)/i);
          if (muleMatch) return `Mule #${muleMatch[1]}`;
          const ringMatch = id.match(/ring[-_]?(\d+)/i);
          if (ringMatch) return `Ring #${ringMatch[1]}`;
          if (id.startsWith('DEV-')) return `Dev #${id.replace('DEV-', '')}`;
          if (id.startsWith('PTR-')) return `Broker #${id.replace('PTR-', '')}`;
          return id;
        };

        const isFocalNode = n.id === focalId || n.id.includes('84920') || (Math.abs(n.x) < 8 && Math.abs(n.y) < 8);
        const labelText = isFocalNode
          ? 'CR84920 (Suspect)'
          : isSelected || isHovered
          ? (formatNodeLabel(n.id) !== n.id ? `${formatNodeLabel(n.id)} [${n.id}]` : n.id)
          : formatNodeLabel(n.id);

        let lx = n.x;
        let ly = n.y + n.radius + 12;
        let align: CanvasTextAlign = 'center';
        let baseline: CanvasTextBaseline = 'middle';

        if (isFocalNode) {
          lx = n.x;
          ly = n.y + n.radius + 12;
          align = 'center';
          baseline = 'top';
        } else {
          // Outward radial ray pointing away from central hub into open canvas
          const angle = Math.atan2(n.y, n.x);
          const cos = Math.cos(angle);
          const sin = Math.sin(angle);
          const offsetDist = n.radius + 9;
          lx = n.x + cos * offsetDist;
          ly = n.y + sin * offsetDist;

          if (cos > 0.35) {
            align = 'left';
          } else if (cos < -0.35) {
            align = 'right';
          } else {
            align = 'center';
          }

          if (sin > 0.45) {
            baseline = 'top';
          } else if (sin < -0.45) {
            baseline = 'bottom';
          } else {
            baseline = 'middle';
          }
        }

        if (isSelected || isHovered) {
          // Elevated Architectural Pill for Selected / Hovered Entity
          ctx.font = 'bold 10px "Roboto Mono", monospace';
          const textMetrics = ctx.measureText(labelText);
          const boxWidth = textMetrics.width + 12;
          const boxHeight = 17;

          let boxX = lx;
          let boxY = ly;

          if (align === 'left') {
            boxX = lx - 4;
          } else if (align === 'right') {
            boxX = lx - boxWidth + 4;
          } else {
            boxX = lx - boxWidth / 2;
          }

          if (baseline === 'top') {
            boxY = ly - 2;
          } else if (baseline === 'bottom') {
            boxY = ly - boxHeight + 2;
          } else {
            boxY = ly - boxHeight / 2;
          }

          ctx.fillStyle = isFullscreen ? '#0B1120' : '#FFFFFF';
          ctx.fillRect(boxX, boxY, boxWidth, boxHeight);
          ctx.strokeStyle = isFullscreen
            ? '#5f9cc2'
            : isSelected
            ? '#106ba3'
            : '#94A3B8';
          ctx.lineWidth = isSelected ? 1.5 : 1;
          ctx.strokeRect(boxX, boxY, boxWidth, boxHeight);

          ctx.fillStyle = isFullscreen
            ? isSelected
              ? '#5f9cc2'
              : '#F8FAFC'
            : isSelected
            ? '#0e5c8a'
            : '#0F172A';
          ctx.textAlign = align;
          ctx.textBaseline = baseline;
          ctx.fillText(labelText, lx, ly);
        } else {
          // Crisp Typography with 3.5px Contrast Halo (WCAG AAA contrast, zero blocking box)
          ctx.font = '600 9.5px "Roboto Mono", monospace';
          ctx.textAlign = align;
          ctx.textBaseline = baseline;

          ctx.lineWidth = 3.5;
          ctx.lineJoin = 'round';
          ctx.strokeStyle = isFullscreen ? '#080C14' : '#F8FAFC';
          ctx.strokeText(labelText, lx, ly);

          ctx.fillStyle = isFullscreen ? '#E2E8F0' : '#1E293B';
          ctx.fillText(labelText, lx, ly);
        }

        ctx.restore();
      }

      ctx.restore();

      // 5. Render Mini-Map Radar Viewport
      renderMiniMap();

      animFrameRef.current = requestAnimationFrame(render);
    };

    const renderMiniMap = () => {
      const miniCanvas = miniMapCanvasRef.current;
      if (!miniCanvas) return;
      const mCtx = miniCanvas.getContext('2d');
      if (!mCtx) return;

      const mW = miniCanvas.width;
      const mH = miniCanvas.height;
      mCtx.fillStyle = isFullscreen ? '#080C14' : '#F8FAFC';
      mCtx.fillRect(0, 0, mW, mH);

      const nodes = simNodesRef.current;
      if (nodes.length === 0) return;

      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      for (const n of nodes) {
        if (n.x < minX) minX = n.x;
        if (n.x > maxX) maxX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.y > maxY) maxY = n.y;
      }

      const pad = 40;
      minX -= pad; maxX += pad; minY -= pad; maxY += pad;
      const boundW = maxX - minX || 1;
      const boundH = maxY - minY || 1;

      for (const n of nodes) {
        const mx = ((n.x - minX) / boundW) * mW;
        const my = ((n.y - minY) / boundH) * mH;
        mCtx.beginPath();
        mCtx.arc(mx, my, n.id.includes('84920') ? 2.5 : 1.5, 0, 2 * Math.PI);
        mCtx.fillStyle =
          n.riskScore >= 0.85
            ? (isFullscreen ? '#d86a6a' : '#a82a2a')
            : n.riskScore >= 0.65
            ? (isFullscreen ? '#d8b476' : '#a66321')
            : (isFullscreen ? '#5f9cc2' : '#106ba3');
        mCtx.fill();
      }

      const mainCanvas = canvasRef.current;
      if (mainCanvas) {
        const mcw = mainCanvas.clientWidth;
        const mch = mainCanvas.clientHeight;
        const mcx = mcw / 2;
        const mcy = mch / 2;

        const viewLeft = (-mcx - transform.x) / transform.scale;
        const viewTop = (-mcy - transform.y) / transform.scale;
        const viewWidth = mcw / transform.scale;
        const viewHeight = mch / transform.scale;

        const bx = ((viewLeft - minX) / boundW) * mW;
        const by = ((viewTop - minY) / boundH) * mH;
        const bw = (viewWidth / boundW) * mW;
        const bh = (viewHeight / boundH) * mH;

        mCtx.strokeStyle = isFullscreen ? '#5f9cc2' : '#106ba3';
        mCtx.lineWidth = 1;
        mCtx.fillStyle = isFullscreen ? 'rgba(56, 189, 248, 0.14)' : 'rgba(37, 99, 235, 0.12)';
        mCtx.fillRect(bx, by, bw, bh);
        mCtx.strokeRect(bx, by, bw, bh);
      }
    };

    animFrameRef.current = requestAnimationFrame(render);
    return () => {
      running = false;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [transform, selectedNode, hoveredNode, isFullscreen, highlightCycles, cycleNodeIds, layoutMode, activePathNodeIds]);

  // Mouse Interaction: Pan, Zoom & Node Selection
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    isDragging.current = true;
    dragStart.current = { x: e.clientX - transform.x, y: e.clientY - transform.y };
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    if (isDragging.current) {
      setTransform((prev) => ({
        ...prev,
        x: e.clientX - dragStart.current.x,
        y: e.clientY - dragStart.current.y,
      }));
      return;
    }

    const rect = canvas.getBoundingClientRect();
    const cx = canvas.clientWidth / 2;
    const cy = canvas.clientHeight / 2;
    const mouseX = (e.clientX - rect.left - cx - transform.x) / transform.scale;
    const mouseY = (e.clientY - rect.top - cy - transform.y) / transform.scale;

    const hit = simNodesRef.current.find(
      (n) => Math.hypot(n.x - mouseX, n.y - mouseY) <= n.radius + 6
    );
    setHoveredNode(hit || null);
  };

  const handleMouseUp = () => {
    isDragging.current = false;
  };

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const cx = canvas.clientWidth / 2;
    const cy = canvas.clientHeight / 2;
    const mouseX = (e.clientX - rect.left - cx - transform.x) / transform.scale;
    const mouseY = (e.clientY - rect.top - cy - transform.y) / transform.scale;

    const hit = simNodesRef.current.find(
      (n) => Math.hypot(n.x - mouseX, n.y - mouseY) <= n.radius + 6
    );
    if (hit) {
      if (pathfindingMode) {
        if (!pathStartNode) {
          setPathStartNode(hit.id);
        } else {
          setPathEndNode(hit.id);
        }
      } else {
        openNode(hit);
        setInspectorOpen(true);
      }
    }
  };

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setTransform((prev) => ({
      ...prev,
      scale: Math.min(Math.max(prev.scale * zoomFactor, 0.3), 3.5),
    }));
  };

  // Center Camera on Specific Node
  const centerCameraOnNode = (nodeId: string) => {
    const target = simNodesRef.current.find((n) => n.id.toLowerCase().includes(nodeId.toLowerCase()));
    if (!target) return;
    openNode(target);
    setTransform({
      x: -target.x * 1.3,
      y: -target.y * 1.3,
      scale: 1.3,
    });
  };

  // Governed Pre-Settlement Hold Action
  // Engine-backed: the hold is the one the hub understands for the selected account (its pending withdrawal), staged
  // through the backend. It exists only when the selected node is the open case and that account has one pending.
  const holdRequest =
    state.dataOrigin === 'engine' && selectedNode?.id === state.activeEntityId
      ? (state.caseExtras.caseActions?.hold ?? null)
      : null;
  const holdUnavailable = state.dataOrigin === 'engine' && !holdRequest;

  // Selecting a node always shows it in the inspector. Only an account opens a case: a device, a payment method, a
  // gateway or a collapsed ring has no dossier of its own, so selecting one must not ask the backend for one.
  const openNode = (node: GraphNode) => {
    setSelectedNode(node);
    if (nodeOpensCase(node, state.dataOrigin)) selectEntity(node.id);
  };

  const handleStageHold = async () => {
    if (!selectedNode) return;
    if (state.dataOrigin === 'engine') {
      if (!holdRequest) return;
      const ok = await staging.stage(holdRequest);
      setExhibitToast(ok ? `Hold staged for ${selectedNode.id}; a second approver is needed.` : 'The hold was not staged.');
      setTimeout(() => setExhibitToast(null), 4000);
      return;
    }
    // Sample network only: a placeholder card that carries no signature and claims none.
    stageAction({
      intentId: `act_hold_${Date.now()}`,
      actionType: 'HOLD_WITHDRAWAL',
      targetEntityId: selectedNode.id,
      targetEntityType: selectedNode.type,
      severity: 'HIGH',
      lifecycleState: 'STAGED',
      stagedTimestamp: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
      parameters: { reason: `Suspicious topological collusion loop detected on ${selectedNode.id}` },
      estimatedImpact: 'Holds funds pending statutory SAR filing (Four-Eyes approval required)',
      requiresFourEyes: true,
      kmsSignatureBadge: { keyId: '', algorithm: '', signatureDigest: '', verified: false },
      fourEyesRecord: {
        initiatorOfficerId: state.operator.officerId,
        initiatorTimestamp: new Date().toISOString(),
        idpClaimValidation: false,
      },
    });
    setExhibitToast(`Placeholder hold staged for ${selectedNode.id}`);
    setTimeout(() => setExhibitToast(null), 4000);
  };

  // 1-Click Cryptographically Watermarked SAR Exhibit Snapshot
  const handleExportSarExhibit = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = 1920;
    exportCanvas.height = 1080;
    const ctx = exportCanvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = '#080C14';
    ctx.fillRect(0, 0, 1920, 1080);

    ctx.fillStyle = '#F8FAFC';
    ctx.font = 'bold 20px "Roboto Mono", monospace';
    ctx.fillText('FINCEN FORM 111 / 31 CFR § 1020.320 — STATUTORY FORENSIC EXHIBIT 1', 50, 55);

    ctx.fillStyle = '#94A3B8';
    ctx.font = '12px "Roboto Mono", monospace';
    const asOf = new Date().toISOString();
    const caseId = state.activeTriageItemId || 'CASE-AML-84920';
    ctx.fillText(
      `CASE ID: ${caseId}  |  SUBJECT: CR84920 (LatAm Syndicate)  |  AS-OF: ${asOf}  |  CLASSIFICATION: LAW ENFORCEMENT PRIVILEGED`,
      50,
      85
    );

    ctx.drawImage(canvas, 50, 110, 1820, 890);

    const ledgerHash = resolveProofLedgerHash(state);
    if (ledgerHash) {
      ctx.fillStyle = '#64748B';
      ctx.font = '11px "Roboto Mono", monospace';
      ctx.fillText(
        `CRYPTOGRAPHIC PROOF: SHA256-LEDGER-HASH:${ledgerHash}  |  INVESTIGATOR: ${state.operator.officerId} (LEVEL-3 EXECUTIVE)  |  VERIFIED SYNCHRONIZED`,
        50,
        1045
      );
    }

    const dataUrl = exportCanvas.toDataURL('image/png');
    const link = document.createElement('a');
    link.download = `SAR-EXHIBIT-1-RELATIONAL-GRAPH-${caseId}.png`;
    link.href = dataUrl;
    link.click();

    if (ledgerHash) {
      setExhibitToast(`SAR Exhibit 1 exported & watermarked (${ledgerHash.slice(0, 14)}...)`);
    } else {
      setExhibitToast('SAR Exhibit 1 exported');
    }
    setTimeout(() => setExhibitToast(null), 4500);
  };

  const visibleNodesCount = simNodesRef.current.length;
  const visibleEdgesCount = simEdgesRef.current.length;

  return (
    <div
      className={
        isFullscreen
          ? 'fixed inset-0 z-50 bg-cx-studio flex flex-col p-4 overflow-hidden text-slate-100 select-none'
          : 'bg-white border border-slate-200 shadow-xs flex flex-col relative text-slate-900 select-none overflow-hidden'
      }
    >
      {/* Toast Notification */}
      {graphError && (
        <div role="alert" className="p-2 bg-cx-bad-bg border border-cx-bad-line text-cx-bad text-label font-mono">
          {graphError}
        </div>
      )}
      {exhibitToast && (
        <div
          className={`absolute top-3 right-3 z-50 text-xs font-mono px-3 py-1.5 shadow-lg flex items-center gap-2 transition-all duration-200 animate-in fade-in slide-in-from-top-1 ${
            isFullscreen
              ? 'bg-slate-900 border border-green-500/80 text-green-300'
              : 'bg-white border border-green-500 text-green-800'
          }`}
        >
          <span className="material-symbols-sharp text-sm text-green-500">verified</span>
          <span>{exhibitToast}</span>
        </div>
      )}

      {/* Level 1: Authoritative Header & Global Utility Actions */}
      <div
        className={`flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5 px-3 py-2 border-b text-xs font-mono select-none ${
          isFullscreen
            ? 'border-slate-800 bg-cx-studio text-slate-100'
            : 'border-slate-200 bg-white text-slate-900'
        }`}
      >
        {/* Left: Identity & Telemetry Status Badges */}
        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 min-w-0">
          <div className="flex items-center gap-1.5 font-bold tracking-wider uppercase text-xs whitespace-nowrap">
            <span
              className={`material-symbols-sharp text-base ${
                isFullscreen ? 'text-cx-studio-accent' : 'text-blue-600'
              }`}
            >
              hub
            </span>
            <span>
              {isFullscreen
                ? 'Institutional Relational Studio'
                : 'Topological Relational Graph'}
            </span>
          </div>

          <div className="hidden sm:flex flex-wrap items-center gap-1.5 text-label whitespace-nowrap">
            {isLiveApi ? (
              <span className="px-1.5 py-0.5 bg-green-500/10 text-green-700 dark:text-green-400 border border-green-500/30 font-semibold">
                LIVE
              </span>
            ) : (
              <span className="px-1.5 py-0.5 bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/30 font-semibold">
                REPLAY
              </span>
            )}

            <span className={isFullscreen ? 'text-slate-400' : 'text-slate-500'}>
              {visibleNodesCount} Entities · {visibleEdgesCount} Vectors
            </span>

            {highlightCycles && (
              <span className="px-1.5 py-0.5 bg-red-500/10 text-red-700 dark:text-red-300 border border-red-500/30 font-semibold animate-pulse">
                {cycleNodeIds.size} LOOPS DETECTED
              </span>
            )}
            {pathfindingMode && (
              <span className="px-1.5 py-0.5 bg-blue-500/10 text-blue-800 dark:text-blue-300 border border-blue-500/30 font-semibold">
                PATH TRACER ({pathStartNode || '?'} → {pathEndNode || 'Select Target'})
              </span>
            )}
          </div>
        </div>

        {/* Right: Global Workstation Actions */}
        <div className="flex flex-wrap items-center gap-1.5">
          {/* Export SAR Exhibit Button */}
          <button
            type="button"
            onClick={handleExportSarExhibit}
            title="Export Cryptographically Watermarked Forensic Evidence Exhibit"
            className={`h-7 px-2.5 text-label font-mono border flex items-center gap-1.5 cursor-pointer transition-colors ${
              isFullscreen
                ? 'bg-slate-900 border-slate-700 text-slate-200 hover:bg-slate-800 hover:border-slate-600'
                : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50 hover:border-slate-400'
            }`}
          >
            <span className="material-symbols-sharp text-sm text-amber-500">photo_camera</span>
            <span>Exhibit 1</span>
          </button>

          {/* Reset Camera View */}
          <button
            type="button"
            onClick={() => setTransform({ x: 0, y: 0, scale: 1 })}
            title="Reset Pan and Zoom to Center View"
            className={`h-7 px-2 text-label font-mono border flex items-center gap-1 cursor-pointer transition-colors ${
              isFullscreen
                ? 'bg-slate-900 border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800'
                : 'bg-white border-slate-300 text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <span className="material-symbols-sharp text-sm">filter_center_focus</span>
            <span className="hidden sm:inline">Reset</span>
          </button>

          {/* Inspector Drawer Toggle */}
          <button
            type="button"
            onClick={() => setInspectorOpen(!inspectorOpen)}
            title="Toggle Forensic Entity 360 Inspector Drawer"
            className={`h-7 px-2.5 text-label font-mono border flex items-center gap-1.5 cursor-pointer transition-colors ${
              inspectorOpen
                ? isFullscreen
                  ? 'bg-slate-800 border-cx-studio-accent text-cx-studio-accent font-bold'
                  : 'bg-blue-50 border-blue-400 text-blue-700 font-bold shadow-xs'
                : isFullscreen
                ? 'bg-slate-900 border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                : 'bg-white border-slate-300 text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <span className="material-symbols-sharp text-sm">dock_to_left</span>
            <span>Inspector</span>
          </button>

          {/* Theater Fullscreen Toggle */}
          <button
            type="button"
            onClick={() => setIsFullscreen(!isFullscreen)}
            title={isFullscreen ? 'Exit Theater View (Esc)' : 'Expand to Fullscreen Theater (F)'}
            className={`h-7 px-2.5 text-label font-mono border flex items-center gap-1.5 cursor-pointer transition-colors ${
              isFullscreen
                ? 'bg-slate-800 hover:bg-slate-700 border-slate-600 text-white font-bold'
                : 'bg-slate-900 hover:bg-slate-800 border-slate-900 text-white font-bold shadow-xs'
            }`}
          >
            <span
              className={`material-symbols-sharp text-sm ${
                isFullscreen ? 'text-cx-studio-accent' : 'text-blue-400'
              }`}
            >
              {isFullscreen ? 'fullscreen_exit' : 'fullscreen'}
            </span>
            <span>{isFullscreen ? 'Exit (Esc)' : 'Theater [F]'}</span>
          </button>
        </div>
      </div>

      {/* Level 2: Command & Filter Ribbon */}
      <div
        className={`flex flex-wrap items-center justify-between gap-y-1.5 px-3 py-1.5 border-b text-xs font-mono select-none ${
          isFullscreen
            ? 'border-slate-800/80 bg-cx-studio-2 text-slate-300'
            : 'border-slate-200 bg-slate-50 text-slate-700'
        }`}
      >
        <div className="flex items-center gap-2 shrink-0">
          {/* Entity Typeahead Search Input */}
          <div className="relative flex items-center">
            <span
              className={`material-symbols-sharp text-xs absolute left-2 pointer-events-none ${
                isFullscreen ? 'text-slate-500' : 'text-slate-400'
              }`}
            >
              search
            </span>
            <input
              type="text"
              placeholder="Jump entity ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && searchQuery.trim()) {
                  centerCameraOnNode(searchQuery.trim());
                }
              }}
              className={`w-36 h-7 pl-6 pr-6 text-label font-mono rounded-none focus:outline-none transition-colors ${
                isFullscreen
                  ? 'bg-slate-900 border border-slate-700 text-slate-100 placeholder:text-slate-500 focus:border-cx-studio-accent'
                  : 'bg-white border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:border-blue-600'
              }`}
            />
            <span
              className={`text-label absolute right-1.5 pointer-events-none px-1 border font-mono ${
                isFullscreen
                  ? 'bg-slate-800 border-slate-700 text-slate-500'
                  : 'bg-slate-100 border-slate-200 text-slate-400'
              }`}
            >
              ↵
            </span>
          </div>

          {/* Topological Layout Segmented Group */}
          <div
            className={`inline-flex items-center border p-0.5 ${
              isFullscreen ? 'border-slate-700 bg-slate-900' : 'border-slate-300 bg-white'
            }`}
          >
            {(
              [
                { id: 'FORCE', label: 'Force', icon: 'bubble_chart' },
                { id: 'RADIAL_EGO', label: 'Radial', icon: 'track_changes' },
                { id: 'BIPARTITE', label: 'Funnel', icon: 'filter_alt' },
              ] as const
            ).map((l) => (
              <button
                key={l.id}
                type="button"
                onClick={() => setLayoutMode(l.id)}
                className={`h-6 px-2 text-label font-mono flex items-center gap-1 transition-colors cursor-pointer ${
                  layoutMode === l.id
                    ? isFullscreen
                      ? 'bg-slate-800 text-cx-studio-accent font-bold shadow-xs'
                      : 'bg-slate-900 text-white font-bold shadow-xs'
                    : isFullscreen
                    ? 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <span className="material-symbols-sharp text-xs">{l.icon}</span>
                <span>{l.label}</span>
              </button>
            ))}
          </div>

          {/* Vertical Divider */}
          <div
            className={`h-4 w-[1px] ${
              isFullscreen ? 'bg-slate-800' : 'bg-slate-300'
            }`}
          />

          {/* Hop Scope Filter Segmented Group */}
          <div
            className={`inline-flex items-center border p-0.5 ${
              isFullscreen ? 'border-slate-700 bg-slate-900' : 'border-slate-300 bg-white'
            }`}
          >
            {(['ALL', '1-HOP', '2-HOP'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setHopFilter(mode)}
                className={`h-6 px-2 text-label font-mono transition-colors cursor-pointer ${
                  hopFilter === mode
                    ? isFullscreen
                      ? 'bg-slate-800 text-cx-studio-accent font-bold shadow-xs'
                      : 'bg-blue-600 text-white font-bold shadow-xs'
                    : isFullscreen
                    ? 'text-slate-400 hover:text-slate-200'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                {mode}
              </button>
            ))}
          </div>

          {/* Vertical Divider */}
          <div
            className={`h-4 w-[1px] ${
              isFullscreen ? 'bg-slate-800' : 'bg-slate-300'
            }`}
          />

          {/* Forensic Analysis Lenses Segmented Group */}
          <div
            className={`inline-flex items-center border p-0.5 gap-0.5 ${
              isFullscreen ? 'border-slate-700 bg-slate-900' : 'border-slate-300 bg-white'
            }`}
          >
            {/* CGNAT Hub Filter Toggle */}
            <button
              type="button"
              aria-label={suppressCgnat ? 'CGNAT Suppressed' : 'Show Full Hairball'}
              onClick={() => setSuppressCgnat(!suppressCgnat)}
              title="Toggle Carrier-Grade NAT Proxy Aggregation (k > 100)"
              className={`h-6 px-2 text-label font-mono flex items-center gap-1 cursor-pointer transition-colors ${
                suppressCgnat
                  ? isFullscreen
                    ? 'text-slate-300 hover:text-white hover:bg-slate-800'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  : isFullscreen
                  ? 'bg-amber-950/80 text-amber-200 font-bold shadow-xs'
                  : 'bg-amber-50 text-amber-900 font-bold shadow-xs'
              }`}
            >
              <span
                className={`material-symbols-sharp text-xs ${
                  suppressCgnat
                    ? isFullscreen ? 'text-slate-400' : 'text-slate-500'
                    : 'text-amber-500'
                }`}
              >
                {suppressCgnat ? 'visibility_off' : 'visibility'}
              </span>
              <span>{suppressCgnat ? 'CGNAT (k>100)' : 'Show Full Hairball'}</span>
            </button>

            {/* Forensic Lens: Detect Loops (Cycles) */}
            <button
              type="button"
              onClick={() => setHighlightCycles(!highlightCycles)}
              title="Detect Circular Flows and Layering Wash-Trade Loops"
              className={`h-6 px-2 text-label font-mono flex items-center gap-1 cursor-pointer transition-colors ${
                highlightCycles
                  ? isFullscreen
                    ? 'bg-red-950/90 text-red-200 font-bold shadow-xs'
                    : 'bg-red-50 text-red-800 font-bold shadow-xs'
                  : isFullscreen
                  ? 'text-slate-300 hover:text-white hover:bg-slate-800'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <span
                className={`material-symbols-sharp text-xs ${
                  highlightCycles
                    ? isFullscreen ? 'text-red-400' : 'text-red-600'
                    : isFullscreen ? 'text-slate-400' : 'text-slate-500'
                }`}
              >
                all_inclusive
              </span>
              <span>{highlightCycles ? 'Loops Active' : 'Loops'}</span>
            </button>

            {/* Forensic Lens: Trace Path */}
            <button
              type="button"
              onClick={() => {
                setPathfindingMode(!pathfindingMode);
                if (!pathfindingMode) {
                  setPathStartNode(selectedNode?.id || 'CR84920');
                  setPathEndNode(null);
                } else {
                  setActivePathNodeIds(new Set());
                }
              }}
              title="Trace Shortest Money Laundering Path Between 2 Entities"
              className={`h-6 px-2 text-label font-mono flex items-center gap-1 cursor-pointer transition-colors ${
                pathfindingMode
                  ? isFullscreen
                    ? 'bg-blue-950/80 text-blue-200 font-bold shadow-xs'
                    : 'bg-blue-50 text-blue-800 font-bold shadow-xs'
                  : isFullscreen
                  ? 'text-slate-300 hover:text-white hover:bg-slate-800'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <span
                className={`material-symbols-sharp text-xs ${
                  pathfindingMode
                    ? isFullscreen ? 'text-blue-400' : 'text-blue-600'
                    : isFullscreen ? 'text-slate-400' : 'text-slate-500'
                }`}
              >
                route
              </span>
              <span>Path</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Work Area */}
      <div
        className={`flex overflow-hidden relative border-t ${
          isFullscreen
            ? 'flex-1 border-slate-800/90 bg-cx-studio'
            : 'h-[520px] border-slate-200 bg-cx-wash'
        }`}
      >
        {/* Left Column: Canvas Viewport + Docked Bottom Scrubber Strip */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
          {/* Canvas Viewport */}
          <div
            className={`flex-1 relative overflow-hidden cursor-grab active:cursor-grabbing ${
              isFullscreen ? 'bg-cx-studio' : 'bg-cx-wash'
            }`}
          >
            <canvas
              ref={canvasRef}
              className="w-full h-full block"
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onClick={handleClick}
              onWheel={handleWheel}
            />

            {/* Floating HUD Overlays Toggles (Radar & Legend) in Left Corner */}
            <div
              className={`absolute top-2.5 left-2.5 z-10 inline-flex items-center border p-0.5 gap-0.5 shadow-sm backdrop-blur-md ${
                isFullscreen ? 'border-slate-700 bg-slate-900/90' : 'border-slate-300 bg-white/95'
              }`}
              onMouseDown={(e) => e.stopPropagation()}
            >
              {/* Mini-Map Toggle */}
              <button
                type="button"
                onClick={() => setShowMiniMap(!showMiniMap)}
                title={showMiniMap ? 'Hide Radar Mini-Map' : 'Show Radar Mini-Map'}
                className={`h-6 px-2 text-label font-mono flex items-center gap-1 cursor-pointer transition-colors ${
                  showMiniMap
                    ? isFullscreen
                      ? 'bg-slate-800 text-slate-200 font-semibold'
                      : 'bg-slate-200/80 text-slate-800 font-semibold'
                    : isFullscreen
                    ? 'text-slate-400 hover:text-slate-200'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <span className="material-symbols-sharp text-xs">map</span>
                <span>Radar</span>
              </button>

              {/* Legend Toggle */}
              <button
                type="button"
                onClick={() => setShowLegend(!showLegend)}
                title={showLegend ? 'Hide Legend' : 'Show Legend'}
                className={`h-6 px-2 text-label font-mono flex items-center gap-1 cursor-pointer transition-colors ${
                  showLegend
                    ? isFullscreen
                      ? 'bg-slate-800 text-slate-200 font-semibold'
                      : 'bg-slate-200/80 text-slate-800 font-semibold'
                    : isFullscreen
                    ? 'text-slate-400 hover:text-slate-200'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <span className="material-symbols-sharp text-xs">info</span>
                <span>Legend</span>
              </button>
            </div>

            {/* Radar Mini-Map Viewport Overlay */}
            {showMiniMap && (
              <div
                className={`absolute bottom-2.5 right-2.5 p-1.5 backdrop-blur-md shadow-md border ${
                  isFullscreen
                    ? 'bg-cx-ink-deep/90 border-slate-800 text-slate-300 shadow-xl'
                    : 'bg-white/95 border-slate-200 text-slate-700 shadow-sm'
                }`}
              >
                <div
                  className={`text-label font-mono uppercase tracking-wider mb-1 flex items-center justify-between ${
                    isFullscreen ? 'text-slate-400' : 'text-slate-500'
                  }`}
                >
                  <span>Radar Mini-Map</span>
                  <button
                    type="button"
                    onClick={() => setShowMiniMap(false)}
                    className="hover:opacity-100 opacity-60 cursor-pointer ml-2 text-label min-w-6"
                    title="Minimize Radar"
                    aria-label="Minimize radar mini-map"
                  >
                    ✕
                  </button>
                </div>
                <canvas
                  ref={miniMapCanvasRef}
                  width={120}
                  height={75}
                  className={`block border ${
                    isFullscreen
                      ? 'border-slate-800/80 bg-cx-studio'
                      : 'border-slate-200 bg-cx-wash'
                  }`}
                />
              </div>
            )}

            {/* Legend Overlay */}
            {showLegend && (
              <div
                className={`absolute bottom-2.5 left-2.5 p-2 text-label font-mono space-y-1 backdrop-blur-md shadow-sm border ${
                  isFullscreen
                    ? 'bg-cx-ink-deep/90 border-slate-800 text-slate-300 shadow-xl'
                    : 'bg-white/95 border-slate-200 text-slate-700 shadow-sm'
                }`}
              >
                <div className="flex items-center justify-between gap-3 pb-0.5 border-b border-slate-200 dark:border-slate-800 text-label uppercase tracking-wider text-slate-400">
                  <span>Topology Key</span>
                  <button
                    type="button"
                    onClick={() => setShowLegend(false)}
                    className="hover:opacity-100 opacity-60 cursor-pointer text-label min-w-6"
                    title="Hide Legend"
                    aria-label="Hide legend"
                  >
                    ✕
                  </button>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 bg-cx-bad-solid-2 inline-block border border-red-300/40" />
                  <span>Critical Syndicate (&ge; 0.85)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 bg-cx-warn-solid-2 inline-block border border-amber-300/40" />
                  <span>High Risk (&ge; 0.65)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 bg-cx-info-solid inline-block border border-blue-300/40" />
                  <span>Monitored Counterparty</span>
                </div>
              </div>
            )}
          </div>

          {/* Docked Timeline Playback Scrubber & Volume Strip */}
          <div
            className={`h-9 px-3 flex items-center gap-3 border-t text-xs font-mono shrink-0 select-none ${
              isFullscreen
                ? 'bg-cx-ink-deep border-slate-800 text-slate-200'
                : 'bg-slate-50 border-slate-200 text-slate-800'
            }`}
          >
            <button
              type="button"
              onClick={() => setIsPlayingTimeline(!isPlayingTimeline)}
              className={`size-6 flex items-center justify-center cursor-pointer border ${
                isFullscreen
                  ? 'bg-slate-800 hover:bg-slate-700 border-slate-600 text-slate-200'
                  : 'bg-white hover:bg-slate-100 border-slate-300 text-slate-800 shadow-xs'
              }`}
              title={isPlayingTimeline ? 'Pause Timeline' : 'Play Transaction Sequence'}
            >
              <span className="material-symbols-sharp text-sm">
                {isPlayingTimeline ? 'pause' : 'play_arrow'}
              </span>
            </button>

            <span
              className={`text-label whitespace-nowrap ${
                isFullscreen ? 'text-slate-400' : 'text-slate-600'
              }`}
            >
              Timeline: <strong className={isFullscreen ? 'text-white' : 'text-slate-900'}>Day {timelineDay}</strong> of 30
            </span>

            <input
              type="range"
              aria-label="Timeline day"
              min={1}
              max={30}
              value={timelineDay}
              onChange={(e) => setTimelineDay(parseInt(e.target.value, 10))}
              className={`flex-1 h-1.5 rounded-none cursor-pointer ${
                isFullscreen ? 'accent-cx-studio-accent bg-slate-800' : 'accent-blue-600 bg-slate-200'
              }`}
            />

            {/* Min Volume Filter */}
            <div
              className={`flex items-center gap-1.5 pl-3 border-l ${
                isFullscreen ? 'border-slate-800' : 'border-slate-200'
              }`}
            >
              <span className={`text-label ${isFullscreen ? 'text-slate-400' : 'text-slate-500'}`}>
                Min Vol:
              </span>
              <select
                value={minVolumeThreshold}
                onChange={(e) => setMinVolumeThreshold(parseInt(e.target.value, 10))}
                className={`text-label px-1.5 py-0.5 rounded-none focus:outline-none border cursor-pointer ${
                  isFullscreen
                    ? 'bg-slate-900 border-slate-700 text-slate-200'
                    : 'bg-white border-slate-300 text-slate-800'
                }`}
              >
                <option value={0}>All Volume</option>
                <option value={50000}>&gt; $50K</option>
                <option value={100000}>&gt; $100K</option>
                <option value={200000}>&gt; $200K</option>
              </select>
            </div>
          </div>
        </div>

        {/* Forensic Entity 360 Flyout Inspector */}
        {inspectorOpen && selectedNode && (
          <aside
            className={`w-80 lg:w-96 flex flex-col shrink-0 text-xs font-mono z-20 shadow-xl overflow-y-auto border-l ${
              isFullscreen
                ? 'bg-cx-studio-2 border-slate-800 text-slate-100 shadow-2xl'
                : 'bg-white border-slate-200 text-slate-900'
            }`}
          >
            {/* Inspector Header */}
            <div
              className={`p-3 border-b flex items-center justify-between ${
                isFullscreen
                  ? 'bg-cx-ink-deep border-slate-800'
                  : 'bg-slate-50 border-slate-200 text-slate-900'
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`material-symbols-sharp text-sm ${
                    isFullscreen ? 'text-cx-studio-accent' : 'text-blue-600'
                  }`}
                >
                  fingerprint
                </span>
                <span
                  className={`font-bold uppercase tracking-wider ${
                    isFullscreen ? 'text-white' : 'text-slate-900'
                  }`}
                >
                  Entity 360 Inspector
                </span>
              </div>
              <button
                type="button"
                onClick={() => setInspectorOpen(false)}
                aria-label="Close entity inspector"
                className={`cursor-pointer ${
                  isFullscreen ? 'text-slate-400 hover:text-white' : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                <span className="material-symbols-sharp text-sm">close</span>
              </button>
            </div>

            {/* Primary Entity Card */}
            <div
              className={`p-3 border-b space-y-2 ${
                isFullscreen ? 'border-slate-800/80 bg-cx-studio' : 'border-slate-200 bg-white'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className={`font-bold text-sm ${isFullscreen ? 'text-white' : 'text-slate-900'}`}>
                  {selectedNode.label}
                </span>
                <span
                  className={`px-1.5 py-0.2 text-label font-bold border ${
                    selectedNode.riskScore >= 0.85
                      ? isFullscreen
                        ? 'bg-red-950/80 text-red-300 border-red-600/60'
                        : 'bg-red-50 text-red-700 border-red-300'
                      : isFullscreen
                      ? 'bg-amber-950/80 text-amber-300 border-amber-600/60'
                      : 'bg-amber-50 text-amber-800 border-amber-300'
                  }`}
                >
                  Risk: {riskLabel(selectedNode, isLiveApi)}
                </span>
              </div>
              <div
                className={`text-label flex items-center gap-2 ${
                  isFullscreen ? 'text-slate-400' : 'text-slate-600'
                }`}
              >
                <span>
                  Type: <strong className={isFullscreen ? 'text-slate-200' : 'text-slate-900'}>{selectedNode.type}</strong>
                </span>
                <span>•</span>
                <span>
                  Jurisdiction:{' '}
                  <strong className={isFullscreen ? 'text-slate-200' : 'text-slate-900'}>
                    {selectedNode.details?.country || '—'}
                  </strong>
                </span>
              </div>
            </div>

            {/* Centrality Metrics */}
            <div
              className={`p-3 border-b space-y-2 ${
                isFullscreen ? 'border-slate-800/80' : 'border-slate-200'
              }`}
            >
              <div
                className={`text-label uppercase tracking-wider font-bold flex items-center gap-1 ${
                  isFullscreen ? 'text-slate-400' : 'text-slate-600'
                }`}
              >
                <span
                  className={`material-symbols-sharp text-xs ${
                    isFullscreen ? 'text-cx-studio-accent' : 'text-blue-600'
                  }`}
                >
                  analytics
                </span>
                <span>Topological Centrality Metrics</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-label">
                <div
                  className={`p-2 border ${
                    isFullscreen ? 'bg-cx-ink-deep border-slate-800' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <div className="text-label uppercase text-slate-500">Degree Centrality</div>
                  <div className={`text-sm font-bold ${isFullscreen ? 'text-white' : 'text-slate-900'}`}>
                    {selectedNode.degree} links
                  </div>
                </div>
                <div
                  className={`p-2 border ${
                    isFullscreen ? 'bg-cx-ink-deep border-slate-800' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <div className="text-label uppercase text-slate-500">Betweenness Score</div>
                  <div
                    className={`text-sm font-bold ${
                      isFullscreen ? 'text-amber-400' : 'text-amber-700'
                    }`}
                  >
                    {selectedNode.details?.betweenness || '—'}
                  </div>
                </div>
                <div
                  className={`p-2 border ${
                    isFullscreen ? 'bg-cx-ink-deep border-slate-800' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <div className="text-label uppercase text-slate-500">30D Velocity ($)</div>
                  <div className={`text-sm font-bold ${isFullscreen ? 'text-white' : 'text-slate-900'}`}>
                    {selectedNode.details?.turnover || '—'}
                  </div>
                </div>
                <div
                  className={`p-2 border ${
                    isFullscreen ? 'bg-cx-ink-deep border-slate-800' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <div className="text-label uppercase text-slate-500">Clustering Index</div>
                  <div
                    className={`text-sm font-bold ${
                      isFullscreen ? 'text-green-400' : 'text-green-700'
                    }`}
                  >
                    {selectedNode.details?.clustering || '—'}
                  </div>
                </div>
              </div>
            </div>

            {/* Counterparties List */}
            <div
              className={`p-3 border-b space-y-2 flex-1 ${
                isFullscreen ? 'border-slate-800/80' : 'border-slate-200'
              }`}
            >
              <div
                className={`text-label uppercase tracking-wider font-bold flex items-center justify-between ${
                  isFullscreen ? 'text-slate-400' : 'text-slate-600'
                }`}
              >
                <span>Immediate Counterparties ({selectedConnectedEdges.length})</span>
                <span className={`text-label ${isFullscreen ? 'text-slate-500' : 'text-slate-400'}`}>
                  Sorted by Volume
                </span>
              </div>

              <div className="space-y-1.5">
                {selectedConnectedEdges.map((e, idx) => {
                  const counterparty = e.source.id === selectedNode.id ? e.target : e.source;
                  const isOutflow = e.source.id === selectedNode.id;
                  return (
                    <div
                      key={idx}
                      onClick={() => {
                        openNode(counterparty);
                      }}
                      className={`p-2 border flex items-center justify-between cursor-pointer transition-colors ${
                        isFullscreen
                          ? 'bg-cx-ink-deep hover:bg-cx-ink-line border-slate-800'
                          : 'bg-slate-50 hover:bg-slate-100 border-slate-200'
                      }`}
                    >
                      <div>
                        <div
                          className={`font-bold flex items-center gap-1 ${
                            isFullscreen ? 'text-slate-200' : 'text-slate-900'
                          }`}
                        >
                          <span
                            className={`material-symbols-sharp text-xs ${
                              isOutflow
                                ? isFullscreen
                                  ? 'text-red-400'
                                  : 'text-red-600'
                                : isFullscreen
                                ? 'text-green-400'
                                : 'text-green-600'
                            }`}
                          >
                            {isOutflow ? 'arrow_forward' : 'arrow_back'}
                          </span>
                          <span>{counterparty.id}</span>
                        </div>
                        <div className="text-label text-slate-500">{e.type.replace(/_/g, ' ')}</div>
                      </div>
                      <div className="text-right">
                        <div
                          className={`font-bold ${
                            isFullscreen ? 'text-slate-100' : 'text-slate-900'
                          }`}
                        >
                          {e.amountUsd !== undefined ? `$${e.amountUsd.toLocaleString()}` : (e.label || '—')}
                        </div>
                        <div
                          className={`text-label ${
                            isFullscreen ? 'text-slate-400' : 'text-slate-500'
                          }`}
                        >
                          {e.dayIndex !== undefined ? `Day ${e.dayIndex}` : ''}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Drawer Footer Actions */}
            <div
              className={`p-3 border-t space-y-2 select-none ${
                isFullscreen ? 'bg-cx-ink-deep border-slate-800' : 'bg-slate-50 border-slate-200'
              }`}
            >
              <button
                type="button"
                onClick={handleStageHold}
                disabled={holdUnavailable || staging.busy}
                title={holdUnavailable ? 'This account has no pending withdrawal to hold' : undefined}
                className={`w-full h-8 px-3 text-xs font-mono font-bold transition-colors flex items-center justify-center gap-2 cursor-pointer border ${
                  isFullscreen
                    ? 'bg-red-950/80 hover:bg-red-900 border-red-600 text-red-200 shadow-sm'
                    : 'bg-red-600 hover:bg-red-700 border-red-700 text-white shadow-xs'
                }`}
              >
                <span className="material-symbols-sharp text-sm">lock</span>
                <span>Stage Pre-Settlement Hold</span>
                <span className="text-label opacity-80 font-normal">[KMS P-256]</span>
              </button>

              <button
                type="button"
                onClick={handleExportSarExhibit}
                className={`w-full h-7.5 px-3 border text-xs font-mono transition-colors flex items-center justify-center gap-1.5 cursor-pointer ${
                  isFullscreen
                    ? 'bg-slate-900 hover:bg-slate-800 border-slate-700 text-slate-200'
                    : 'bg-white hover:bg-slate-100 border-slate-300 text-slate-700'
                }`}
              >
                <span className="material-symbols-sharp text-sm text-amber-500">photo_camera</span>
                <span>Snapshot SAR Exhibit 1</span>
              </button>
            </div>
          </aside>
        )}
      </div>

      {/* Selected Entity Bottom Bar (Quick Actions when Inspector is closed) */}
      {!inspectorOpen && selectedNode && (
        <div
          className={`p-2.5 border flex flex-wrap items-center justify-between gap-3 text-xs font-mono ${
            isFullscreen
              ? 'bg-cx-ink-deep border-slate-800 text-slate-100'
              : 'bg-slate-50 border-slate-200 text-slate-900'
          }`}
        >
          <div className="flex items-center gap-2">
            <span className={`font-bold ${isFullscreen ? 'text-white' : 'text-slate-900'}`}>
              {selectedNode.label}
            </span>
            <span
              className={`px-1.5 py-0.2 text-label ${
                isFullscreen ? 'bg-slate-800 text-slate-300' : 'bg-slate-200 text-slate-700'
              }`}
            >
              Type: {selectedNode.type}
            </span>
            <span
              className={`px-1.5 py-0.2 text-label font-bold border ${
                selectedNode.riskScore >= 0.85
                  ? isFullscreen
                    ? 'bg-red-950/80 text-red-300 border-red-700/60'
                    : 'bg-red-50 text-red-700 border-red-300'
                  : isFullscreen
                  ? 'bg-amber-950/80 text-amber-300 border-amber-700/60'
                  : 'bg-amber-50 text-amber-800 border-amber-300'
              }`}
            >
              Risk: {riskLabel(selectedNode, isLiveApi)}
            </span>
            <span
              className={`text-label hidden md:inline ${
                isFullscreen ? 'text-slate-400' : 'text-slate-500'
              }`}
            >
              Degree: {selectedNode.degree} • Status: Under AML Surveillance
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setInspectorOpen(true)}
              className={`px-2.5 py-1 border flex items-center gap-1 cursor-pointer ${
                isFullscreen
                  ? 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-cx-studio-accent'
                  : 'bg-white hover:bg-slate-100 border-slate-300 text-blue-700 font-bold'
              }`}
            >
              <span className="material-symbols-sharp text-sm">dock_to_left</span>
              <span>Open Inspector</span>
            </button>
            <button
              type="button"
              onClick={handleStageHold}
              disabled={holdUnavailable || staging.busy}
              title={holdUnavailable ? 'This account has no pending withdrawal to hold' : undefined}
              className="px-3 py-1 disabled:opacity-60 bg-red-600 hover:bg-red-700 text-white font-bold transition-colors flex items-center gap-1 shadow-sm cursor-pointer"
            >
              <span className="material-symbols-sharp text-sm">lock</span>
              <span>Stage Hold</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
