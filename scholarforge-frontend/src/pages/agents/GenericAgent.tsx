import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { usePaperStore } from '@/store/paperStore';
import { apiClient } from '@/api/client';
import {
  BrainCircuit,
  Play,
  FileText,
  AlertCircle,
  RefreshCw,
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

  const selectedPaperIds = usePaperStore(
    (state) => state.selectedPaperIds
  );

  const papers = usePaperStore((state) => state.papers);

  const [loading, setLoading] = useState(false);
  const [loadingSavedResult, setLoadingSavedResult] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [hasLoadedSavedResult, setHasLoadedSavedResult] = useState(false);

  const loadingPhases = [
    'Analyzing papers...',
    'Extracting knowledge...',
    'Generating insights...',
    'Structuring output...',
  ];

  const [loadingPhase, setLoadingPhase] = useState(0);

  /*
   * --------------------------------------------------------------------------
   * Utility: normalize backend result
   * --------------------------------------------------------------------------
   *
   * The backend may return:
   *
   * 1. object
   * 2. JSON string
   * 3. markdown-wrapped JSON
   * 4. an object containing { result: ... }
   *
   * Normalize all of them before rendering.
   */
  const normalizeResult = (raw: any): any => {
    if (raw === null || raw === undefined) {
      return null;
    }

    // Backend sometimes returns { result: actualResult }
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

  /*
   * --------------------------------------------------------------------------
   * Utility: safely convert any value to displayable text
   * --------------------------------------------------------------------------
   */
  const valueToText = (value: any): string => {
    if (value === null || value === undefined) {
      return '';
    }

    if (typeof value === 'string') {
      return value;
    }

    if (typeof value === 'number' || typeof value === 'boolean') {
      return String(value);
    }

    if (Array.isArray(value)) {
      return value
        .map((item) => valueToText(item))
        .filter(Boolean)
        .join('\n');
    }

    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }

    return String(value);
  };

  /*
   * --------------------------------------------------------------------------
   * Loading phase animation
   * --------------------------------------------------------------------------
   */
  useEffect(() => {
    if (!loading) return;

    const interval = setInterval(() => {
      setLoadingPhase((p) => (p + 1) % loadingPhases.length);
    }, 2000);

    return () => clearInterval(interval);
  }, [loading]);

  /*
   * --------------------------------------------------------------------------
   * IMPORTANT:
   *
   * We NO LONGER do:
   *
   * setResult(null)
   *
   * whenever location.pathname changes.
   *
   * Instead, every time an agent page opens, we try to retrieve its
   * previously saved result from the backend.
   *
   * The backend GET endpoint will be added in the next step.
   * --------------------------------------------------------------------------
   */
  useEffect(() => {
    let cancelled = false;

    const loadSavedResult = async () => {
      if (!config || selectedPaperIds.length === 0) {
        setHasLoadedSavedResult(false);
        return;
      }

      setLoadingSavedResult(true);
      setHasLoadedSavedResult(false);

      try {
        /*
         * The backend GET endpoint will use:
         *
         * /agents/{endpoint}/result
         *
         * with the selected paper IDs as query parameters.
         *
         * Example:
         *
         * /agents/literature-review/result?paper_ids=id1&paper_ids=id2
         */
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
        } else {
          setResult(null);
        }

        setHasLoadedSavedResult(true);
      } catch (error: any) {
        if (cancelled) return;

        /*
         * 404 means:
         * There is simply no previously generated result.
         *
         * This is NOT an error that should be shown to the user.
         */
        const status = error?.response?.status;

        if (status === 404) {
          setResult(null);
          setHasLoadedSavedResult(true);
        } else {
          console.error(
            `Could not load saved ${config.title} result:`,
            error?.response?.data || error
          );

          setResult(null);
          setHasLoadedSavedResult(true);
        }
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
  }, [location.pathname, selectedPaperIds.join(','), config?.endpoint]);

  /*
   * --------------------------------------------------------------------------
   * Run agent
   * --------------------------------------------------------------------------
   */
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
      const response = await apiClient.post(
        `/agents/${config.endpoint}`,
        {
          paper_ids: selectedPaperIds,
          parameters: {},
        }
      );

      const generatedResult = normalizeResult(response.data);

      setResult(generatedResult);
      setHasLoadedSavedResult(true);

      toast.success(`${config.title} completed successfully.`);
    } catch (e: any) {
      const detail =
        e?.response?.data?.detail ||
        e?.message ||
        'Unknown error';

      toast.error(`Failed to run ${config.title}: ${detail}`);

      console.error(
        `Agent error [${config.endpoint}]:`,
        e?.response?.data || e
      );
    } finally {
      setLoading(false);
    }
  };

  /*
   * --------------------------------------------------------------------------
   * Render a generic value safely
   * --------------------------------------------------------------------------
   */
  const renderValue = (
    value: any,
    colorName: string
  ): React.ReactNode => {
    if (value === null || value === undefined) {
      return (
        <p className="text-sm text-muted-foreground">
          No data available.
        </p>
      );
    }

    /*
     * Array
     */
    if (Array.isArray(value)) {
      if (value.length === 0) {
        return (
          <p className="text-sm text-muted-foreground">
            No data available.
          </p>
        );
      }

      /*
       * Array of primitive values
       */
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
          <ul className="space-y-3">
            {value.map((item, index) => (
              <li key={index} className="flex gap-3 text-sm">
                <div
                  style={{
                    backgroundColor: `hsl(var(--${colorName}))`,
                  }}
                  className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0"
                />

                <span className="leading-relaxed text-card-foreground whitespace-pre-wrap">
                  {valueToText(item)}
                </span>
              </li>
            ))}
          </ul>
        );
      }

      /*
       * Array of objects
       */
      return (
        <div className="space-y-4">
          {value.map((item, index) => (
            <div
              key={index}
              className="bg-background border border-border rounded-lg p-4"
            >
              {typeof item === 'object' && item !== null ? (
                <div className="space-y-3">
                  {Object.entries(item).map(([key, nestedValue]) => (
                    <div key={key}>
                      <h5 className="font-medium text-sm mb-1 capitalize">
                        {key
                          .split('_')
                          .map(
                            (word) =>
                              word.charAt(0).toUpperCase() +
                              word.slice(1)
                          )
                          .join(' ')}
                      </h5>

                      <div className="text-sm text-muted-foreground whitespace-pre-wrap">
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

    /*
     * Object
     */
    if (typeof value === 'object') {
      return (
        <div className="space-y-3">
          {Object.entries(value).map(([key, nestedValue]) => (
            <div
              key={key}
              className="bg-background border border-border rounded-lg p-4"
            >
              <h5 className="font-medium text-sm mb-2 capitalize">
                {key
                  .split('_')
                  .map(
                    (word) =>
                      word.charAt(0).toUpperCase() +
                      word.slice(1)
                  )
                  .join(' ')}
              </h5>

              <div className="text-sm text-card-foreground">
                {renderValue(nestedValue, colorName)}
              </div>
            </div>
          ))}
        </div>
      );
    }

    /*
     * Primitive
     */
    return (
      <p className="text-sm leading-relaxed text-card-foreground whitespace-pre-wrap">
        {valueToText(value)}
      </p>
    );
  };

  /*
   * --------------------------------------------------------------------------
   * Render result
   * --------------------------------------------------------------------------
   */
  const renderResult = () => {
    if (result === null || result === undefined) {
      return null;
    }

    const parsedResult = normalizeResult(result);

    if (
      parsedResult === null ||
      parsedResult === undefined
    ) {
      return null;
    }

    /*
     * Special rendering for citations
     */
    if (location.pathname === '/agents/citations') {
      if (
        typeof parsedResult === 'object' &&
        !Array.isArray(parsedResult)
      ) {
        return (
          <div className="space-y-4">
            {Object.entries(parsedResult).map(
              ([style, text]) => (
                <div
                  key={style}
                  className="bg-background border border-border p-4 rounded-lg"
                >
                  <h4 className="font-semibold capitalize text-sm text-muted-foreground mb-2">
                    {style}
                  </h4>

                  <p className="font-mono text-sm whitespace-pre-wrap">
                    {valueToText(text)}
                  </p>
                </div>
              )
            )}
          </div>
        );
      }
    }

    /*
     * Special rendering for difficulty
     */
    if (location.pathname === '/agents/difficulty') {
      if (
        typeof parsedResult === 'object' &&
        !Array.isArray(parsedResult)
      ) {
        return (
          <div className="bg-background border border-border p-6 rounded-lg space-y-4">
            <div className="flex items-center gap-3">
              <span className="text-muted-foreground font-medium">
                Predicted Difficulty:
              </span>

              <span className="px-3 py-1 bg-primary/20 text-primary rounded-full font-bold uppercase tracking-wider text-sm">
                {valueToText(
                  (parsedResult as any).difficulty
                )}
              </span>
            </div>

            <div>
              <h4 className="font-semibold text-sm mb-2 text-muted-foreground">
                Rationale
              </h4>

              <p className="text-sm leading-relaxed whitespace-pre-wrap">
                {valueToText(
                  (parsedResult as any).rationale
                )}
              </p>
            </div>
          </div>
        );
      }
    }

    /*
     * Structured JSON object
     */
    if (
      typeof parsedResult === 'object' &&
      parsedResult !== null &&
      !Array.isArray(parsedResult)
    ) {
      const entries = Object.entries(parsedResult);

      if (entries.length > 0) {
        return (
          <div className="space-y-6 animate-fade-in max-w-4xl mx-auto">
            {entries.map(([key, value], index) => {
              const colors = [
                'google-blue',
                'google-green',
                'google-yellow',
                'google-red',
              ];

              const colorName =
                colors[index % colors.length];

              const title = key
                .split('_')
                .map(
                  (word) =>
                    word.charAt(0).toUpperCase() +
                    word.slice(1)
                )
                .join(' ');

              return (
                <div
                  key={key}
                  style={{
                    borderLeftColor: `hsl(var(--${colorName}))`,
                  }}
                  className="bg-card border-l-4 shadow-sm p-6 rounded-r-xl relative overflow-hidden"
                >
                  <h3
                    style={{
                      color: `hsl(var(--${colorName}))`,
                    }}
                    className="text-lg font-display font-semibold mb-4 flex items-center gap-2"
                  >
                    <BrainCircuit className="w-5 h-5" />
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

    /*
     * Array result
     */
    if (Array.isArray(parsedResult)) {
      return (
        <div className="max-w-4xl mx-auto">
          {renderValue(parsedResult, 'google-blue')}
        </div>
      );
    }

    /*
     * Plain string / markdown
     */
    const content =
      typeof parsedResult === 'string'
        ? parsedResult
        : valueToText(parsedResult);

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

  if (!config) {
    return <div>Agent not found</div>;
  }

  const selectedPapers = papers.filter((paper) =>
    selectedPaperIds.includes(paper.id)
  );

  const isInitialLoading =
    loadingSavedResult &&
    !result &&
    selectedPaperIds.length > 0;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-border/50 flex items-center justify-between bg-card/50">
        <div>
          <h1 className="text-2xl font-display font-bold flex items-center gap-3">
            {config.title}

            {(loading || loadingSavedResult) && (
              <GoogleLoader size="sm" />
            )}
          </h1>

          <p className="text-muted-foreground text-sm mt-1">
            {config.desc}
          </p>
        </div>

        <button
          onClick={handleRun}
          disabled={
            loading ||
            loadingSavedResult ||
            selectedPaperIds.length === 0
          }
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
      {selectedPaperIds.length === 0 &&
        !loading &&
        !result &&
        !loadingSavedResult && (
          <div className="m-6 p-4 bg-amber-500/10 border border-amber-500/20 text-amber-500 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />

            <p className="text-sm font-medium">
              You need to select papers from the Library before
              running this agent.
            </p>
          </div>
        )}

      {/* Loading saved result */}
      {isInitialLoading && (
        <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
          <RefreshCw className="w-8 h-8 mb-4 animate-spin" />

          <p className="text-lg font-medium text-foreground">
            Loading saved result...
          </p>

          <p className="text-sm mt-1">
            Checking for a previously generated {config.title}.
          </p>
        </div>
      )}

      {/* Selected Context */}
      {!isInitialLoading &&
        selectedPapers.length > 0 &&
        !loading &&
        !result && (
          <div className="p-6 border-b border-border/50">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
              Input Context ({selectedPapers.length} Papers)
            </h3>

            <div className="flex flex-wrap gap-2">
              {selectedPapers.map((paper) => (
                <div
                  key={paper.id}
                  className="flex items-center gap-2 bg-background border border-border px-3 py-1.5 rounded-md text-xs font-medium"
                >
                  <FileText className="w-3.5 h-3.5 text-primary" />

                  <span className="truncate max-w-[200px]">
                    {paper.title}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

      {/* Result Area */}
      {!isInitialLoading && (
        <div className="flex-1 overflow-y-auto p-6 bg-transparent">
          {loading ? (
            <div className="h-full flex flex-col items-center justify-center text-muted-foreground animate-fade-in">
              <GoogleLoader size="lg" className="mb-6" />

              <p className="text-xl font-display font-medium text-foreground mb-2">
                {loadingPhases[loadingPhase]}
              </p>

              <p className="text-sm opacity-70">
                Synthesizing information across{' '}
                {selectedPapers.length} papers...
              </p>
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
      )}
    </div>
  );
}