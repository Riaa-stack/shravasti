import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { usePaperStore } from '@/store/paperStore';
import { apiClient } from '@/api/client';
import { BrainCircuit, Loader2, Play, FileText, AlertCircle } from 'lucide-react';
import { GoogleLoader } from '@/components/ui/GoogleLoader';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeHighlight from 'rehype-highlight';
import { toast } from 'sonner';

const agentConfig: Record<string, { endpoint: string, title: string, desc: string }> = {
  '/agents/literature-review': { endpoint: 'literature-review', title: 'Literature Review', desc: 'Synthesize selected papers into a comprehensive review.' },
  '/agents/methodology': { endpoint: 'methodology', title: 'Methodology Analysis', desc: 'Extract and compare methodologies across papers.' },
  '/agents/research-gaps': { endpoint: 'research-gap', title: 'Research Gaps', desc: 'Identify limitations and unaddressed areas in the current literature.' },
  '/agents/trends': { endpoint: 'trend', title: 'Trend Analysis', desc: 'Discover temporal trends and shifts in research focus.' },
  '/agents/ideas': { endpoint: 'idea', title: 'Idea Generation', desc: 'Generate novel research proposals based on selected papers.' },
  '/agents/citations': { endpoint: 'citation', title: 'Citation Formatting', desc: 'Generate citations in multiple standard formats.' },
  '/agents/difficulty': { endpoint: 'difficulty', title: 'Difficulty Prediction', desc: 'Assess readability and technical difficulty of papers.' },
};

