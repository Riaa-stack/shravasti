import { useState, useEffect, useCallback } from 'react';
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
import { Network } from 'lucide-react';
import { GoogleLoader } from '@/components/ui/GoogleLoader';
import { useTheme } from '@/store/themeStore';
import { toast } from 'sonner';

export function KnowledgeGraph() {
  const selectedPaperIds = usePaperStore(state => state.selectedPaperIds);
  const papers = usePaperStore(state => state.papers);
  const theme = useTheme(state => state.theme);
  
  const selectedPaper = selectedPaperIds.length > 0 ? papers.find(p => p.id === selectedPaperIds[0]) : null;
  const paperStatus = selectedPaper?.status;
  
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchGraph = async () => {
      if (selectedPaperIds.length === 0) {
        setNodes([]);
        setEdges([]);
        setError(null);
        return;
      }
      
      setLoading(true);
      setError(null);
      if (paperStatus && (paperStatus === 'processing' || paperStatus === 'uploaded')) {
        toast.info("Knowledge graph is still indexing for this paper.");
        setNodes([]);
        setEdges([]);
        setLoading(false);
        return;
      }
      
      try {
        const response = await apiClient.get(`/knowledge-graph/paper/${selectedPaperIds[0]}`);
        const { nodes: backendNodes, edges: backendEdges } = response.data;
        
        if (!backendNodes || backendNodes.length === 0) {
          toast.info("Knowledge graph is empty for this paper.");
          setNodes([]);
          setEdges([]);
          return;
        }

        const mainPaperId = `paper_${selectedPaperIds[0]}`;
        const mainNodeIndex = backendNodes.findIndex((n: any) => n.id === mainPaperId);

        const rfNodes: Node[] = backendNodes.map((n: any, idx: number) => {
          let x = 0, y = 0;
          
          if (n.id !== mainPaperId) {
             const otherIdx = idx > mainNodeIndex && mainNodeIndex !== -1 ? idx - 1 : idx;
             
             let ring = 1;
             let capacity = 12;
             let currentCapacitySum = capacity;
             let prevCapacitySum = 0;
             
             while (otherIdx >= currentCapacitySum) {
                 ring++;
                 prevCapacitySum = currentCapacitySum;
                 capacity = Math.floor(capacity * 1.8); 
                 currentCapacitySum += capacity;
             }
             
             const indexInRing = otherIdx - prevCapacitySum;
             const nodesInThisRing = Math.min(capacity, backendNodes.length - (mainNodeIndex !== -1 ? 1 : 0) - prevCapacitySum);
             
             const radius = ring * 300;
             const angle = (indexInRing / (nodesInThisRing || 1)) * 2 * Math.PI;
             
             x = Math.cos(angle) * radius;
             y = Math.sin(angle) * radius;
          }

          let title = n.properties?.title || n.properties?.name || n.id;
          if (title.length > 45) title = title.substring(0, 42) + '...';
          
          const isMainNode = n.id === mainPaperId;
          const isAuthor = n.labels?.includes('Author');
          const isKeyword = n.labels?.includes('Keyword');

          return {
            id: n.id,
            position: { x, y }, 
            data: { 
              label: (
                <div className="flex flex-col items-center text-center">
                  <div className="font-bold text-[10px] opacity-60 mb-1 uppercase tracking-wider">{n.labels?.[0] || 'Node'}</div>
                  <div className="text-sm font-medium leading-snug">{title}</div>
                </div>
              )
            },
            style: {
              background: isMainNode 
                ? 'hsl(var(--google-blue)/0.15)' 
                : isAuthor 
                  ? 'hsl(var(--google-green)/0.15)' 
                  : isKeyword
                  ? 'hsl(var(--google-yellow)/0.15)'
                  : 'hsl(var(--card))',
              border: isMainNode 
                ? '2px solid hsl(var(--google-blue))' 
                : '1px solid hsl(var(--border))',
              borderRadius: '12px',
              color: 'hsl(var(--foreground))',
              padding: '12px 16px',
              width: isMainNode ? 240 : 180,
              boxShadow: isMainNode ? '0 0 25px hsl(var(--google-blue)/0.2)' : '0 4px 12px rgba(0,0,0,0.05)',
              zIndex: isMainNode ? 10 : 1
            }
          };
        });

        const rfEdges: Edge[] = backendEdges.map((e: any) => ({
          id: `${e.source}-${e.target}`,
          source: e.source,
          target: e.target,
          label: e.type,
          animated: true,
          style: { stroke: 'hsl(var(--muted-foreground))', strokeWidth: 1.5, opacity: 0.5 },
          labelStyle: { fill: 'hsl(var(--foreground))', fontWeight: 500, fontSize: 10 },
          labelBgStyle: { fill: 'hsl(var(--background))', fillOpacity: 0.8 }
        }));

        setNodes(rfNodes);
        setEdges(rfEdges);
      } catch (e: any) {
        const detail = e?.response?.data?.detail || 'Failed to load graph from Neo4j.';
        console.error('Failed to load graph', e);
        toast.error(detail);
        setError(detail);
        setNodes([]);
        setEdges([]);
      } finally {
        setLoading(false);
      }
    };

    fetchGraph();
  }, [selectedPaperIds, paperStatus, setNodes, setEdges]);

  return (
    <div className="flex flex-col h-full space-y-6 animate-fade-in pb-8">
      <div>
        <h1 className="text-3xl font-display font-bold tracking-tight">Knowledge Graph</h1>
        <p className="text-muted-foreground mt-1">
          Visualizing connections for selected paper.
        </p>
      </div>

      <div className="flex-1 rounded-[2rem] border border-border bg-card shadow-[15px_15px_40px_rgba(0,0,0,0.05),-15px_-15px_40px_rgba(255,255,255,0.02),inset_3px_3px_10px_rgba(255,255,255,0.05),inset_-3px_-3px_10px_rgba(0,0,0,0.02)] overflow-hidden relative">
        {selectedPaperIds.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
            <Network className="w-16 h-16 mb-4 opacity-20" />
            <p>Select a paper from the Library to view its real graph.</p>
          </div>
        ) : loading ? (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
            <GoogleLoader size="lg" className="mb-4" />
            <p>Constructing graph...</p>
          </div>
        ) : error ? (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground gap-3 p-8">
            <Network className="w-16 h-16 opacity-20" />
            <p className="text-sm font-medium text-destructive text-center max-w-md">{error}</p>
            <p className="text-xs opacity-60 text-center">Ensure Neo4j is running and papers have finished processing.</p>
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
            <Background gap={16} size={1} color="hsl(var(--muted-foreground))" className="opacity-20" />
            <Controls className="bg-card border-border fill-foreground" />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
