import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Files, 
  Search, 
  LineChart, 
  Settings, 
  LogOut,
  BrainCircuit,
  MessageSquare,
  Network
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { ScholarIcon } from '@/components/ui/ScholarIcon';

const mainNav = [
  { icon: LayoutDashboard, label: 'Dashboard', to: '/' },
  { icon: Files, label: 'Library', to: '/papers' },
  { icon: Search, label: 'Search', to: '/search' },
  { icon: MessageSquare, label: 'Chat', to: '/chat' },
  { icon: Network, label: 'Knowledge Graph', to: '/knowledge-graph' },
];

const agentNav = [
  { label: 'Literature Review', to: '/agents/literature-review' },
  { label: 'Methodology', to: '/agents/methodology' },
  { label: 'Research Gaps', to: '/agents/research-gaps' },
  { label: 'Trends', to: '/agents/trends' },
  { label: 'Ideas', to: '/agents/ideas' },
  { label: 'Citations', to: '/agents/citations' },
  { label: 'Difficulty', to: '/agents/difficulty' },
];

export function Sidebar() {
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);

  return (
    <aside className="w-64 h-screen border-r border-border/50 bg-card/50 backdrop-blur flex flex-col transition-all duration-300">
      <div className="p-6 flex items-center gap-3">
        <div className="p-2 bg-background rounded-lg border border-border shadow-sm relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-tr from-google-blue via-google-red to-google-yellow opacity-20" />
          <ScholarIcon className="w-6 h-6 text-google-blue relative z-10" />
        </div>
        <span className="font-display font-semibold text-xl tracking-tight bg-gradient-to-r from-google-blue to-google-red bg-clip-text text-transparent">ScholarForge</span>
      </div>

      <nav className="flex-1 px-4 space-y-8 overflow-y-auto">
        <div>
          <p className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Platform</p>
          <div className="space-y-1">
            {mainNav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all ${
                    isActive 
                      ? 'bg-gradient-to-r from-google-blue/10 to-transparent border-l-2 border-google-blue text-google-blue font-medium' 
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground border-l-2 border-transparent'
                  }`
                }
              >
                <item.icon className="w-4 h-4" />
                {item.label}
              </NavLink>
            ))}
            {user?.role === 'admin' && (
              <NavLink
                to="/admin"
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                    isActive 
                      ? 'bg-primary/10 text-primary font-medium' 
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  }`
                }
              >
                <Settings className="w-4 h-4" />
                Admin Panel
              </NavLink>
            )}
          </div>
        </div>

        <div>
          <p className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">AI Agents</p>
          <div className="space-y-1">
            {agentNav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all ${
                    isActive 
                      ? 'bg-gradient-to-r from-google-green/10 to-transparent border-l-2 border-google-green text-google-green font-medium' 
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground border-l-2 border-transparent'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <div className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-google-green shadow-[0_0_8px_rgba(52,168,83,0.8)]' : 'bg-transparent'}`} />
                    {item.label}
                  </>
                )}
              </NavLink>
            ))}
          </div>
        </div>
      </nav>

      <div className="p-4 border-t border-border/50">
        <button
          onClick={logout}
          className="flex items-center gap-3 px-3 py-2 w-full rounded-md text-sm text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </button>
      </div>
    </aside>
  );
}
