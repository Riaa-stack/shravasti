import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { BrainCircuit, Loader2, ArrowRight } from 'lucide-react';
import { apiClient } from '@/api/client';
import { useAuthStore } from '@/store/authStore';
import { toast } from 'sonner';
import { ScholarIcon } from '@/components/ui/ScholarIcon';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const setTokens = useAuthStore(state => state.setTokens);
  const setUser = useAuthStore(state => state.setUser);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append('username', email); // OAuth2 expects username
      formData.append('password', password);

      const response = await apiClient.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      
      const { access_token, refresh_token } = response.data;
      setTokens(access_token, refresh_token);
      
      const userResponse = await apiClient.get('/auth/me', {
        headers: { Authorization: `Bearer ${access_token}` }
      });
      
      setUser(userResponse.data);
      toast.success('Welcome back to ScholarForge');
      navigate('/');
    } catch (error) {
      toast.error('Invalid credentials or server error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-background/80 backdrop-blur-sm -z-10" />
      
      <div className="w-full max-w-md bg-card/80 backdrop-blur-xl border border-border/50 rounded-2xl shadow-2xl overflow-hidden animate-slide-up">
        <div className="p-8">
          <div className="flex justify-center mb-8">
            <div className="p-3 bg-primary/10 rounded-xl">
              <ScholarIcon className="w-10 h-10 text-primary" />
            </div>
          </div>
          
          <h2 className="text-2xl font-display font-semibold text-center mb-2">Welcome Back</h2>
          <p className="text-muted-foreground text-center text-sm mb-8">
            Sign in to access your research workspace
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Email address</label>
              <input 
                type="email" 
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                placeholder="name@example.com"
              />
            </div>
            
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-sm font-medium">Password</label>
                <a href="#" className="text-xs text-primary hover:underline">Forgot password?</a>
              </div>
              <input 
                type="password" 
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                placeholder="••••••••"
              />
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-medium rounded-lg px-4 py-2.5 mt-2 flex items-center justify-center transition-colors disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Sign In'}
            </button>
          </form>
        </div>
        
        <div className="p-4 bg-muted/30 border-t border-border/50 text-center">
          <p className="text-sm text-muted-foreground">
            Don't have an account?{' '}
            <Link to="/register" className="text-primary hover:underline font-medium inline-flex items-center gap-1">
              Create one <ArrowRight className="w-3 h-3" />
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
