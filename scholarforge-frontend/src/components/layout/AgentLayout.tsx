import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { 
  BookOpen, 
  Settings2, 
  SearchX, 
  TrendingUp, 
  Lightbulb, 
  Quote, 
  Brain,
  MessageSquare
} from 'lucide-react';

const agentNav = [
  { label: 'Literature Review', to: '/agents/literature-review', icon: BookOpen },
  { label: 'Methodology', to: '/agents/methodology', icon: Settings2 },
  { label: 'Research Gaps', to: '/agents/research-gaps', icon: SearchX },
  { label: 'Trends', to: '/agents/trends', icon: TrendingUp },
  { label: 'Ideas', to: '/agents/ideas', icon: Lightbulb },
  { label: 'Citations', to: '/agents/citations', icon: Quote },
  { label: 'Difficulty', to: '/agents/difficulty', icon: Brain },
  { label: 'Chat', to: '/agents/chat', icon: MessageSquare },
];

export function AgentLayout() {
  const location = useLocation();

  return (
    <div className="flex h-full gap-6 animate-fade-in pb-8">
      {/* Agent Selector Sidebar */}
      <div className="w-64 flex-shrink-0">
        <div className="sticky top-0 space-y-1">
          <h2 className="px-3 text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">
            AI Analysts
          </h2>
          {agentNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive 
                    ? 'bg-primary text-primary-foreground shadow-md shadow-primary/20' 
                    : 'text-muted-foreground hover:bg-card hover:text-foreground border border-transparent hover:border-border/50'
                }`
              }
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </NavLink>
          ))}
        </div>
      </div>

      {/* Agent Content Area */}
      <div className="flex-1 bg-card/40 backdrop-blur-sm border border-border/50 rounded-2xl overflow-hidden flex flex-col relative">
        {/* Subtle top inner shadow/glow */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-primary/20 to-transparent" />
        
        <Outlet />
      </div>
    </div>
  );
}
