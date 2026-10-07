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
          <div className="text-right hidden md:block">
            <p className="text-sm font-medium leading-none">
              {user?.name || 'User'}
            </p>

            <p className="text-xs text-muted-foreground mt-1 capitalize">
              {user?.role || 'Guest'}
            </p>
          </div>

          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-google-blue to-google-red text-white flex items-center justify-center font-semibold shadow-md">
            {user?.name?.charAt(0).toUpperCase() || 'U'}
          </div>
        </div>
      </div>
    </header>
  );
}