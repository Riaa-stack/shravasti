import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { usePaperStore } from '@/store/paperStore';
import { useAgentStore } from '@/store/agentStore';
import { apiClient } from '@/api/client';
import {
  BrainCircuit,
  Play,
  FileText,
  AlertCircle,
  RefreshCw,
  GitCompare,
  Sparkles,
  Layers,
  BookOpen,
  Gauge,
  Download
} from 'lucide-react';
import { GoogleLoader } from '@/components/ui/GoogleLoader';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeHighlight from 'rehype-highlight';
import { toast } from 'sonner';

const agentConfig: Record<
  string,
  {
    endpoint: string;
    title: string;
    desc: string;
  }
> = {
  '/agents/literature-review': {
    endpoint: 'literature-review',
    title: 'Literature Review',
    desc: 'Synthesize selected papers into a comprehensive review.',
  },
  '/agents/methodology': {
    endpoint: 'methodology',
    title: 'Methodology Analysis',
    desc: 'Extract and compare methodologies across papers.',
  },
  '/agents/research-gaps': {
    endpoint: 'research-gap',
    title: 'Research Gaps',
    desc: 'Identify limitations and unaddressed areas in the current literature.',
  },
  '/agents/trends': {
    endpoint: 'trend',
    title: 'Trend Analysis',
    desc: 'Discover temporal trends and shifts in research focus.',
  },
  '/agents/ideas': {
    endpoint: 'idea',
    title: 'Idea Generation',
    desc: 'Generate novel research proposals based on selected papers.',
  },
  '/agents/citations': {
    endpoint: 'citation',
    title: 'Citation Formatting',
    desc: 'Generate citations in multiple standard formats.',
  },
  '/agents/difficulty': {
    endpoint: 'difficulty',
    title: 'Difficulty Prediction',
    desc: 'Assess readability and technical difficulty of papers.',
  },
};

