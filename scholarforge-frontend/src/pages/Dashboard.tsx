import { useEffect, useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import { apiClient } from '@/api/client';
import { BrainCircuit, FileText, CheckCircle2, Clock, Sparkles, RefreshCw } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

export function Dashboard() {
  const user = useAuthStore((state) => state.user);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const fetchStats = async (showRefreshState = false) => {
      if (showRefreshState && mounted) setRefreshing(true);
      try {
        const response = await apiClient.get('/analytics/overview');
        if (mounted) {
          setStats(response.data);
          setAnalyticsError(null);
        }
      } catch (error) {
        console.error('Failed to fetch analytics', error);
        if (mounted) setAnalyticsError('Unable to load live analytics. Please try again.');
      } finally {
        if (mounted) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    };

    void fetchStats();
    // Refresh charts periodically so they reflect newly uploaded/processed papers.
    const intervalId = window.setInterval(() => void fetchStats(true), 60_000);
    return () => {
      mounted = false;
      window.clearInterval(intervalId);
    };
  }, []);

  const refreshAnalytics = async () => {
    setRefreshing(true);
    try {
      const response = await apiClient.get('/analytics/overview');
      setStats(response.data);
      setAnalyticsError(null);
    } catch (error) {
      console.error('Failed to refresh analytics', error);
      setAnalyticsError('Unable to load live analytics. Please try again.');
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-muted-foreground animate-pulse">
          <BrainCircuit className="w-12 h-12" />
          <p>Analyzing research patterns...</p>
        </div>
      </div>
    );
  }

  // Charts use only API data; empty states are shown when there is no real data.
  const topicData: Array<{ name: string; value: number }> = stats?.top_topics ?? [];
  const activityData: Array<{ date: string; name: string; papers: number }> = stats?.reading_activity ?? [];

  const COLORS = ['#4A88F7', '#8B5CF6', '#10B981', '#F59E0B'];

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-3xl font-display font-bold tracking-tight">
              Welcome back, {user?.name || 'User'}
            </h1>
            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border shadow-sm ${
              user?.role === 'professor' 
                ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30'
                : user?.role === 'researcher'
                ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30'
                : user?.role === 'student'
                ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
                : user?.role === 'reviewer'
                ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30'
                : user?.role === 'admin'
                ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30'
                : 'bg-primary/10 text-primary border-primary/20'
            }`}>
              {user?.role || 'Guest'}
            </span>
          </div>
          <p className="text-muted-foreground mt-1">Here is the overview of your research workspace.</p>
        </div>
        <button
          type="button"
          onClick={refreshAnalytics}
          disabled={refreshing}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Refreshing...' : 'Refresh charts'}
        </button>
      </div>
      {analyticsError && (
        <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {analyticsError}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {[
          { title: 'Total Papers', value: stats?.total_papers || 0, icon: FileText, color: 'text-blue-500', bg: 'bg-blue-500/10' },
          { title: 'Processed', value: stats?.processed_papers || 0, icon: CheckCircle2, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
          { title: 'Processing', value: stats?.processing_papers || 0, icon: Clock, color: 'text-amber-500', bg: 'bg-amber-500/10' },
          { title: 'AI Insights', value: stats?.total_insights || 0, icon: Sparkles, color: 'text-purple-500', bg: 'bg-purple-500/10' },
        ].map((stat, i) => (
          <div key={i} className="rounded-xl border border-border/50 bg-card/40 backdrop-blur-sm p-6 hover:-translate-y-1 transition-transform duration-300">
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-lg ${stat.bg}`}>
                <stat.icon className={`w-6 h-6 ${stat.color}`} />
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">{stat.title}</p>
                <h3 className="text-2xl font-bold">{stat.value}</h3>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-border/50 bg-card/40 backdrop-blur-sm p-6">
          <h3 className="text-lg font-semibold mb-6">Topic Distribution</h3>
          <div className="h-[300px] w-full">
            {topicData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={topicData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {topicData.map((_entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }}
                    itemStyle={{ color: 'hsl(var(--foreground))' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">No topic data yet. Add papers with a category to see the distribution.</div>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-border/50 bg-card/40 backdrop-blur-sm p-6">
          <h3 className="text-lg font-semibold mb-6">Reading Activity <span className="text-sm font-normal text-muted-foreground">(last 7 days)</span></h3>
          <div className="h-[300px] w-full">
            {activityData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={activityData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip
                    cursor={{ fill: 'hsl(var(--muted))', opacity: 0.2 }}
                    contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }}
                  />
                  <Bar dataKey="papers" name="Papers added" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">No reading activity data available yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
