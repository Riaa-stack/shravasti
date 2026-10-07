import { useEffect, useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import { apiClient } from '@/api/client';
import { BrainCircuit, FileText, CheckCircle2, Clock, Sparkles } from 'lucide-react';
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

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await apiClient.get('/analytics/overview');
        setStats(response.data);
      } catch (error) {
        console.error('Failed to fetch analytics', error);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

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

  // Mock data if backend analytics are empty for now
  const topicData = stats?.top_topics?.length ? stats.top_topics : [
    { name: 'Machine Learning', value: 400 },
    { name: 'NLP', value: 300 },
    { name: 'Computer Vision', value: 300 },
    { name: 'Robotics', value: 200 },
  ];

  const activityData = [
    { name: 'Mon', papers: 2 },
    { name: 'Tue', papers: 5 },
    { name: 'Wed', papers: 3 },
    { name: 'Thu', papers: 8 },
    { name: 'Fri', papers: 4 },
    { name: 'Sat', papers: 1 },
    { name: 'Sun', papers: 0 },
  ];

  const COLORS = ['#4A88F7', '#8B5CF6', '#10B981', '#F59E0B'];

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      <div>
        <h1 className="text-3xl font-display font-bold tracking-tight">
          Welcome back, {user?.name?.split(' ')[0] || 'User'}
        </h1>
        <p className="text-muted-foreground mt-1">Here is the overview of your research workspace.</p>
      </div>

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
                  {topicData.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }}
                  itemStyle={{ color: 'hsl(var(--foreground))' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border border-border/50 bg-card/40 backdrop-blur-sm p-6">
          <h3 className="text-lg font-semibold mb-6">Reading Activity</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={activityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip 
                  cursor={{ fill: 'hsl(var(--muted))', opacity: 0.2 }}
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }}
                />
                <Bar dataKey="papers" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
