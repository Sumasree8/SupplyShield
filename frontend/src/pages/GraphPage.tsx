import { useQuery } from '@tanstack/react-query';
import { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import { api } from '@/services/api';
import type { GraphNode, GraphData } from '@/types';
import { Network, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

const TIER_COLORS: Record<number, string> = {
  1: '#1a56db',
  2: '#7c3aed',
  3: '#0891b2',
  4: '#6b7280',
};

const NODE_RADIUS = 18;

interface SimNode extends GraphNode, d3.SimulationNodeDatum {}

interface SimEdge extends d3.SimulationLinkDatum<SimNode> {
  id: string;
  source: SimNode;
  target: SimNode;
  type: string;
  annual_volume_usd?: number;
  lead_time_days?: number;
}

export function GraphPage() {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);

  const { data: graphData, isLoading, error } = useQuery<GraphData>({
    queryKey: ['graph-visualization'],
    queryFn: () => api.getGraphVisualization(),
  });

  useEffect(() => {
    if (!graphData || !svgRef.current) return;
    const { nodes, edges } = graphData;
    if (nodes.length === 0) return;

    const el = svgRef.current;
    const width = el.clientWidth || 900;
    const height = el.clientHeight || 600;

    d3.select(el).selectAll('*').remove();

    const svg = d3.select(el)
      .attr('width', width)
      .attr('height', height);

    // Defs: arrowhead
    svg.append('defs').append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', NODE_RADIUS + 8)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#c8cfd9');

    const g = svg.append('g');

    // Zoom
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 4])
      .on('zoom', (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
        g.attr('transform', event.transform.toString());
      });
    svg.call(zoom);
    zoomRef.current = zoom;

    // Simulation
    const simNodes: SimNode[] = nodes.map(n => ({ ...n, x: width / 2, y: height / 2 }));
    const nodeMap = new Map(simNodes.map(n => [n.id, n]));

    const simEdges: SimEdge[] = edges
      .map(e => ({
        ...e,
        source: nodeMap.get(e.source) as SimNode,
        target: nodeMap.get(e.target) as SimNode,
      }))
      .filter((e): e is SimEdge => !!e.source && !!e.target);

    const sim = d3.forceSimulation<SimNode>(simNodes)
      .force('link', d3.forceLink<SimNode, SimEdge>(simEdges).id(d => d.id).distance(120).strength(0.5))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide(NODE_RADIUS + 12));

    // Edges
    const link = g.append('g')
      .selectAll('line')
      .data(simEdges)
      .join('line')
      .attr('stroke', '#e2e6ed')
      .attr('stroke-width', 1.5)
      .attr('marker-end', 'url(#arrow)');

    // Nodes
    const node = g.append('g')
      .selectAll<SVGGElement, SimNode>('g')
      .data(simNodes)
      .join('g')
      .style('cursor', 'pointer')
      .call(
        d3.drag<SVGGElement, SimNode>()
          .on('start', (event, d) => {
            if (!event.active) sim.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
          .on('end', (event, d) => {
            if (!event.active) sim.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      )
      .on('click', (_, d) => setSelectedNode(d));

    node.append('circle')
      .attr('r', NODE_RADIUS)
      .attr('fill', d => TIER_COLORS[d.tier] || '#6b7280')
      .attr('stroke', 'white')
      .attr('stroke-width', 2)
      .attr('opacity', 0.9);

    node.append('text')
      .attr('dy', '0.35em')
      .attr('text-anchor', 'middle')
      .attr('fill', 'white')
      .attr('font-size', 9)
      .attr('font-weight', '600')
      .attr('pointer-events', 'none')
      .text(d => `T${d.tier}`);

    node.append('text')
      .attr('dy', NODE_RADIUS + 14)
      .attr('text-anchor', 'middle')
      .attr('fill', '#4a5568')
      .attr('font-size', 10)
      .attr('pointer-events', 'none')
      .text(d => d.label.length > 20 ? d.label.slice(0, 18) + '…' : d.label);

    sim.on('tick', () => {
      link
        .attr('x1', d => d.source.x ?? 0)
        .attr('y1', d => d.source.y ?? 0)
        .attr('x2', d => d.target.x ?? 0)
        .attr('y2', d => d.target.y ?? 0);

      node.attr('transform', d => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    return () => { sim.stop(); };
  }, [graphData]);

  const handleZoom = (factor: number) => {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, factor);
  };

  const handleReset = () => {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current).transition().duration(400).call(zoomRef.current.transform, d3.zoomIdentity);
  };

  return (
    <div className="page" style={{ paddingBottom: 0 }}>
      <div className="page__header">
        <div>
          <h1 className="page__title">Supply Chain Graph</h1>
          <p className="page__subtitle">Interactive visualization of supplier dependencies and relationships</p>
        </div>
        {graphData && (
          <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
            <span className="text-muted text-sm">
              {graphData.stats.total_nodes} nodes · {graphData.stats.total_edges} edges
            </span>
          </div>
        )}
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 'var(--space-4)', marginBottom: 'var(--space-3)', alignItems: 'center', flexWrap: 'wrap' }}>
        {[1, 2, 3, 4].map(tier => (
          <div key={tier} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: TIER_COLORS[tier] }} />
            <span className="text-sm text-muted">Tier {tier}</span>
          </div>
        ))}
        <span className="text-muted text-sm" style={{ marginLeft: 'auto' }}>
          Drag nodes · Scroll to zoom · Click to inspect
        </span>
      </div>

      <div style={{ display: 'flex', gap: 'var(--space-4)', height: 'calc(100vh - 220px)' }}>
        {/* Graph */}
        <div className="graph-container" style={{ flex: 1, position: 'relative' }}>
          {isLoading && (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span className="loading-spinner" />
            </div>
          )}
          {error && (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <p className="text-muted">Failed to load graph. Check API connection.</p>
            </div>
          )}
          {graphData && graphData.nodes.length === 0 && (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
              <Network size={40} style={{ color: 'var(--color-border-strong)' }} />
              <p className="empty-state__title">No suppliers in graph</p>
              <p className="text-muted">Add suppliers and define their relationships to build the supply chain graph</p>
            </div>
          )}
          <svg ref={svgRef} style={{ width: '100%', height: '100%' }} />

          {/* Zoom controls */}
          <div style={{ position: 'absolute', bottom: 16, right: 16, display: 'flex', flexDirection: 'column', gap: 4 }}>
            <button className="btn btn--secondary btn--sm" onClick={() => handleZoom(1.3)} aria-label="Zoom in"><ZoomIn size={14} /></button>
            <button className="btn btn--secondary btn--sm" onClick={() => handleZoom(0.77)} aria-label="Zoom out"><ZoomOut size={14} /></button>
            <button className="btn btn--secondary btn--sm" onClick={handleReset} aria-label="Reset view"><RotateCcw size={14} /></button>
          </div>
        </div>

        {/* Inspector panel */}
        {selectedNode && (
          <div className="card" style={{ width: 260, flexShrink: 0, height: '100%', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 'var(--space-3)' }}>
              <p className="card__title">Node Inspector</p>
              <button className="btn btn--secondary btn--sm" onClick={() => setSelectedNode(null)}>✕</button>
            </div>
            <p style={{ fontWeight: 600, fontSize: 'var(--text-base)', marginBottom: 'var(--space-3)' }}>{selectedNode.label}</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <InspectorRow label="Tier" value={<span className={`badge badge--tier-${selectedNode.tier}`}>Tier {selectedNode.tier}</span>} />
              <InspectorRow label="Country" value={selectedNode.country} />
              <InspectorRow label="Status" value={<span className={`badge badge--${selectedNode.status}`}>{selectedNode.status}</span>} />
              {selectedNode.industry && <InspectorRow label="Industry" value={selectedNode.industry} />}
            </div>
            <div style={{ marginTop: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              <a href={`/suppliers/${selectedNode.id}`} className="btn btn--secondary btn--sm" style={{ justifyContent: 'center' }}>
                View Supplier
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function InspectorRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-sm)' }}>
      <span style={{ color: 'var(--color-text-muted)' }}>{label}</span>
      <span style={{ fontWeight: 500 }}>{value}</span>
    </div>
  );
}
