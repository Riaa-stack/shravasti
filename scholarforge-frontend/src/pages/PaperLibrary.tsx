import { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { usePaperStore, type Paper } from '@/store/paperStore';
import { apiClient } from '@/api/client';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Clock, Trash2, Search as SearchIcon, CheckSquare, Square, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

export function PaperLibrary() {
  const { papers, setPapers, addPaper, selectedPaperIds, toggleSelection, selectAll, clearSelection } = usePaperStore();
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchPapers = async (searchTerm = '') => {
    setIsRefreshing(true);
    try {
      const url = searchTerm ? `/papers/?query=${encodeURIComponent(searchTerm)}` : '/papers/';
      const response = await apiClient.get(url);
      setPapers(response.data);
    } catch (e) {
      toast.error('Failed to load papers from library');
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchPapers();
  }, []);

  // Automatically poll every 3 seconds if any paper is still processing
  useEffect(() => {
    const hasPending = papers.some(p => p.status === 'processing' || p.status === 'uploaded');
    if (!hasPending) return;

    const interval = setInterval(() => {
      fetchPapers(search);
    }, 3000);

    return () => clearInterval(interval);
  }, [papers, search]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchPapers(search);
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (!acceptedFiles.length) return;
    
    setLoading(true);
    const formData = new FormData();
    acceptedFiles.forEach(file => {
      formData.append('files', file);
    });

    try {
      const response = await apiClient.post('/papers/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      // response.data is List[PaperResponse]
      if (Array.isArray(response.data)) {
        response.data.forEach((p: Paper) => addPaper(p));
      }
      toast.success(`Successfully uploaded and saved ${acceptedFiles.length} paper(s) to library`);
      // Refresh to get full saved metadata
      fetchPapers(search);
    } catch (error) {
      toast.error('Failed to upload papers');
    } finally {
      setLoading(false);
    }
  }, [addPaper, search]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop,
    accept: { 'application/pdf': ['.pdf'] }
  });

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await apiClient.delete(`/papers/${id}`);
      setPapers(papers.filter(p => p.id !== id));
      toast.success('Paper deleted from library');
    } catch (e) {
      toast.error('Failed to delete paper');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'processed': return <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
      case 'processing': return <Clock className="w-4 h-4 text-amber-500" />;
      case 'failed': return <AlertCircle className="w-4 h-4 text-destructive" />;
      default: return <FileText className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const formatAuthors = (authors?: string[] | string) => {
    if (!authors) return 'Unknown Authors';
    if (Array.isArray(authors)) return authors.join(', ');
    return String(authors);
  };

  const filteredPapers = papers.filter(p => {
    const q = search.toLowerCase();
    const titleMatch = (p.title || '').toLowerCase().includes(q);
    const fileMatch = (p.file_path || '').toLowerCase().includes(q);
    const authorStr = formatAuthors(p.authors).toLowerCase();
    const authorMatch = authorStr.includes(q);
    const categoryMatch = (p.category || '').toLowerCase().includes(q);
    return titleMatch || fileMatch || authorMatch || categoryMatch;
  });

  const allSelected = papers.length > 0 && selectedPaperIds.length === papers.length;

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight">Paper Library</h1>
          <p className="text-muted-foreground mt-1">
            Store, search, and select research papers for AI analysis. All papers are permanently stored.
          </p>
        </div>
        <button
          onClick={() => fetchPapers(search)}
          disabled={isRefreshing}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg border border-border bg-card/60 hover:bg-muted transition-colors disabled:opacity-50 self-start sm:self-auto"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh Library
        </button>
      </div>

      <div 
        {...getRootProps()} 
        className={`border-2 border-dashed rounded-xl p-10 text-center transition-all duration-300 cursor-pointer flex flex-col items-center justify-center gap-3 bg-card/40 backdrop-blur-sm
          ${isDragActive ? 'border-primary bg-primary/5 scale-[1.01]' : 'border-border hover:border-primary/50 hover:bg-muted/30'}`}
      >
        <input {...getInputProps()} />
        <div className={`p-3.5 rounded-full ${isDragActive ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'}`}>
          <UploadCloud className="w-8 h-8" />
        </div>
        <div>
          <p className="text-base font-medium">{isDragActive ? 'Drop PDF papers here...' : 'Drag & drop research papers here (PDF)'}</p>
          <p className="text-xs text-muted-foreground mt-1">Permanently saves papers into your library for future comparative and agent analysis</p>
        </div>
        {loading && <p className="text-sm text-primary font-medium animate-pulse">Uploading and indexing paper...</p>}
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input 
            type="text" 
            placeholder="Search papers by saved name, keyword, or author..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-background border border-border rounded-lg pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all placeholder:text-muted-foreground/70"
          />
        </form>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={allSelected ? clearSelection : selectAll}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-border bg-card/50 hover:bg-muted transition-colors text-foreground"
          >
            {allSelected ? <CheckSquare className="w-3.5 h-3.5 text-primary" /> : <Square className="w-3.5 h-3.5" />}
            {allSelected ? 'Deselect All' : 'Select All'}
          </button>

          {selectedPaperIds.length > 0 && (
            <button
              type="button"
              onClick={clearSelection}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Clear
            </button>
          )}

          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20">
            {selectedPaperIds.length} of {papers.length} selected for agents
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filteredPapers.map((paper) => {
          const isSelected = selectedPaperIds.includes(paper.id);
          const authorText = formatAuthors(paper.authors);

          return (
            <div 
              key={paper.id}
              onClick={() => toggleSelection(paper.id)}
              className={`relative rounded-xl border p-5 cursor-pointer transition-all duration-200 group bg-card/60 backdrop-blur-sm select-none
                ${isSelected 
                  ? 'border-primary ring-2 ring-primary/40 shadow-lg bg-primary/[0.03]' 
                  : 'border-border/50 hover:border-primary/50 hover:-translate-y-0.5'}`}
            >
              <div className="flex justify-between items-start mb-3 gap-2">
                <div className="flex items-center gap-2">
                  <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                    isSelected ? 'bg-primary border-primary text-primary-foreground' : 'border-border bg-background'
                  }`}>
                    {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-white" />}
                  </div>
                  <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-background/60 border border-border/50 text-[11px] font-medium">
                    {getStatusIcon(paper.status)}
                    <span className="capitalize">{paper.status}</span>
                  </div>
                </div>

                <button 
                  onClick={(e) => handleDelete(e, paper.id)}
                  title="Delete from library"
                  className="opacity-0 group-hover:opacity-100 p-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-md transition-all"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              <h3 className="font-semibold text-base leading-snug line-clamp-2 mb-2 group-hover:text-primary transition-colors">
                {paper.title || 'Untitled Research Paper'}
              </h3>
              
              <p className="text-xs text-muted-foreground line-clamp-1 mb-3">
                {authorText}
              </p>
              
              <div className="flex items-center justify-between pt-2 border-t border-border/40 text-[11px] text-muted-foreground">
                <span>{paper.category || 'General'}</span>
                {paper.difficulty_level && (
                  <span className="capitalize font-medium text-foreground/80 px-1.5 py-0.5 bg-muted rounded">
                    {paper.difficulty_level}
                  </span>
                )}
              </div>
            </div>
          );
        })}
        {filteredPapers.length === 0 && (
          <div className="col-span-full py-16 text-center text-muted-foreground border border-dashed rounded-xl bg-card/20">
            <FileText className="w-10 h-10 mx-auto text-muted-foreground/40 mb-3" />
            <p className="text-base font-medium">No research papers found</p>
            <p className="text-sm mt-1 text-muted-foreground">
              {search ? 'Try clearing your search query or uploading new papers.' : 'Drag & drop PDF files above to store papers in your library.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
