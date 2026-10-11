import { useState, useEffect } from 'react';
import { 
  ReactFlow, 
  Controls, 
  Background, 
  useNodesState, 
  useEdgesState,
  type Node,
  type Edge
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { usePaperStore } from '@/store/paperStore';
import { apiClient } from '@/api/client';
import { Network, RefreshCw, Layers, Sparkles, Filter } from 'lucide-react';
import { GoogleLoader } from '@/components/ui/GoogleLoader';
import { useTheme } from '@/store/themeStore';
import { toast } from 'sonner';

export function KnowledgeGraph() {
  const selectedPaperIds = usePaperStore(state => state.selectedPaperIds);
  const papers = usePaperStore(state => state.papers);
  const theme = useTheme(state => state.theme);
  
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'all' | 'selected'>('all');
  const [stats, setStats] = useState<{ nodesCount: number; edgesCount: number }>({ nodesCount: 0, edgesCount: 0 });

  const fetchGraph = async () => {
    setLoading(true);
    setError(null);
    try {
      let endpoint = '/knowledge-graph/all';
      if (viewMode === 'selected' && selectedPaperIds.length > 0) {
        if (selectedPaperIds.length === 1) {
          endpoint = `/knowledge-graph/paper/${selectedPaperIds[0]}`;
        } else {
          endpoint = `/knowledge-graph/batch`;
        }
      }

      let response;
      if (viewMode === 'selected' && selectedPaperIds.length > 1) {
        response = await apiClient.post(endpoint, { paper_ids: selectedPaperIds });
      } else {
        response = await apiClient.get(endpoint);
      }

      const { nodes: backendNodes, edges: backendEdges } = response.data;
      
      if (!backendNodes || backendNodes.length === 0) {
        setNodes([]);
        setEdges([]);
        setStats({ nodesCount: 0, edgesCount: 0 });
        return;
      }

      setStats({ nodesCount: backendNodes.length, edgesCount: backendEdges ? backendEdges.length : 0 });

      // Identify all Paper nodes
      const paperNodeIds = new Set(
        backendNodes
          .filter((n: any) => n.labels?.includes('Paper') || n.id.startsWith('paper_'))
          .map((n: any) => n.id)
      );

      const paperNodesList = backendNodes.filter((n: any) => paperNodeIds.has(n.id));
      const entityNodesList = backendNodes.filter((n: any) => !paperNodeIds.has(n.id));

      // Coordinate placement with multi-center radial layout
      const rfNodes: Node[] = [];
      const numPapers = Math.max(paperNodesList.length, 1);
      const paperCenters = new Map<string, { x: number; y: number }>();

      paperNodesList.forEach((pn: any, pIdx: number) => {
        const centerAngle = (pIdx / numPapers) * 2 * Math.PI;
        const centerRadius = numPapers > 1 ? 400 + numPapers * 80 : 0;
        const cx = Math.cos(centerAngle) * centerRadius;
        const cy = Math.sin(centerAngle) * centerRadius;
        paperCenters.set(pn.id, { x: cx, y: cy });

        let title = pn.properties?.title || pn.id;
        if (title.length > 40) title = title.substring(0, 38) + '...';

        rfNodes.push({
          id: pn.id,
          position: { x: cx, y: cy },
          data: {
            label: (
              <div className="flex flex-col items-center text-center p-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-google-blue mb-1">
                  Research Paper
                </span>
                <span className="text-xs font-semibold leading-tight text-foreground line-clamp-2">
                  {title}
                </span>
                {pn.properties?.category && (
                  <span className="text-[9px] mt-1 text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                    {pn.properties.category}
                  </span>
                )}
              </div>
            )
          },
          style: {
            background: 'hsl(var(--card))',
            border: '2px solid hsl(var(--google-blue))',
            borderRadius: '16px',
            color: 'hsl(var(--foreground))',
            padding: '12px 16px',
            width: 220,
            boxShadow: '0 8px 30px rgba(74, 136, 247, 0.25)',
            zIndex: 10
          }
        });
      });

      // Distribute entity nodes in rings or around connected paper
      entityNodesList.forEach((en: any, eIdx: number) => {
        const label = en.labels?.[0] || 'Entity';
        let border = '1px solid hsl(var(--border))';
        let bg = 'hsl(var(--card))';
        let badgeColor = 'text-muted-foreground';

        if (label === 'Author') {
          border = '1px solid hsl(var(--google-green))';
          bg = 'hsl(var(--google-green)/0.08)';
          badgeColor = 'text-google-green';
        } else if (label === 'Methodology') {
          border = '1px solid hsl(var(--google-red))';
          bg = 'hsl(var(--google-red)/0.08)';
          badgeColor = 'text-google-red';
        } else if (label === 'Domain') {
          border = '1px solid hsl(var(--google-blue))';
          bg = 'hsl(var(--google-blue)/0.08)';
          badgeColor = 'text-google-blue';
        } else if (label === 'Concept') {
          border = '1px solid hsl(var(--google-yellow))';
          bg = 'hsl(var(--google-yellow)/0.08)';
          badgeColor = 'text-amber-500';
        } else if (label === 'Dataset') {
          border = '1px solid #ec4899';
          bg = 'rgba(236, 72, 153, 0.08)';
          badgeColor = 'text-pink-500';
        }

        // Circular offset around global center or connected paper
        const ring = Math.floor(eIdx / 16) + 1;
        const ringIdx = eIdx % 16;
        const angle = (ringIdx / 16) * 2 * Math.PI + (ring * 0.4);
        const radius = (numPapers > 1 ? 550 : 260) + ring * 160;

        const x = Math.cos(angle) * radius;
        const y = Math.sin(angle) * radius;

        let name = en.properties?.name || en.properties?.title || en.id.replace(/^[a-z]+_/, '');
        if (name.length > 30) name = name.substring(0, 28) + '..';

        rfNodes.push({
          id: en.id,
          position: { x, y },
          data: {
            label: (
              <div className="flex flex-col items-center text-center p-0.5">
                <span className={`text-[9px] font-bold uppercase tracking-wider ${badgeColor} mb-0.5`}>
                  {label}
                </span>
                <span className="text-xs font-medium leading-snug text-foreground">
                  {name}
                </span>
              </div>
            )
          },
          style: {
            background: bg,
            border: border,
            borderRadius: '12px',
            color: 'hsl(var(--foreground))',
            padding: '8px 12px',
            width: 160,
            boxShadow: '0 4px 14px rgba(0,0,0,0.06)',
            zIndex: 1
          }
        });
      });

      const rfEdges: Edge[] = (backendEdges || []).map((e: any) => ({
        id: `${e.source}-${e.target}-${e.type}`,
        source: e.source,
        target: e.target,
        label: e.type,
        animated: true,
        style: { stroke: 'hsl(var(--muted-foreground))', strokeWidth: 1.5, opacity: 0.6 },
        labelStyle: { fill: 'hsl(var(--foreground))', fontWeight: 600, fontSize: 9 },
        labelBgStyle: { fill: 'hsl(var(--background))', fillOpacity: 0.85, rx: 4, ry: 4 }
      }));

      setNodes(rfNodes);
      setEdges(rfEdges);
    } catch (e: any) {
      console.error('Failed to load knowledge graph', e);
      setError('Could not load knowledge tree. Ensure papers have been uploaded.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, [viewMode, selectedPaperIds.length]);

  return (
    <div className="flex flex-col h-full space-y-5 animate-fade-in pb-6">
      {/* Header with Title and Mode Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-display font-bold tracking-tight">Interconnected Knowledge Tree</h1>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              <Sparkles className="w-3 h-3" />
              Auto-Indexed
            </span>
          </div>
          <p className="text-muted-foreground text-sm mt-1">
            Always-visible semantic graph interconnecting all papers through methodologies, authors, domains, and concepts.
          </p>
        </div>

        <div className="flex items-center gap-3 self-start sm:self-auto flex-wrap">
          {/* Mode Switch: All Papers vs Selected */}
          <div className="flex items-center bg-muted/60 p-1 rounded-lg border border-border/70 text-xs font-medium">
            <button
              onClick={() => setViewMode('all')}
              className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 ${
                viewMode === 'all'
                  ? 'bg-background text-foreground shadow-sm font-semibold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              All Library Papers ({papers.length})
            </button>
            <button
              onClick={() => {
                if (selectedPaperIds.length === 0) {
                  toast.info('Please select papers in Library first to filter by selection.');
                }
                setViewMode('selected');
              }}
              className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 ${
                viewMode === 'selected'
                  ? 'bg-background text-foreground shadow-sm font-semibold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              Selected Only ({selectedPaperIds.length})
            </button>
          </div>

          <button
            onClick={fetchGraph}
            disabled={loading}
            className="p-2 rounded-lg border border-border bg-card/60 hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
            title="Refresh Knowledge Graph"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-primary' : ''}`} />
          </button>
        </div>
      </div>

      {/* Legend Bar */}
      <div className="flex items-center justify-between gap-4 px-4 py-2.5 bg-card/60 border border-border/70 rounded-xl text-xs backdrop-blur-sm overflow-x-auto">
        <div className="flex items-center gap-4 flex-wrap">
          <span className="font-semibold text-muted-foreground uppercase tracking-wider text-[11px]">
            Node Types:
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-google-blue ring-2 ring-google-blue/20" />
            <span className="text-foreground/90 font-medium">Research Paper</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-google-green ring-2 ring-google-green/20" />
            <span className="text-foreground/90 font-medium">Author (AUTHORED)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-google-red ring-2 ring-google-red/20" />
            <span className="text-foreground/90 font-medium">Methodology (USES_METHOD)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-500 ring-2 ring-cyan-500/20" />
            <span className="text-foreground/90 font-medium">Domain (IN_DOMAIN)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-google-yellow ring-2 ring-google-yellow/20" />
            <span className="text-foreground/90 font-medium">Concept (EXPLORES)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-pink-500 ring-2 ring-pink-500/20" />
            <span className="text-foreground/90 font-medium">Dataset (EVALUATED_ON)</span>
          </span>
        </div>

        <div className="text-[11px] text-muted-foreground shrink-0 font-medium">
          {stats.nodesCount} Entities &middot; {stats.edgesCount} Interconnections
        </div>
      </div>

      {/* Main Graph Viewport */}
      <div className="flex-1 min-h-[550px] rounded-2xl border border-border/80 bg-card/70 shadow-lg overflow-hidden relative">
        {loading ? (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground gap-3">
            <GoogleLoader size="lg" />
            <p className="text-sm font-medium">Traversing and rendering interconnected knowledge tree...</p>
          </div>
        ) : error ? (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground gap-3 p-8">
            <Network className="w-14 h-14 opacity-20 text-destructive" />
            <p className="text-sm font-semibold text-destructive text-center max-w-md">{error}</p>
            <button
              onClick={fetchGraph}
              className="px-4 py-2 text-xs font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Retry Graph Construction
            </button>
          </div>
        ) : nodes.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground p-8 text-center">
            <Network className="w-16 h-16 mb-4 opacity-20 text-primary" />
            <p className="text-base font-semibold text-foreground">No knowledge tree data available yet</p>
            <p className="text-xs text-muted-foreground max-w-sm mt-1">
              Upload papers in the Library. The knowledge graph will automatically extract authors, methodologies, domains, and concepts, interconnecting them in real time.
            </p>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            colorMode={theme}
            defaultEdgeOptions={{ animated: true }}
          >
            <Background gap={18} size={1} color="hsl(var(--muted-foreground))" className="opacity-15" />
            <Controls className="bg-card border-border fill-foreground shadow-md rounded-lg" />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
