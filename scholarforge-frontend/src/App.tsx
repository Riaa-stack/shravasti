import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';

import { ParticleBackground } from '@/components/layout/ParticleBackground';
import { AppShell } from '@/components/layout/AppShell';
import { useAuthStore } from '@/store/authStore';

import { Dashboard } from '@/pages/Dashboard';
import { Login } from '@/pages/Login';
import { Register } from '@/pages/Register';
import { LandingPage } from '@/pages/LandingPage';
import { PaperLibrary } from '@/pages/PaperLibrary';
import { AgentLayout } from '@/components/layout/AgentLayout';
import { GenericAgent } from '@/pages/agents/GenericAgent';
import { ChatAgent } from '@/pages/agents/ChatAgent';
import { KnowledgeGraph } from '@/pages/KnowledgeGraph';
import { Admin } from '@/pages/Admin';

const queryClient = new QueryClient();

// A simple protective wrapper
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const token = useAuthStore((state) => state.accessToken);
  if (!token) return <Navigate to="/landing" replace />;
  return <>{children}</>;
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ParticleBackground />

        <Routes>
          {/* Public Routes */}
          <Route path="/landing" element={<LandingPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected Routes */}
          <Route path="/" element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="papers" element={<PaperLibrary />} />

            <Route path="agents" element={<AgentLayout />}>
              <Route path="chat" element={<ChatAgent />} />
              <Route path="*" element={<GenericAgent />} />
            </Route>

            <Route path="knowledge-graph" element={<KnowledgeGraph />} />
            <Route path="admin" element={<Admin />} />
          </Route>
        </Routes>

        <Toaster position="bottom-right" theme="system" />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