export function GenericAgent() {
  const location = useLocation();
  const config = agentConfig[location.pathname];
  const selectedPaperIds = usePaperStore((state) => state.selectedPaperIds);
  const papers = usePaperStore((state) => state.papers);

  const { setAgentResult, getAgentResult } = useAgentStore();

  const [loading, setLoading] = useState(false);
  const [loadingSavedResult, setLoadingSavedResult] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [_hasLoadedSavedResult, setHasLoadedSavedResult] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const loadingPhases = [
    'Analyzing papers...',
    'Extracting knowledge...',
    'Generating comparative insights...',
    'Structuring output...',
  ];

  const [loadingPhase, setLoadingPhase] = useState(0);

  const batchKey = [...selectedPaperIds].sort().join(',');

  const normalizeResult = (raw: any): any => {
    if (raw === null || raw === undefined) {
      return null;
    }
    if (
      typeof raw === 'object' &&
      !Array.isArray(raw) &&
      raw.result !== undefined
    ) {
      return normalizeResult(raw.result);
    }
    if (typeof raw === 'string') {
      const cleaned = raw
        .replace(/^```json\s*/i, '')
        .replace(/^```\s*/i, '')
        .replace(/\s*```$/i, '')
        .trim();
      try {
        return JSON.parse(cleaned);
      } catch {
        return raw;
      }
    }
    return raw;
  };

  const valueToText = (value: any): string => {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') return value;
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
    if (Array.isArray(value)) {
      return value.map((item) => valueToText(item)).filter(Boolean).join('\n');
    }
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  useEffect(() => {
    if (!loading) return;
    const interval = setInterval(() => {
      setLoadingPhase((p) => (p + 1) % loadingPhases.length);
    }, 2000);
    return () => clearInterval(interval);
  }, [loading]);

  useEffect(() => {
    let cancelled = false;

    const loadSavedResult = async () => {
      if (!config || selectedPaperIds.length === 0) {
        setResult(null);
        setHasLoadedSavedResult(false);
        return;
      }

      // 1. Check local session store first for ongoing session retention
      const cached = getAgentResult(config.endpoint, batchKey);
      if (cached !== null && cached !== undefined) {
        setResult(cached);
        setHasLoadedSavedResult(true);
        return;
      }

      // 2. Fetch from backend if not yet in local session cache
      setLoadingSavedResult(true);
      try {
        const params = new URLSearchParams();
        selectedPaperIds.forEach((id) => {
          params.append('paper_ids', id);
        });

        const response = await apiClient.get(
          `/agents/${config.endpoint}/result?${params.toString()}`
        );

        if (cancelled) return;

        const savedResult = normalizeResult(response.data);
        if (savedResult !== null && savedResult !== undefined) {
          setResult(savedResult);
          setAgentResult(config.endpoint, batchKey, savedResult);
        } else {
          setResult(null);
        }
        setHasLoadedSavedResult(true);
      } catch (error: any) {
        if (cancelled) return;
        setResult(null);
        setHasLoadedSavedResult(true);
      } finally {
        if (!cancelled) {
          setLoadingSavedResult(false);
        }
      }
    };

    loadSavedResult();

    return () => {
      cancelled = true;
    };
  }, [location.pathname, batchKey, config?.endpoint]);

  const handleRun = async () => {
    if (selectedPaperIds.length === 0) {
      toast.error('Please select at least one paper from the library first.');
      return;
    }
    if (!config) {
      toast.error('Agent configuration not found.');
      return;
    }

    setLoading(true);
    setLoadingPhase(0);

    try {
      const response = await apiClient.post(`/agents/${config.endpoint}`, {
        paper_ids: selectedPaperIds,
        parameters: {},
      });

      const generatedResult = normalizeResult(response.data);
      setResult(generatedResult);
      setHasLoadedSavedResult(true);

      // Save into ongoing session store so switching agent tabs will NEVER erase this response!
      setAgentResult(config.endpoint, batchKey, generatedResult);

      toast.success(`${config.title} generated successfully.`);
    } catch (e: any) {
      const detail =
        e?.response?.data?.detail || e?.message || 'Unknown error';
      toast.error(`Failed to run ${config.title}: ${detail}`);
    } finally {
      setLoading(false);
    }
  };

  const generateReportMarkdown = (parsedResult: any): string => {
    let md = `# ${config.title} - Research Report\n\n`;
    md += `Generated: ${new Date().toLocaleString()}\n`;
    md += `Selected Papers (${selectedPapers.length}): ${selectedPapers.map(p => p.title).join(', ')}\n\n`;
    md += `---\n\n`;

    if (parsedResult.comparative_analysis || parsedResult.comparative_review) {
      md += `## Comparative Analysis & Synthesis\n\n`;
      md += `${valueToText(parsedResult.comparative_analysis || parsedResult.comparative_review)}\n\n`;
    }

    const breakdowns =
      parsedResult.paper_reviews ||
      parsedResult.paper_analyses ||
      parsedResult.paper_gaps ||
      parsedResult.paper_citations ||
      parsedResult.paper_difficulties;

    if (Array.isArray(breakdowns) && breakdowns.length > 0) {
      md += `## Side-by-Side Paper Breakdowns\n\n`;
      breakdowns.forEach((item: any, idx: number) => {
        md += `### Paper ${idx + 1}: ${item.title || 'Untitled'}\n\n`;
        Object.entries(item).forEach(([k, v]) => {
          if (k !== 'paper_id' && k !== 'title') {
            md += `**${k.replace(/_/g, ' ').toUpperCase()}**:\n${valueToText(v)}\n\n`;
          }
        });
      });
    }

    Object.entries(parsedResult).forEach(([k, v]) => {
      if (
        ![
          'paper_reviews',
          'paper_analyses',
          'paper_gaps',
          'paper_citations',
          'paper_difficulties',
          'comparative_analysis',
          'comparative_review',
        ].includes(k)
      ) {
        md += `## ${k.replace(/_/g, ' ').toUpperCase()}\n\n`;
        md += `${valueToText(v)}\n\n`;
      }
    });

    return md;
  };

  const handleDownloadPdf = async () => {
    if (!result) {
      toast.error('No response generated to download.');
      return;
    }

    setDownloadingPdf(true);
    try {
      const parsed = normalizeResult(result);
      const reportMarkdown = generateReportMarkdown(parsed);

      let reportType = 'general';
      if (config.endpoint === 'literature-review') reportType = 'literature_review';
      else if (config.endpoint === 'methodology') reportType = 'methodology';
      else if (config.endpoint === 'research-gap') reportType = 'gap_analysis';
      else if (config.endpoint === 'trend') reportType = 'trend_report';
      else if (config.endpoint === 'citation') reportType = 'citation_report';
      else if (config.endpoint === 'idea') reportType = 'idea_generation';
      else if (config.endpoint === 'difficulty') reportType = 'difficulty_analysis';

      const response = await apiClient.post(
        '/export/report',
        {
          report_type: reportType,
          format: 'pdf',
          content: reportMarkdown,
        },
        { responseType: 'blob' }
      );

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${config.title.replace(/\s+/g, '_')}_Report.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success('PDF report downloaded successfully');
    } catch (e: any) {
      // Fallback printable formatted document window
      try {
        const parsed = normalizeResult(result);
        const reportText = generateReportMarkdown(parsed);
        const printWindow = window.open('', '_blank');
        if (printWindow) {
          printWindow.document.write(`
            <!DOCTYPE html>
            <html>
              <head>
                <title>${config.title} - ScholarForge Report</title>
                <style>
                  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 40px; color: #202124; line-height: 1.6; }
                  h1 { color: #1a73e8; border-bottom: 2px solid #e8eaed; padding-bottom: 8px; margin-bottom: 8px; }
                  .meta { color: #5f6368; font-size: 13px; margin-bottom: 24px; }
                  pre { background: #f8f9fa; border: 1px solid #dadce0; padding: 16px; border-radius: 8px; white-space: pre-wrap; font-family: inherit; font-size: 13px; }
                </style>
              </head>
              <body>
                <h1>ScholarForge AI - ${config.title}</h1>
                <div class="meta">Generated on ${new Date().toLocaleString()} &bull; ${selectedPapers.length} Selected Papers</div>
                <pre>${reportText.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
                <script>window.onload = function() { window.print(); };</script>
              </body>
            </html>
          `);
          printWindow.document.close();
          toast.success('Printable PDF window opened');
        } else {
          toast.error('Could not open print window.');
        }
      } catch (err) {
        toast.error('Failed to export PDF.');
      }
    } finally {
      setDownloadingPdf(false);
    }
  };

  const renderValue = (value: any, colorName: string): React.ReactNode => {
    if (value === null || value === undefined) {
      return <p className="text-sm text-muted-foreground">No data available.</p>;
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <p className="text-sm text-muted-foreground">No data available.</p>;
      }

      const allPrimitive = value.every(
        (item) =>
          item === null ||
          item === undefined ||
          typeof item === 'string' ||
          typeof item === 'number' ||
          typeof item === 'boolean'
      );

      if (allPrimitive) {
        return (
          <ul className="space-y-2.5">
            {value.map((item, index) => (
              <li key={index} className="flex gap-2.5 text-sm">
                <div
                  style={{ backgroundColor: `hsl(var(--${colorName}))` }}
                  className="w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0"
                />
                <span className="leading-relaxed text-card-foreground whitespace-pre-wrap">
                  {valueToText(item)}
                </span>
              </li>
            ))}
          </ul>
        );
      }

      return (
        <div className="space-y-3">
          {value.map((item, index) => (
            <div
              key={index}
              className="bg-background/80 border border-border/70 rounded-lg p-3.5 shadow-sm"
            >
              {typeof item === 'object' && item !== null ? (
                <div className="space-y-2">
                  {Object.entries(item).map(([key, nestedValue]) => (
                    <div key={key}>
                      <h5 className="font-semibold text-xs uppercase tracking-wider text-muted-foreground mb-1">
                        {key.replace(/_/g, ' ')}
                      </h5>
                      <div className="text-sm text-card-foreground">
                        {renderValue(nestedValue, colorName)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <span>{valueToText(item)}</span>
              )}
            </div>
          ))}
        </div>
      );
    }

    if (typeof value === 'object') {
      return (
        <div className="space-y-3">
          {Object.entries(value).map(([key, nestedValue]) => (
            <div
              key={key}
              className="bg-background/80 border border-border/70 rounded-lg p-4 shadow-sm"
            >
              <h5 className="font-semibold text-xs uppercase tracking-wider text-muted-foreground mb-1.5">
                {key.replace(/_/g, ' ')}
              </h5>
              <div className="text-sm text-card-foreground">
                {renderValue(nestedValue, colorName)}
              </div>
            </div>
          ))}
        </div>
      );
    }

    return (
      <p className="text-sm leading-relaxed text-card-foreground whitespace-pre-wrap">
        {valueToText(value)}
      </p>
    );
  };

  /*
   * Side-by-side multi-paper card renderer
   */
  const renderMultiPaperSection = (parsedResult: any) => {
    const paperItems: Array<{
      title: string;
      id?: string;
      data: any;
    }> = [];

    if (Array.isArray(parsedResult.paper_reviews) && parsedResult.paper_reviews.length > 0) {
      parsedResult.paper_reviews.forEach((item: any, idx: number) => {
        paperItems.push({
          title: item.title || `Paper #${idx + 1}`,
          id: item.paper_id,
          data: item
        });
      });
    } else if (Array.isArray(parsedResult.paper_analyses) && parsedResult.paper_analyses.length > 0) {
      parsedResult.paper_analyses.forEach((item: any, idx: number) => {
        paperItems.push({
          title: item.title || `Paper #${idx + 1}`,
          id: item.paper_id,
          data: item
        });
      });
    } else if (Array.isArray(parsedResult.paper_gaps) && parsedResult.paper_gaps.length > 0) {
      parsedResult.paper_gaps.forEach((item: any, idx: number) => {
        paperItems.push({
          title: item.title || `Paper #${idx + 1}`,
          id: item.paper_id,
          data: item
        });
      });
    } else if (Array.isArray(parsedResult.paper_citations) && parsedResult.paper_citations.length > 0) {
      parsedResult.paper_citations.forEach((item: any, idx: number) => {
        paperItems.push({
          title: item.title || `Paper #${idx + 1}`,
          id: item.paper_id,
          data: item
        });
      });
    } else if (Array.isArray(parsedResult.paper_difficulties) && parsedResult.paper_difficulties.length > 0) {
      parsedResult.paper_difficulties.forEach((item: any, idx: number) => {
        paperItems.push({
          title: item.title || `Paper #${idx + 1}`,
          id: item.paper_id,
          data: item
        });
      });
    }

    const comparativeContent =
      parsedResult.comparative_analysis ||
      parsedResult.comparative_review ||
      (selectedPaperIds.length > 1 ? parsedResult.summary : null);

    return (
      <div className="space-y-8 animate-fade-in max-w-7xl mx-auto">
        {/* Comparative Synthesis Card */}
        {comparativeContent && (
          <div className="relative rounded-2xl border-2 border-primary/30 bg-card/90 shadow-xl overflow-hidden p-6 md:p-8 backdrop-blur-md">
            <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-google-blue via-google-green to-google-red" />
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
                <GitCompare className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xl font-display font-bold text-foreground flex items-center gap-2">
                  Comparative Analysis & Synthesis
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-primary/15 text-primary font-semibold">
                    {selectedPaperIds.length} Papers Cross-Examined
                  </span>
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Direct side-by-side synthesis comparing methodological strengths, findings, and divergences.
                </p>
              </div>
            </div>
            <div className="prose prose-sm dark:prose-invert max-w-none text-foreground/90 leading-relaxed bg-background/50 rounded-xl p-5 border border-border/50">
              <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeHighlight]}>
                {valueToText(comparativeContent)}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {/* Side-by-side Grid of Papers */}
        {paperItems.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <Layers className="w-4 h-4 text-primary" />
                Side-by-Side Paper Breakdown ({paperItems.length} Papers)
              </h4>
              <span className="text-xs text-muted-foreground hidden sm:inline">
                Independent analysis per paper batch
              </span>
            </div>

            <div
              className={`grid grid-cols-1 ${
                paperItems.length === 2
                  ? 'md:grid-cols-2'
                  : paperItems.length >= 3
                  ? 'md:grid-cols-2 lg:grid-cols-3'
                  : ''
              } gap-6`}
            >
              {paperItems.map((paperItem, idx) => (
                <div
                  key={paperItem.id || idx}
                  className="rounded-xl border border-border/80 bg-card/70 backdrop-blur-sm shadow-md overflow-hidden flex flex-col transition-all hover:border-primary/50"
                >
                  <div className="p-4 border-b border-border/60 bg-muted/30 flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="w-6 h-6 rounded-full bg-primary/20 text-primary font-bold text-xs flex items-center justify-center shrink-0">
                        {idx + 1}
                      </span>
                      <h5 className="font-semibold text-sm leading-snug truncate" title={paperItem.title}>
                        {paperItem.title}
                      </h5>
                    </div>
                    <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-background border text-muted-foreground shrink-0 uppercase">
                      Paper {idx + 1}
                    </span>
                  </div>

                  <div className="p-5 space-y-4 flex-1 overflow-y-auto max-h-[600px]">
                    {Object.entries(paperItem.data).map(([key, val]) => {
                      if (key === 'paper_id' || key === 'title') return null;
                      return (
                        <div key={key} className="space-y-1.5">
                          <h6 className="font-semibold text-xs uppercase tracking-wider text-primary/90 flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                            {key.replace(/_/g, ' ')}
                          </h6>
                          <div className="text-xs text-card-foreground bg-background/60 p-3 rounded-lg border border-border/40 leading-relaxed whitespace-pre-wrap">
                            {renderValue(val, 'google-blue')}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Other top-level synthesis fields */}
        {Object.entries(parsedResult).map(([key, value]) => {
          if (
            [
              'paper_reviews',
              'paper_analyses',
              'paper_gaps',
              'paper_citations',
              'paper_difficulties',
              'comparative_analysis',
              'comparative_review',
            ].includes(key)
          ) {
            return null;
          }

          return (
            <div
              key={key}
              className="bg-card border-l-4 border-google-blue shadow-sm p-6 rounded-r-xl relative overflow-hidden"
            >
              <h3 className="text-base font-display font-semibold mb-3 flex items-center gap-2 text-foreground">
                <BrainCircuit className="w-4 h-4 text-google-blue" />
                {key.replace(/_/g, ' ').toUpperCase()}
              </h3>
              {renderValue(value, 'google-blue')}
            </div>
          );
        })}
      </div>
    );
  };

  const renderResult = () => {
    if (result === null || result === undefined) return null;
    const parsedResult = normalizeResult(result);
    if (parsedResult === null || parsedResult === undefined) return null;

    // Check if multi-paper side-by-side array is present
    const hasMultiPaperArray =
      (Array.isArray(parsedResult.paper_reviews) && parsedResult.paper_reviews.length > 0) ||
      (Array.isArray(parsedResult.paper_analyses) && parsedResult.paper_analyses.length > 0) ||
      (Array.isArray(parsedResult.paper_gaps) && parsedResult.paper_gaps.length > 0) ||
      (Array.isArray(parsedResult.paper_citations) && parsedResult.paper_citations.length > 0) ||
      (Array.isArray(parsedResult.paper_difficulties) && parsedResult.paper_difficulties.length > 0);

    if (hasMultiPaperArray || (selectedPaperIds.length > 1 && typeof parsedResult === 'object' && !Array.isArray(parsedResult))) {
      return renderMultiPaperSection(parsedResult);
    }

    // Citations special rendering for single paper
    if (location.pathname === '/agents/citations' && typeof parsedResult === 'object' && !Array.isArray(parsedResult)) {
      return (
        <div className="space-y-4 max-w-4xl mx-auto">
          {Object.entries(parsedResult).map(([style, text]) => {
            if (style === 'paper_citations') return null;
            return (
              <div key={style} className="bg-background border border-border p-4 rounded-lg shadow-sm">
                <h4 className="font-semibold capitalize text-sm text-primary mb-2 flex items-center gap-2">
                  <BookOpen className="w-4 h-4" />
                  {style}
                </h4>
                <p className="font-mono text-xs whitespace-pre-wrap leading-relaxed text-foreground/90 bg-muted/40 p-3 rounded border">
                  {valueToText(text)}
                </p>
              </div>
            );
          })}
        </div>
      );
    }

    // Difficulty special rendering for single paper
    if (location.pathname === '/agents/difficulty' && typeof parsedResult === 'object' && !Array.isArray(parsedResult)) {
      return (
        <div className="bg-card border border-border p-6 rounded-xl space-y-5 max-w-3xl mx-auto shadow-md">
          <div className="flex items-center justify-between border-b pb-4">
            <span className="text-muted-foreground font-medium flex items-center gap-2">
              <Gauge className="w-5 h-5 text-primary" />
              Predicted Difficulty Level:
            </span>
            <span className="px-3.5 py-1 bg-primary/20 text-primary border border-primary/30 rounded-full font-bold uppercase tracking-wider text-xs">
              {valueToText((parsedResult as any).difficulty || (parsedResult as any).technical_depth || 'Moderate')}
            </span>
          </div>
          <div>
            <h4 className="font-semibold text-sm mb-2 text-foreground">Detailed Rationale & Metrics</h4>
            <div className="text-sm leading-relaxed text-muted-foreground whitespace-pre-wrap bg-background/60 p-4 rounded-lg border">
              {valueToText((parsedResult as any).rationale || (parsedResult as any).comparative_analysis || parsedResult)}
            </div>
          </div>
        </div>
      );
    }

    // Generic Structured Object
    if (typeof parsedResult === 'object' && parsedResult !== null && !Array.isArray(parsedResult)) {
      const entries = Object.entries(parsedResult);
      if (entries.length > 0) {
        return (
          <div className="space-y-6 animate-fade-in max-w-4xl mx-auto">
            {entries.map(([key, value], index) => {
              const colors = ['google-blue', 'google-green', 'google-yellow', 'google-red'];
              const colorName = colors[index % colors.length];
              const title = key.replace(/_/g, ' ').toUpperCase();

              return (
                <div
                  key={key}
                  style={{ borderLeftColor: `hsl(var(--${colorName}))` }}
                  className="bg-card border-l-4 shadow-sm p-6 rounded-r-xl relative overflow-hidden"
                >
                  <h3
                    style={{ color: `hsl(var(--${colorName}))` }}
                    className="text-base font-display font-semibold mb-3 flex items-center gap-2"
                  >
                    <BrainCircuit className="w-4 h-4" />
                    {title}
                  </h3>
                  {renderValue(value, colorName)}
                </div>
              );
            })}
          </div>
        );
      }
    }

    // Array result
    if (Array.isArray(parsedResult)) {
      return (
        <div className="max-w-4xl mx-auto">
          {renderValue(parsedResult, 'google-blue')}
        </div>
      );
    }

    // Plain text / Markdown
    const content = typeof parsedResult === 'string' ? parsedResult : valueToText(parsedResult);
    return (
      <div className="prose prose-sm dark:prose-invert max-w-4xl mx-auto bg-card p-6 rounded-xl border border-border shadow-sm">
        <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeHighlight]}>
          {content}
        </ReactMarkdown>
      </div>
    );
  };

  if (!config) {
    return <div>Agent not found</div>;
  }

  const selectedPapers = papers.filter((paper) =>
    selectedPaperIds.includes(paper.id)
  );

  const isInitialLoading =
    loadingSavedResult && !result && selectedPaperIds.length > 0;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-border/50 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-card/50">
        <div>
          <h1 className="text-2xl font-display font-bold flex items-center gap-3">
            {config.title}
            {(loading || loadingSavedResult) && <GoogleLoader size="sm" />}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">{config.desc}</p>
        </div>

        <div className="flex items-center gap-3 self-start sm:self-auto flex-wrap">
          {result && (
            <button
              onClick={handleDownloadPdf}
              disabled={downloadingPdf}
              className="flex items-center justify-center gap-2 bg-card hover:bg-muted border border-border px-4 py-2.5 rounded-lg text-sm font-semibold transition-all hover:scale-[1.02] shadow-sm text-foreground disabled:opacity-50 cursor-pointer"
              title="Download generated response as PDF"
            >
              {downloadingPdf ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-primary" />
                  Generating PDF...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4 text-primary" />
                  Download PDF
                </>
              )}
            </button>
          )}

          <button
            onClick={handleRun}
            disabled={loading || selectedPaperIds.length === 0}
            className="flex items-center justify-center gap-2 bg-google-blue hover:bg-google-blue/90 text-white px-6 py-2.5 rounded-lg font-medium transition-all disabled:opacity-50 disabled:hover:scale-100 hover:scale-[1.02] shadow-lg shadow-google-blue/20"
          >
            {loading ? (
              <>
                <BrainCircuit className="w-4 h-4 animate-pulse" />
                Processing Papers...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Agent on {selectedPaperIds.length > 1 ? `${selectedPaperIds.length} Papers` : 'Paper'}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Warning when 0 papers selected */}
      {selectedPaperIds.length === 0 && !loading && !result && !loadingSavedResult && (
        <div className="m-6 p-4 bg-amber-500/10 border border-amber-500/20 text-amber-500 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p className="text-sm font-medium">
            Please select one or more research papers from the <strong>Library</strong> before running this agent.
          </p>
        </div>
      )}

      {/* Selected Papers Context Bar */}
      {selectedPapers.length > 0 && (
        <div className="px-6 py-3 border-b border-border/50 bg-muted/20 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mr-2">
              Context ({selectedPapers.length} Selected):
            </span>
            {selectedPapers.map((paper) => (
              <div
                key={paper.id}
                className="flex items-center gap-1.5 bg-background border border-border px-2.5 py-1 rounded-md text-xs font-medium text-foreground"
              >
                <FileText className="w-3 h-3 text-primary" />
                <span className="truncate max-w-[180px]">{paper.title}</span>
              </div>
            ))}
          </div>

          {result && (
            <div className="flex items-center gap-2.5">
              <button
                onClick={handleDownloadPdf}
                disabled={downloadingPdf}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/25 hover:bg-primary/20 transition-all cursor-pointer"
                title="Download PDF Report"
              >
                <Download className="w-3.5 h-3.5" />
                Download PDF
              </button>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <Sparkles className="w-3 h-3" />
                Session Output Preserved
              </span>
            </div>
          )}
        </div>
      )}

      {/* Initial Loading */}
      {isInitialLoading && (
        <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground py-16">
          <RefreshCw className="w-8 h-8 mb-4 animate-spin text-primary" />
          <p className="text-base font-medium text-foreground">Checking saved session results...</p>
          <p className="text-xs mt-1 text-muted-foreground">Retrieving analysis for the selected batch of papers.</p>
        </div>
      )}

      {/* Result Area */}
      {!isInitialLoading && (
        <div className="flex-1 overflow-y-auto p-6 bg-transparent">
          {loading ? (
            <div className="h-full flex flex-col items-center justify-center text-muted-foreground py-16 animate-fade-in">
              <GoogleLoader size="lg" className="mb-6" />
              <p className="text-xl font-display font-medium text-foreground mb-2">
                {loadingPhases[loadingPhase]}
              </p>
              <p className="text-sm opacity-70">
                Synthesizing and analyzing {selectedPapers.length} selected paper(s)...
              </p>
            </div>
          ) : result ? (
            <div className="animate-slide-up pb-8">{renderResult()}</div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-muted-foreground/50 py-20">
              <BrainCircuit className="w-16 h-16 mb-4 opacity-20" />
              <p className="text-base font-medium text-foreground/60">Ready to analyze</p>
              <p className="text-xs text-muted-foreground mt-1">
                Click "Run Agent" above to generate insights for your selected paper(s).
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}