export function GenericAgent() {
  const location = useLocation();
  const config = agentConfig[location.pathname];
  
  const selectedPaperIds = usePaperStore(state => state.selectedPaperIds);
  const papers = usePaperStore(state => state.papers);
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const loadingPhases = [
    "Analyzing papers...",
    "Extracting knowledge...",
    "Generating insights...",
    "Structuring output...",
  ];
  const [loadingPhase, setLoadingPhase] = useState(0);

  useEffect(() => {
    if (!loading) return;
    const interval = setInterval(() => {
      setLoadingPhase(p => (p + 1) % loadingPhases.length);
    }, 2000);
    return () => clearInterval(interval);
  }, [loading]);

  // Reset result on route change
  useEffect(() => {
    setResult(null);
  }, [location.pathname]);

  if (!config) return <div>Agent not found</div>;

  const selectedPapers = papers.filter(p => selectedPaperIds.includes(p.id));

  const handleRun = async () => {
    if (selectedPaperIds.length === 0) {
      toast.error('Please select at least one paper from the library first.');
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      const response = await apiClient.post(`/agents/${config.endpoint}`, {
        paper_ids: selectedPaperIds,
        parameters: {}
      });
      setResult(response.data.result);
      toast.success(`${config.title} completed successfully.`);
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || 'Unknown error';
      toast.error(`Failed to run ${config.title}: ${detail}`);
      console.error(`Agent error [${config.endpoint}]:`, e?.response?.data || e);
    } finally {
      setLoading(false);
    }
  };

  const renderResult = () => {
    if (!result) return null;

    // Special rendering for citations
    if (location.pathname === '/agents/citations') {
      return (
        <div className="space-y-4">
          {Object.entries(result).map(([style, text]) => (
            <div key={style} className="bg-background border border-border p-4 rounded-lg">
              <h4 className="font-semibold capitalize text-sm text-muted-foreground mb-2">{style}</h4>
              <p className="font-mono text-sm">{String(text)}</p>
            </div>
          ))}
        </div>
      );
    }

    // Special rendering for difficulty
    if (location.pathname === '/agents/difficulty') {
      return (
        <div className="bg-background border border-border p-6 rounded-lg space-y-4">
          <div className="flex items-center gap-3">
            <span className="text-muted-foreground font-medium">Predicted Difficulty:</span>
            <span className="px-3 py-1 bg-primary/20 text-primary rounded-full font-bold uppercase tracking-wider text-sm">
              {result.difficulty}
            </span>
          </div>
          <div>
            <h4 className="font-semibold text-sm mb-2 text-muted-foreground">Rationale</h4>
            <p className="text-sm leading-relaxed">{result.rationale}</p>
          </div>
        </div>
      );
    }

    // Attempt to parse JSON for structured rendering
    let parsedJson = null;
    if (typeof result === 'string') {
      try {
        const cleanJsonStr = result.replace(/```json\n?|\n?```/g, '').trim();
        parsedJson = JSON.parse(cleanJsonStr);
      } catch (e) {
        // Not valid JSON string
      }
    } else if (typeof result === 'object' && result !== null) {
      parsedJson = result;
    }

    if (parsedJson && Object.keys(parsedJson).length > 0) {
      return (
        <div className="space-y-6 animate-fade-in max-w-4xl mx-auto">
          {Object.entries(parsedJson).map(([key, value], index) => {
            const colors = ['google-blue', 'google-green', 'google-yellow', 'google-red'];
            const colorName = colors[index % colors.length];
            const title = key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');

            return (
              <div key={key} style={{ borderLeftColor: `hsl(var(--${colorName}))` }} className={`bg-card border-l-4 shadow-sm p-6 rounded-r-xl relative overflow-hidden`}>
                <h3 style={{ color: `hsl(var(--${colorName}))` }} className="text-lg font-display font-semibold mb-4 flex items-center gap-2">
                  <BrainCircuit className="w-5 h-5" /> {title}
                </h3>
                {Array.isArray(value) ? (
                  <ul className="space-y-3">
                    {value.map((item: any, i: number) => (
                      <li key={i} className="flex gap-3 text-sm">
                        <div style={{ backgroundColor: `hsl(var(--${colorName}))` }} className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0" />
                        <span className="leading-relaxed text-card-foreground">{String(item)}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm leading-relaxed text-card-foreground">{String(value)}</p>
                )}
              </div>
            );
          })}
        </div>
      );
    }

    // Default markdown rendering for non-JSON
    const content = typeof result === 'string' ? result : result.content || result.report || JSON.stringify(result, null, 2);
    
    return (
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown 
          remarkPlugins={[remarkMath]}
          rehypePlugins={[rehypeHighlight]}
        >
          {content}
        </ReactMarkdown>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-border/50 flex items-center justify-between bg-card/50">
        <div>
          <h1 className="text-2xl font-display font-bold flex items-center gap-3">
            {config.title}
            {loading && <GoogleLoader size="sm" />}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">{config.desc}</p>
        </div>
        <button
          onClick={handleRun}
          disabled={loading || selectedPaperIds.length === 0}
          className="flex items-center gap-2 bg-google-blue hover:bg-google-blue/90 text-white px-6 py-2.5 rounded-lg font-medium transition-all disabled:opacity-50 disabled:hover:scale-100 hover:scale-[1.02] shadow-lg shadow-google-blue/20"
        >
          {loading ? (
            <>
              <BrainCircuit className="w-4 h-4 animate-pulse" />
              Processing...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Run Agent
            </>
          )}
        </button>
      </div>

      {/* Context Selection Warning */}
      {selectedPaperIds.length === 0 && !loading && !result && (
        <div className="m-6 p-4 bg-amber-500/10 border border-amber-500/20 text-amber-500 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p className="text-sm font-medium">You need to select papers from the Library before running this agent.</p>
        </div>
      )}

      {/* Selected Context */}
      {selectedPapers.length > 0 && !loading && !result && (
        <div className="p-6 border-b border-border/50">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Input Context ({selectedPapers.length} Papers)
          </h3>
          <div className="flex flex-wrap gap-2">
            {selectedPapers.map(p => (
              <div key={p.id} className="flex items-center gap-2 bg-background border border-border px-3 py-1.5 rounded-md text-xs font-medium">
                <FileText className="w-3.5 h-3.5 text-primary" />
                <span className="truncate max-w-[200px]">{p.title}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Result Area */}
      <div className="flex-1 overflow-y-auto p-6 bg-transparent">
        {loading ? (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground animate-fade-in">
            <GoogleLoader size="lg" className="mb-6" />
            <p className="text-xl font-display font-medium text-foreground mb-2">
              {loadingPhases[loadingPhase]}
            </p>
            <p className="text-sm opacity-70">Synthesizing information across {selectedPapers.length} papers...</p>
          </div>
        ) : result ? (
          <div className="animate-slide-up">
            {renderResult()}
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground/50">
            <BrainCircuit className="w-16 h-16 mb-4 opacity-20" />
            <p>Ready to analyze.</p>
          </div>
        )}
      </div>
    </div>
  );
}
