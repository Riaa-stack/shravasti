import { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { usePaperStore, type Paper } from '@/store/paperStore';
import { apiClient } from '@/api/client';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Clock, Trash2, Search as SearchIcon } from 'lucide-react';
import { toast } from 'sonner';

export function PaperLibrary() {
  const { papers, setPapers, addPaper, selectedPaperIds, toggleSelection } = usePaperStore();
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

  const fetchPapers = async () => {
    try {
      const response = await apiClient.get('/papers/');
      setPapers(response.data);
    } catch (e) {
      toast.error('Failed to load papers');
    }
  };

  useEffect(() => {
    fetchPapers();
  }, []);

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
      response.data.forEach((p: Paper) => addPaper(p));
      toast.success(`Successfully uploaded ${acceptedFiles.length} papers`);
    } catch (error) {
      toast.error('Failed to upload papers');
    } finally {
      setLoading(false);
    }
  }, [addPaper]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop,
    accept: { 'application/pdf': ['.pdf'] }
  });

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await apiClient.delete(`/papers/${id}`);
      setPapers(papers.filter(p => p.id !== id));
      toast.success('Paper deleted');
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

  const filteredPapers = papers.filter(p => 
    p.title?.toLowerCase().includes(search.toLowerCase()) || 
    p.authors?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      <div>
        <h1 className="text-3xl font-display font-bold tracking-tight">Paper Library</h1>
        <p className="text-muted-foreground mt-1">Manage and upload your research papers.</p>
      </div>

      <div 
        {...getRootProps()} 
        className={`border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300 cursor-pointer flex flex-col items-center justify-center gap-4 bg-card/40 backdrop-blur-sm
          ${isDragActive ? 'border-primary bg-primary/5 scale-[1.01]' : 'border-border hover:border-primary/50 hover:bg-muted/30'}`}
      >
        <input {...getInputProps()} />
        <div className={`p-4 rounded-full ${isDragActive ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'}`}>
          <UploadCloud className="w-8 h-8" />
        </div>
        <div>
          <p className="text-lg font-medium">{isDragActive ? 'Drop the PDFs here...' : 'Drag & drop PDF files here'}</p>
          <p className="text-sm text-muted-foreground mt-1">or click to browse from your computer</p>
        </div>
        {loading && <p className="text-sm text-primary animate-pulse">Uploading and analyzing...</p>}
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input 
            type="text" 
            placeholder="Search library..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-background border border-border rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
          />
        </div>
        <div className="text-sm text-muted-foreground">
          {selectedPaperIds.length} selected
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filteredPapers.map((paper) => {
          const isSelected = selectedPaperIds.includes(paper.id);
          return (
            <div 
              key={paper.id}
              onClick={() => toggleSelection(paper.id)}
              className={`relative rounded-xl border p-5 cursor-pointer transition-all duration-200 group bg-card/60 backdrop-blur-sm
                ${isSelected ? 'border-primary ring-1 ring-primary shadow-md' : 'border-border/50 hover:border-primary/50 hover:-translate-y-1'}`}
            >
              <div className="flex justify-between items-start mb-3 gap-4">
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-background/50 border border-border/50 text-xs font-medium w-fit">
                  {getStatusIcon(paper.status)}
                  <span className="capitalize">{paper.status}</span>
                </div>
                <button 
                  onClick={(e) => handleDelete(e, paper.id)}
                  className="opacity-0 group-hover:opacity-100 p-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-md transition-all"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              <h3 className="font-semibold text-lg leading-tight line-clamp-2 mb-2 group-hover:text-primary transition-colors">
                {paper.title || 'Untitled Paper'}
              </h3>
              
              <p className="text-sm text-muted-foreground line-clamp-1 mb-4">
                {paper.authors || 'Unknown Authors'}
              </p>
              
              {paper.difficulty_level && (
                <div className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-muted text-muted-foreground capitalize">
                  {paper.difficulty_level} Difficulty
                </div>
              )}
            </div>
          );
        })}
        {filteredPapers.length === 0 && (
          <div className="col-span-full py-12 text-center text-muted-foreground">
            No papers found. Upload some PDFs to get started!
          </div>
        )}
      </div>
    </div>
  );
}
