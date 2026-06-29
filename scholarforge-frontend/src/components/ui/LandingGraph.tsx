import React, { useEffect, useState } from 'react';

export function LandingGraph() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Neural network configuration
  const layers = [4, 6, 6, 3];
  const width = 400;
  const height = 300;
  
  const nodes: { id: string; cx: number; cy: number; layer: number; color: string }[] = [];
  const edges: { id: string; source: any; target: any; active: boolean }[] = [];
  
  const colors = [
    "hsl(var(--google-blue))",
    "hsl(var(--google-red))",
    "hsl(var(--google-yellow))",
    "hsl(var(--google-green))"
  ];

  let nodeId = 0;
  const layerXSpacing = width / (layers.length + 1);
  
  const nodesByLayer: any[][] = [];

  layers.forEach((nodeCount, layerIdx) => {
    const layerNodes = [];
    const layerYSpacing = height / (nodeCount + 1);
    const x = layerXSpacing * (layerIdx + 1);
    
    for (let i = 0; i < nodeCount; i++) {
      const y = layerYSpacing * (i + 1);
      const node = {
        id: `n${nodeId++}`,
        cx: x,
        cy: y,
        layer: layerIdx,
        color: colors[(layerIdx + i) % colors.length]
      };
      layerNodes.push(node);
      nodes.push(node);
    }
    nodesByLayer.push(layerNodes);
  });

  // Dense connections between adjacent layers
  let edgeId = 0;
  for (let l = 0; l < nodesByLayer.length - 1; l++) {
    const currentLayer = nodesByLayer[l];
    const nextLayer = nodesByLayer[l + 1];
    
    currentLayer.forEach(source => {
      nextLayer.forEach(target => {
        edges.push({
          id: `e${edgeId++}`,
          source,
          target,
          active: Math.random() > 0.6 // Randomly select active paths for data pulses
        });
      });
    });
  }

  if (!mounted) return null;

  return (
    <div className="relative w-full aspect-video max-w-2xl mx-auto flex items-center justify-center">
      <svg className="w-full h-full drop-shadow-[0_0_15px_rgba(66,133,244,0.3)]" viewBox={`0 0 ${width} ${height}`}>
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <filter id="glow-strong" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Base Edges */}
        {edges.map((edge) => (
          <path
            key={edge.id}
            d={`M ${edge.source.cx} ${edge.source.cy} L ${edge.target.cx} ${edge.target.cy}`}
            stroke="currentColor"
            strokeWidth="0.5"
            className="text-muted-foreground/10 dark:text-muted-foreground/20"
            fill="none"
          />
        ))}

        {/* Active Synaptic Pulses */}
        {edges.filter(e => e.active).map((edge, i) => (
          <path
            key={`pulse-${edge.id}`}
            d={`M ${edge.source.cx} ${edge.source.cy} L ${edge.target.cx} ${edge.target.cy}`}
            stroke={edge.source.color}
            strokeWidth="2"
            fill="none"
            filter="url(#glow)"
            strokeDasharray="40 200"
            className="opacity-60"
          >
            <animate
              attributeName="stroke-dashoffset"
              values="240;0"
              dur={`${1 + (i % 3) * 0.5}s`}
              repeatCount="indefinite"
              begin={`${(i % 5) * 0.2}s`}
            />
          </path>
        ))}

        {/* Neural Nodes */}
        {nodes.map((node, i) => (
          <g key={node.id}>
            {/* Outer Glow / Pulse */}
            <circle
              cx={node.cx}
              cy={node.cy}
              r={6}
              fill={node.color}
              className="opacity-20 mix-blend-screen"
            >
              <animate
                attributeName="r"
                values={`6;${8 + (i%3)};6`}
                dur={`${1.5 + (i % 2)}s`}
                repeatCount="indefinite"
              />
              <animate
                attributeName="opacity"
                values="0.2;0.5;0.2"
                dur={`${1.5 + (i % 2)}s`}
                repeatCount="indefinite"
              />
            </circle>
            {/* Core Node */}
            <circle
              cx={node.cx}
              cy={node.cy}
              r={4}
              fill={node.color}
              filter="url(#glow-strong)"
              className="transition-transform duration-300 hover:scale-150 origin-center cursor-crosshair"
            />
          </g>
        ))}
      </svg>
    </div>
  );
}
