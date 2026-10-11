import { Moon, Sun, Bell, Search as SearchIcon } from 'lucide-react';
import { useTheme } from '@/store/themeStore';
import { useAuthStore } from '@/store/authStore';

export function Header() {
  const { theme, toggleTheme } = useTheme();
  const user = useAuthStore((state) => state.user);

  return (
    <header className="h-16 border-b border-border/50 bg-card/30 backdrop-blur-md flex items-center justify-between px-6 sticky top-0 z-10 transition-colors duration-300">
      <div className="flex items-center gap-4 flex-1">
        <div className="relative max-w-md w-full group">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-primary transition-colors" />

          <input
            type="text"
            placeholder="Search papers, authors, topics (Cmd+K)"
            className="w-full bg-background/50 border border-border rounded-full pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all placeholder:text-muted-foreground/70"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-full transition-colors relative">
          <Bell className="w-5 h-5" />

          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-primary rounded-full ring-2 ring-card" />
        </button>

        <button
          onClick={toggleTheme}
          className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-full transition-colors"
        >
          {theme === 'dark' ? (
            <Sun className="w-5 h-5" />
          ) : (
            <Moon className="w-5 h-5" />
          )}
        </button>

        <div className="flex items-center gap-3 pl-4 border-l border-border/50">
          <div className="text-right">
            <p className="text-sm font-semibold leading-tight text-foreground">
              {user?.name || 'User'}
            </p>
            <div className="flex items-center justify-end mt-1">
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium tracking-wide uppercase shadow-sm border ${
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
          </div>

          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary via-indigo-600 to-violet-600 text-white flex items-center justify-center font-bold shadow-md border-2 border-background">
            {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
          </div>
        </div>
      </div>
    </header>
  );
}