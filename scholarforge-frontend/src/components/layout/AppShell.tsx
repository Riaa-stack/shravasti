import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { AnimatedGrid } from './AnimatedGrid';

export function AppShell() {
  return (
    <>
      <AnimatedGrid />
      <div className="flex h-screen w-full overflow-hidden bg-transparent relative z-10">
        <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 overflow-y-auto p-6 scroll-smooth">
          <div className="max-w-7xl mx-auto h-full relative animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
    </>
  );
}
