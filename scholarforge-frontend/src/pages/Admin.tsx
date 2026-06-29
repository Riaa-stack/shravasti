import { useState, useEffect } from 'react';
import { useAuthStore } from '@/store/authStore';
import { apiClient } from '@/api/client';
import { Navigate } from 'react-router-dom';
import { Users, FileText, Activity, AlertTriangle, RefreshCcw } from 'lucide-react';
import { toast } from 'sonner';

export function Admin() {
  const user = useAuthStore(state => state.user);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/analytics/admin');
      setStats(response.data);
    } catch (error) {
      toast.error('Failed to load admin analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === 'admin') {
      fetchStats();
    }
  }, [user]);

  if (user?.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight text-destructive">Admin Console</h1>
          <p className="text-muted-foreground mt-1">Platform-wide analytics and system health.</p>
        </div>
        <button 
          onClick={fetchStats}
          disabled={loading}
          className="p-2 border border-border rounded-lg bg-card/50 hover:bg-muted transition-colors"
        >
          <RefreshCcw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {loading && !stats ? (
        <div className="h-64 flex items-center justify-center">
          <Activity className="w-12 h-12 text-muted-foreground animate-pulse" />
        </div>
      ) : stats ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-xl border border-border/50 bg-card/40 backdrop-blur-sm p-6 flex items-center gap-4">
            <div className="p-4 rounded-xl bg-blue-500/10 text-blue-500">
              <Users className="w-8 h-8" />
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Total Users</p>
              <h3 className="text-3xl font-bold">{stats.total_users || 0}</h3>
            </div>
          </div>

          <div className="rounded-xl border border-border/50 bg-card/40 backdrop-blur-sm p-6 flex items-center gap-4">
            <div className="p-4 rounded-xl bg-emerald-500/10 text-emerald-500">
              <FileText className="w-8 h-8" />
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Total Papers Hosted</p>
              <h3 className="text-3xl font-bold">{stats.total_papers || 0}</h3>
            </div>
          </div>

          <div className="rounded-xl border border-border/50 bg-card/40 backdrop-blur-sm p-6 flex items-center gap-4">
            <div className="p-4 rounded-xl bg-amber-500/10 text-amber-500">
              <Activity className="w-8 h-8" />
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Agent Invocations</p>
              <h3 className="text-3xl font-bold">{stats.total_agent_runs || 0}</h3>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-6 border border-destructive/20 bg-destructive/10 text-destructive rounded-xl flex items-center gap-3">
          <AlertTriangle className="w-6 h-6" />
          <p>Failed to load admin data. Check if you have proper permissions.</p>
        </div>
      )}
    </div>
  );
}
