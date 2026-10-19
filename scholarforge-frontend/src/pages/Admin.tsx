import { useState, useEffect, useMemo } from 'react';
import { useAuthStore } from '@/store/authStore';
import { apiClient } from '@/api/client';
import { Navigate } from 'react-router-dom';
import {
  Users,
  FileText,
  AlertTriangle,
  RefreshCcw,
  Trash2,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  Search,
  Filter,
  X,
  ShieldBan
} from 'lucide-react';
import { toast } from 'sonner';

interface PaperItem {
  id: string;
  user_id: string;
  title: string | null;
  authors: string[] | null;
  publication_year: number | null;
  venue: string | null;
  doi: string | null;
  abstract: string | null;
  category: string | null;
  difficulty_level: string | null;
  page_count: number | null;
  status: string;
  is_flagged: boolean;
  flag_reason: string | null;
  is_available_for_ai: boolean;
  created_at: string;
  updated_at: string;
  user_name: string | null;
  user_email: string | null;
  user_role: string | null;
}

interface UserItem {
  id: string;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export function Admin() {
  const currentUser = useAuthStore((state) => state.user);

  const [activeTab, setActiveTab] = useState<'papers' | 'users'>('papers');
  const [stats, setStats] = useState<any>(null);
  const [papers, setPapers] = useState<PaperItem[]>([]);
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [paperFilter, setPaperFilter] = useState<'all' | 'flagged' | 'ai_disabled' | 'safe'>('all');

  // Flag Modal State
  const [flagModalPaper, setFlagModalPaper] = useState<PaperItem | null>(null);
  const [flagReasonInput, setFlagReasonInput] = useState('');
  const [flagIsHarmful, setFlagIsHarmful] = useState(true);
  const [flagDisableAI, setFlagDisableAI] = useState(true);
  const [savingFlag, setSavingFlag] = useState(false);

  // Delete Confirmations
  const [deletingPaperId, setDeletingPaperId] = useState<string | null>(null);
  const [deletingUserId, setDeletingUserId] = useState<string | null>(null);

  const fetchAdminData = async (silent = false) => {
    if (!silent) setLoading(true);
    setRefreshing(true);
    try {
      const [analyticsRes, papersRes, usersRes] = await Promise.all([
        apiClient.get('/analytics/admin').catch(() => ({ data: null })),
        apiClient.get('/papers/admin/all'),
        apiClient.get('/users/'),
      ]);

      if (analyticsRes.data) setStats(analyticsRes.data);
      if (papersRes.data) setPapers(papersRes.data);
      if (usersRes.data) setUsers(usersRes.data);
    } catch (error) {
      toast.error('Failed to load admin management data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (currentUser?.role === 'admin') {
      fetchAdminData();
    }
  }, [currentUser]);

  if (currentUser?.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  // Handle Flag Update
  const handleOpenFlagModal = (paper: PaperItem) => {
    setFlagModalPaper(paper);
    setFlagReasonInput(paper.flag_reason || 'Harmful or sensitive material');
    setFlagIsHarmful(paper.is_flagged);
    setFlagDisableAI(!paper.is_available_for_ai);
  };

  const handleSaveFlag = async () => {
    if (!flagModalPaper) return;
    setSavingFlag(true);
    try {
      const response = await apiClient.patch(`/papers/admin/${flagModalPaper.id}/flag`, {
        is_flagged: flagIsHarmful,
        flag_reason: flagIsHarmful || flagDisableAI ? flagReasonInput : null,
        is_available_for_ai: !flagDisableAI,
      });

      const updatedPaper = response.data;
      setPapers((prev) =>
        prev.map((p) => (p.id === updatedPaper.id ? { ...p, ...updatedPaper } : p))
      );

      toast.success(
        flagIsHarmful
          ? 'Paper flagged as harmful and AI disabled'
          : !flagDisableAI
          ? 'Paper unflagged and restored to safe status'
          : 'Paper AI analysis restricted'
      );
      setFlagModalPaper(null);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to update paper moderation status');
    } finally {
      setSavingFlag(false);
    }
  };

  const handleQuickToggleAI = async (paper: PaperItem) => {
    const newAiState = !paper.is_available_for_ai;
    try {
      const response = await apiClient.patch(`/papers/admin/${paper.id}/flag`, {
        is_available_for_ai: newAiState,
      });
      const updated = response.data;
      setPapers((prev) =>
        prev.map((p) => (p.id === updated.id ? { ...p, ...updated } : p))
      );
      toast.success(
        newAiState
          ? `AI analysis enabled for "${paper.title || 'Paper'}"`
          : `AI analysis disabled for "${paper.title || 'Paper'}"`
      );
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to toggle AI status');
    }
  };

  // Handle Paper Deletion
  const handleDeletePaper = async (paperId: string) => {
    if (!window.confirm('Are you sure you want to delete this paper from the system library?')) {
      return;
    }
    setDeletingPaperId(paperId);
    try {
      await apiClient.delete(`/papers/admin/${paperId}`);
      setPapers((prev) => prev.filter((p) => p.id !== paperId));
      toast.success('Paper successfully deleted from system library');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to delete paper');
    } finally {
      setDeletingPaperId(null);
    }
  };

  // Handle User Deletion
  const handleDeleteUser = async (userId: string, userName: string) => {
    if (userId === currentUser?.id) {
      toast.error('You cannot delete your own admin account');
      return;
    }
    if (
      !window.confirm(
        `Are you sure you want to permanently delete user "${userName}" and all their associated records?`
      )
    ) {
      return;
    }
    setDeletingUserId(userId);
    try {
      await apiClient.delete(`/users/${userId}`);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
      // Also remove their papers from local view
      setPapers((prev) => prev.filter((p) => p.user_id !== userId));
      toast.success(`User ${userName} deleted successfully`);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to delete user');
    } finally {
      setDeletingUserId(null);
    }
  };

  // Filtered papers
  const filteredPapers = useMemo(() => {
    return papers.filter((p) => {
      const q = searchQuery.toLowerCase().trim();
      const matchQuery =
        !q ||
        (p.title || '').toLowerCase().includes(q) ||
        (p.user_name || '').toLowerCase().includes(q) ||
        (p.user_email || '').toLowerCase().includes(q) ||
        (p.user_role || '').toLowerCase().includes(q) ||
        (p.category || '').toLowerCase().includes(q);

      if (!matchQuery) return false;

      if (paperFilter === 'flagged') return p.is_flagged;
      if (paperFilter === 'ai_disabled') return !p.is_available_for_ai;
      if (paperFilter === 'safe') return !p.is_flagged && p.is_available_for_ai;
      return true;
    });
  }, [papers, searchQuery, paperFilter]);

  // Filtered users
  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      const q = searchQuery.toLowerCase().trim();
      return (
        !q ||
        u.name.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q) ||
        u.role.toLowerCase().includes(q)
      );
    });
  }, [users, searchQuery]);

  const flaggedCount = papers.filter((p) => p.is_flagged).length;
  const aiDisabledCount = papers.filter((p) => !p.is_available_for_ai).length;

  const getRoleBadge = (role: string | null) => {
    const r = (role || 'student').toLowerCase();
    const colors: Record<string, string> = {
      admin: 'bg-rose-500/10 text-rose-500 border-rose-500/30',
      professor: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
      researcher: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
      reviewer: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      academician: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
      student: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
      guest: 'bg-muted text-muted-foreground border-border',
    };
    return (
      <span
        className={`px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wider border ${
          colors[r] || colors.guest
        }`}
      >
        {role || 'Unknown'}
      </span>
    );
  };

  return (
    <div className="space-y-8 animate-fade-in pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="px-2.5 py-1 rounded-md bg-rose-500/10 text-rose-500 border border-rose-500/20 text-xs font-bold tracking-wide uppercase">
              Admin Privilege
            </span>
            <h1 className="text-3xl font-display font-bold tracking-tight text-foreground">
              Master Admin Console
            </h1>
          </div>
          <p className="text-muted-foreground mt-1 text-sm">
            Control platform libraries, oversee user accounts, and enforce moderation & AI safety.
          </p>
        </div>
        <button
          onClick={() => fetchAdminData(true)}
          disabled={refreshing}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg border border-border bg-card/60 hover:bg-muted transition-colors disabled:opacity-50 self-start sm:self-auto shadow-sm"
        >
          <RefreshCcw className={`w-4 h-4 ${refreshing ? 'animate-spin text-primary' : ''}`} />
          Sync Live Data
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-border/60 bg-card/50 backdrop-blur-sm p-5 flex items-center gap-4 shadow-sm">
          <div className="p-3.5 rounded-xl bg-blue-500/10 text-blue-500 shrink-0">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Total Users
            </p>
            <h3 className="text-2xl font-bold mt-0.5">{users.length || stats?.total_users || 0}</h3>
          </div>
        </div>

        <div className="rounded-xl border border-border/60 bg-card/50 backdrop-blur-sm p-5 flex items-center gap-4 shadow-sm">
          <div className="p-3.5 rounded-xl bg-emerald-500/10 text-emerald-500 shrink-0">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Total Hosted Papers
            </p>
            <h3 className="text-2xl font-bold mt-0.5">{papers.length || stats?.total_papers || 0}</h3>
          </div>
        </div>

        <div className="rounded-xl border border-border/60 bg-card/50 backdrop-blur-sm p-5 flex items-center gap-4 shadow-sm">
          <div className="p-3.5 rounded-xl bg-rose-500/10 text-rose-500 shrink-0">
            <ShieldBan className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Harm Flagged Papers
            </p>
            <h3 className="text-2xl font-bold mt-0.5 text-rose-500">{flaggedCount}</h3>
          </div>
        </div>

        <div className="rounded-xl border border-border/60 bg-card/50 backdrop-blur-sm p-5 flex items-center gap-4 shadow-sm">
          <div className="p-3.5 rounded-xl bg-amber-500/10 text-amber-500 shrink-0">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              AI Analysis Blocked
            </p>
            <h3 className="text-2xl font-bold mt-0.5 text-amber-500">{aiDisabledCount}</h3>
          </div>
        </div>
      </div>

      {/* Tabs & Search Navigation */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/60 pb-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setActiveTab('papers');
              setSearchQuery('');
            }}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              activeTab === 'papers'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            <FileText className="w-4 h-4" />
            Uploaded Papers ({papers.length})
          </button>
          <button
            onClick={() => {
              setActiveTab('users');
              setSearchQuery('');
            }}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              activeTab === 'users'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground'
            }`}
          >
            <Users className="w-4 h-4" />
            User Management ({users.length})
          </button>
        </div>

        {/* Search Bar */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={
              activeTab === 'papers'
                ? 'Search title, uploader, role...'
                : 'Search users, role, email...'
            }
            className="w-full pl-9 pr-4 py-2 rounded-lg text-sm bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/40 transition-all"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* TAB 1: PAPERS MANAGEMENT */}
      {activeTab === 'papers' && (
        <div className="space-y-4">
          {/* Subfilters */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5 mr-1">
              <Filter className="w-3.5 h-3.5" /> Filter:
            </span>
            {[
              { id: 'all', label: `All Papers (${papers.length})` },
              { id: 'safe', label: 'Safe & Active' },
              { id: 'flagged', label: `Harm Flagged (${flaggedCount})` },
              { id: 'ai_disabled', label: `AI Disabled (${aiDisabledCount})` },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setPaperFilter(f.id as any)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  paperFilter === f.id
                    ? 'bg-primary/15 text-primary border border-primary/30'
                    : 'bg-card border border-border/60 text-muted-foreground hover:bg-muted'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Papers Table */}
          <div className="rounded-xl border border-border/70 bg-card/60 backdrop-blur-sm overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-muted/40 border-b border-border text-xs uppercase tracking-wider text-muted-foreground font-semibold">
                  <tr>
                    <th className="px-5 py-3.5">Research Paper</th>
                    <th className="px-5 py-3.5">Uploaded By</th>
                    <th className="px-4 py-3.5">Author Role</th>
                    <th className="px-4 py-3.5">AI Availability</th>
                    <th className="px-4 py-3.5">Moderation</th>
                    <th className="px-5 py-3.5 text-right">Admin Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {filteredPapers.map((paper) => {
                    const isFlagged = paper.is_flagged;

                    return (
                      <tr
                        key={paper.id}
                        className={`transition-colors hover:bg-muted/30 ${
                          isFlagged ? 'bg-rose-500/[0.03]' : ''
                        }`}
                      >
                        {/* Title & Meta */}
                        <td className="px-5 py-4 max-w-xs">
                          <p className="font-semibold text-foreground line-clamp-2 leading-snug">
                            {paper.title || 'Untitled Research Paper'}
                          </p>
                          <div className="flex items-center gap-2 mt-1.5 text-xs text-muted-foreground">
                            <span>{paper.category || 'General'}</span>
                            {paper.publication_year && (
                              <>
                                <span>•</span>
                                <span>{paper.publication_year}</span>
                              </>
                            )}
                            <span>•</span>
                            <span className="capitalize">{paper.status}</span>
                          </div>
                        </td>

                        {/* Uploader Details */}
                        <td className="px-5 py-4">
                          <p className="font-medium text-foreground">{paper.user_name || 'Anonymous'}</p>
                          <p className="text-xs text-muted-foreground font-mono mt-0.5">
                            {paper.user_email || 'No email'}
                          </p>
                        </td>

                        {/* Role */}
                        <td className="px-4 py-4">{getRoleBadge(paper.user_role)}</td>

                        {/* AI Status */}
                        <td className="px-4 py-4">
                          {paper.is_available_for_ai ? (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              AI Enabled
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-medium">
                              <ShieldAlert className="w-3.5 h-3.5" />
                              AI Blocked
                            </span>
                          )}
                        </td>

                        {/* Moderation Status */}
                        <td className="px-4 py-4">
                          {isFlagged ? (
                            <div className="space-y-1">
                              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30 text-xs font-semibold">
                                <AlertTriangle className="w-3 h-3" />
                                Harm Flagged
                              </span>
                              {paper.flag_reason && (
                                <p className="text-[11px] text-rose-300/80 italic max-w-[160px] truncate">
                                  {paper.flag_reason}
                                </p>
                              )}
                            </div>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-muted/60 text-muted-foreground border border-border text-xs">
                              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                              Verified Safe
                            </span>
                          )}
                        </td>

                        {/* Actions */}
                        <td className="px-5 py-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {/* Toggle AI Button */}
                            <button
                              onClick={() => handleQuickToggleAI(paper)}
                              title={
                                paper.is_available_for_ai
                                  ? 'Click to Block AI analysis'
                                  : 'Click to Enable AI analysis'
                              }
                              className={`p-2 rounded-lg border text-xs font-medium transition-colors ${
                                paper.is_available_for_ai
                                  ? 'border-border text-muted-foreground hover:bg-amber-500/10 hover:text-amber-400 hover:border-amber-500/30'
                                  : 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20'
                              }`}
                            >
                              <ShieldAlert className="w-4 h-4" />
                            </button>

                            {/* Flag / Moderation Button */}
                            <button
                              onClick={() => handleOpenFlagModal(paper)}
                              title="Set Harm Flag or AI Policy"
                              className={`p-2 rounded-lg border transition-colors ${
                                isFlagged
                                  ? 'bg-rose-500/15 border-rose-500/40 text-rose-400 hover:bg-rose-500/25'
                                  : 'border-border text-muted-foreground hover:bg-rose-500/10 hover:text-rose-400 hover:border-rose-500/30'
                              }`}
                            >
                              <AlertTriangle className="w-4 h-4" />
                            </button>

                            {/* Delete Paper Button */}
                            <button
                              onClick={() => handleDeletePaper(paper.id)}
                              disabled={deletingPaperId === paper.id}
                              title="Delete paper from library permanently"
                              className="p-2 rounded-lg border border-border text-muted-foreground hover:bg-destructive/15 hover:text-destructive hover:border-destructive/30 transition-colors disabled:opacity-50"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}

                  {filteredPapers.length === 0 && (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-muted-foreground">
                        {loading ? (
                          <div className="flex flex-col items-center justify-center gap-2">
                            <RefreshCcw className="w-6 h-6 animate-spin text-primary" />
                            <p className="font-medium text-sm">Loading library papers...</p>
                          </div>
                        ) : (
                          <>
                            <FileText className="w-8 h-8 mx-auto text-muted-foreground/40 mb-2" />
                            <p className="font-medium text-sm">No research papers match your criteria</p>
                          </>
                        )}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: USER MANAGEMENT */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-border/70 bg-card/60 backdrop-blur-sm overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-muted/40 border-b border-border text-xs uppercase tracking-wider text-muted-foreground font-semibold">
                  <tr>
                    <th className="px-5 py-3.5">User</th>
                    <th className="px-5 py-3.5">Email Address</th>
                    <th className="px-4 py-3.5">Role</th>
                    <th className="px-4 py-3.5">Status</th>
                    <th className="px-4 py-3.5">Papers Hosted</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {filteredUsers.map((u) => {
                    const isSelf = u.id === currentUser?.id;
                    const userPaperCount = papers.filter((p) => p.user_id === u.id).length;

                    return (
                      <tr key={u.id} className="transition-colors hover:bg-muted/30">
                        {/* Name & Avatar */}
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-primary to-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-sm">
                              {u.name ? u.name.charAt(0).toUpperCase() : 'U'}
                            </div>
                            <div>
                              <p className="font-semibold text-foreground flex items-center gap-1.5">
                                {u.name}
                                {isSelf && (
                                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-primary/20 text-primary font-bold">
                                    YOU
                                  </span>
                                )}
                              </p>
                              <p className="text-[11px] text-muted-foreground font-mono">
                                ID: {u.id.slice(0, 8)}...
                              </p>
                            </div>
                          </div>
                        </td>

                        {/* Email */}
                        <td className="px-5 py-4 font-mono text-xs text-foreground/90">{u.email}</td>

                        {/* Role */}
                        <td className="px-4 py-4">{getRoleBadge(u.role)}</td>

                        {/* Account Status */}
                        <td className="px-4 py-4">
                          <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              u.is_active
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                : 'bg-destructive/10 text-destructive border border-destructive/20'
                            }`}
                          >
                            <span
                              className={`w-1.5 h-1.5 rounded-full ${
                                u.is_active ? 'bg-emerald-400' : 'bg-destructive'
                              }`}
                            />
                            {u.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>

                        {/* Paper count */}
                        <td className="px-4 py-4">
                          <span className="font-semibold text-foreground">{userPaperCount}</span>{' '}
                          <span className="text-xs text-muted-foreground">papers</span>
                        </td>

                        {/* Action */}
                        <td className="px-5 py-4 text-right">
                          <button
                            onClick={() => handleDeleteUser(u.id, u.name)}
                            disabled={isSelf || deletingUserId === u.id}
                            title={
                              isSelf
                                ? 'Cannot delete current active admin'
                                : `Delete user "${u.name}" permanently`
                            }
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs font-semibold text-muted-foreground hover:bg-destructive/15 hover:text-destructive hover:border-destructive/30 transition-colors disabled:opacity-30 disabled:pointer-events-none"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            Delete User
                          </button>
                        </td>
                      </tr>
                    );
                  })}

                  {filteredUsers.length === 0 && (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-muted-foreground">
                        {loading ? (
                          <div className="flex flex-col items-center justify-center gap-2">
                            <RefreshCcw className="w-6 h-6 animate-spin text-primary" />
                            <p className="font-medium text-sm">Loading users...</p>
                          </div>
                        ) : (
                          <>
                            <Users className="w-8 h-8 mx-auto text-muted-foreground/40 mb-2" />
                            <p className="font-medium text-sm">No users match your criteria</p>
                          </>
                        )}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* FLAG & MODERATION MODAL */}
      {flagModalPaper && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg bg-card border border-border/80 rounded-2xl shadow-2xl p-6 space-y-5 animate-scale-up">
            <div className="flex items-center justify-between pb-3 border-b border-border/50">
              <div className="flex items-center gap-2 text-rose-500 font-semibold text-lg">
                <AlertTriangle className="w-5 h-5" />
                <h3>Paper Moderation & AI Control</h3>
              </div>
              <button
                onClick={() => setFlagModalPaper(null)}
                className="p-1 rounded-lg text-muted-foreground hover:bg-muted transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">
                Target Research Paper
              </p>
              <h4 className="font-bold text-foreground text-sm line-clamp-2 mt-1">
                {flagModalPaper.title || 'Untitled Research Paper'}
              </h4>
              <p className="text-xs text-muted-foreground mt-1">
                Uploaded by {flagModalPaper.user_name} ({flagModalPaper.user_role})
              </p>
            </div>

            <div className="space-y-4">
              {/* Flag as harm toggle */}
              <label className="flex items-start gap-3 p-3.5 rounded-xl border border-border/70 bg-muted/20 cursor-pointer hover:bg-muted/40 transition-colors">
                <input
                  type="checkbox"
                  checked={flagIsHarmful}
                  onChange={(e) => {
                    setFlagIsHarmful(e.target.checked);
                    if (e.target.checked) setFlagDisableAI(true);
                  }}
                  className="mt-0.5 rounded border-border text-rose-500 focus:ring-rose-500 w-4 h-4"
                />
                <div>
                  <p className="text-sm font-semibold text-rose-500">Flag as Harmful / Inappropriate</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Marks this paper with a high-priority warning badge and warns platform users.
                  </p>
                </div>
              </label>

              {/* Disable AI toggle */}
              <label className="flex items-start gap-3 p-3.5 rounded-xl border border-border/70 bg-muted/20 cursor-pointer hover:bg-muted/40 transition-colors">
                <input
                  type="checkbox"
                  checked={flagDisableAI}
                  onChange={(e) => setFlagDisableAI(e.target.checked)}
                  className="mt-0.5 rounded border-border text-amber-500 focus:ring-amber-500 w-4 h-4"
                />
                <div>
                  <p className="text-sm font-semibold text-amber-500">
                    Not Available for AI Analysis
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Strictly prevents AI agents (literature review, methodology, gaps, chat) from
                    analyzing or synthesizing this paper.
                  </p>
                </div>
              </label>

              {/* Flag reason input */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Reason / Flag Notice
                </label>
                <input
                  type="text"
                  value={flagReasonInput}
                  onChange={(e) => setFlagReasonInput(e.target.value)}
                  placeholder="e.g. Chemical synthesis hazard, sensitive content, copyright notice"
                  className="w-full bg-background border border-border rounded-lg px-3.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                />

                {/* Preset tags */}
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {[
                    'Harmful chemical syntheses',
                    'Biosecurity hazard',
                    'Copyright & IP violation',
                    'Policy breach / inappropriate',
                    'Corrupted text / unprocessable',
                  ].map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      onClick={() => setFlagReasonInput(preset)}
                      className="px-2 py-0.5 rounded-md bg-muted text-[11px] text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {preset}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-border/50">
              <button
                type="button"
                onClick={() => setFlagModalPaper(null)}
                className="px-4 py-2 text-xs font-semibold rounded-lg border border-border text-muted-foreground hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={savingFlag}
                onClick={handleSaveFlag}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 shadow-sm"
              >
                {savingFlag ? 'Saving...' : 'Apply Moderation Settings'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
