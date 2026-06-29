import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { BrainCircuit, Loader2, ArrowRight } from 'lucide-react';
import { apiClient } from '@/api/client';
import { toast } from 'sonner';
import { ScholarIcon } from '@/components/ui/ScholarIcon';

export function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('student');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await apiClient.post('/auth/register', {
        email,
        password,
        name: fullName,
        role
      });
      
      toast.success('Account created! Please sign in.');
      navigate('/login');
    } catch (error) {
      toast.error('Registration failed. Email might be in use.');
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
          
          <h2 className="text-2xl font-display font-semibold text-center mb-2">Create Account</h2>
          <p className="text-muted-foreground text-center text-sm mb-6">
            Join ScholarForge to accelerate your research
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Full Name</label>
              <input 
                type="text" 
                required
                value={fullName}
                onChange={e => setFullName(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                placeholder="Jane Doe"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">Email address</label>
              <input 
                type="email" 
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                placeholder="name@example.com"
              />
            </div>
            
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Password</label>
              <input 
                type="password" 
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                placeholder="••••••••"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">Role</label>
              <select 
                value={role}
                onChange={e => setRole(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
              >
                <option value="student">Student</option>
                <option value="researcher">Researcher</option>
                <option value="academician">Academician</option>
              </select>
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-medium rounded-lg px-4 py-2.5 mt-4 flex items-center justify-center transition-colors disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Create Account'}
            </button>
          </form>
        </div>
        
        <div className="p-4 bg-muted/30 border-t border-border/50 text-center">
          <p className="text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link to="/login" className="text-primary hover:underline font-medium inline-flex items-center gap-1">
              Sign In <ArrowRight className="w-3 h-3" />
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
