import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Loader2, Network, BookOpen, Layers, Moon, Sun, CheckCircle2, Zap, Shield, FileSearch } from 'lucide-react';
import { apiClient } from '@/api/client';
import { useAuthStore } from '@/store/authStore';
import { useTheme } from '@/store/themeStore';
import { toast } from 'sonner';
import { LandingGraph } from '@/components/ui/LandingGraph';
import { ScholarIcon } from '@/components/ui/ScholarIcon';

export function LandingPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  
  const navigate = useNavigate();
  const setTokens = useAuthStore(state => state.setTokens);
  const setUser = useAuthStore(state => state.setUser);
  const { theme, toggleTheme } = useTheme();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (isLogin) {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);
        const response = await apiClient.post('/auth/login', formData, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        });
        setTokens(response.data.access_token, response.data.refresh_token);
        const userResponse = await apiClient.get('/auth/me', {
          headers: { Authorization: `Bearer ${response.data.access_token}` }
        });
        setUser(userResponse.data);
        toast.success('Welcome back!');
      } else {
        await apiClient.post('/auth/register', { email, password, name });
        toast.success('Registration successful. Please log in.');
        setIsLogin(true);
      }
      if (isLogin) navigate('/');
    } catch (error) {
      toast.error(isLogin ? 'Invalid credentials' : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const clayShadow = "shadow-[15px_15px_40px_rgba(0,0,0,0.08),-15px_-15px_40px_rgba(255,255,255,0.03),inset_3px_3px_10px_rgba(255,255,255,0.1),inset_-3px_-3px_10px_rgba(0,0,0,0.05)]";

  // Reusable animation variants for scroll reveals
  const fadeInUp = {
    hidden: { opacity: 0, y: 60, scale: 0.95 },
    visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.8, ease: "easeOut" } }
  };

  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden selection:bg-google-blue/20 relative">
      
      {/* Animated Soft Pastel Background Blobs */}
      <motion.div 
        animate={{ 
          x: [0, 100, -50, 0], 
          y: [0, -100, 50, 0],
          scale: [1, 1.1, 0.9, 1]
        }}
        transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
        className="fixed top-[-10%] left-[-10%] w-[50vw] h-[50vw] max-w-[600px] max-h-[600px] bg-google-blue/15 rounded-full blur-[120px] pointer-events-none z-0" 
      />
      <motion.div 
        animate={{ 
          x: [0, -100, 50, 0], 
          y: [0, 100, -50, 0],
          scale: [1, 0.9, 1.2, 1]
        }}
        transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
        className="fixed bottom-[-10%] right-[-10%] w-[50vw] h-[50vw] max-w-[600px] max-h-[600px] bg-google-red/15 rounded-full blur-[120px] pointer-events-none z-0" 
      />
      <motion.div 
        animate={{ 
          x: [0, 50, -100, 0], 
          y: [0, 50, -100, 0],
        }}
        transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
        className="fixed top-[40%] left-[30%] w-[30vw] h-[30vw] max-w-[400px] max-h-[400px] bg-google-yellow/10 rounded-full blur-[100px] pointer-events-none z-0" 
      />

      {/* Header */}
      <header className="fixed top-0 w-full p-6 flex justify-between items-center z-50 backdrop-blur-md bg-background/50 border-b border-border/30">
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-google-blue to-google-red shadow-lg">
            <ScholarIcon className="w-6 h-6 text-white absolute" />
          </div>
          <span className="font-display font-bold text-2xl tracking-tight bg-gradient-to-r from-google-blue to-google-red bg-clip-text text-transparent">ScholarForge</span>
        </div>
        <button 
          onClick={toggleTheme}
          className={`p-2 text-muted-foreground hover:text-foreground rounded-full transition-colors border border-border bg-card ${clayShadow}`}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
        >
          {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>
      </header>

      <main className="relative z-10 pt-32 pb-20 px-6 max-w-7xl mx-auto space-y-32">
        
        {/* HERO SECTION */}
        <section className="flex flex-col lg:flex-row items-center justify-between gap-16 min-h-[70vh]">
          {/* Left Text Content */}
          <motion.div 
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeInUp}
            className="flex-1 space-y-8"
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-google-green/10 border border-google-green/20 text-google-green text-sm font-semibold mb-4">
              <Zap className="w-4 h-4" />
              <span>Next-Gen AI Research Assistant</span>
            </div>
            <h1 className="text-6xl lg:text-7xl font-display font-bold leading-[1.1] tracking-tight">
              Transform <br/>
              <span className="bg-gradient-to-r from-google-blue via-google-red to-google-yellow bg-clip-text text-transparent">Literature</span> <br/>
              Into Knowledge.
            </h1>
            <p className="text-xl text-muted-foreground leading-relaxed max-w-xl">
              ScholarForge automatically builds interactive neural knowledge graphs, generates comparative reviews, and extracts core methodologies from dense PDFs.
            </p>
          </motion.div>

          {/* Right Solid Claymorphic Login Widget */}
          <motion.div 
            initial={{ opacity: 0, x: 50, scale: 0.9 }}
            whileInView={{ opacity: 1, x: 0, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, type: "spring", bounce: 0.4 }}
            className="w-full max-w-md"
          >
            <div className={`bg-card rounded-[2.5rem] p-8 border border-border ${clayShadow} relative overflow-hidden`}>
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-google-blue via-google-red to-google-yellow" />
              <h2 className="text-2xl font-bold mb-6 text-center text-foreground">{isLogin ? 'Welcome back!' : 'Create Account'}</h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                {!isLogin && (
                  <div className="space-y-1.5">
                    <input type="text" required value={name} onChange={e => setName(e.target.value)} className="w-full bg-background border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-google-blue text-foreground placeholder:text-muted-foreground shadow-inner transition-shadow" placeholder="Full Name" />
                  </div>
                )}
                <div className="space-y-1.5">
                  <input type="email" required value={email} onChange={e => setEmail(e.target.value)} className="w-full bg-background border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-google-blue text-foreground placeholder:text-muted-foreground shadow-inner transition-shadow" placeholder="Email or Username" />
                </div>
                <div className="space-y-1.5">
                  <input type="password" required value={password} onChange={e => setPassword(e.target.value)} className="w-full bg-background border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-google-blue text-foreground placeholder:text-muted-foreground shadow-inner transition-shadow" placeholder="Password" />
                </div>
                <button type="submit" disabled={loading} className="w-full bg-google-blue hover:bg-google-blue/90 hover:scale-[1.02] active:scale-[0.98] transition-all text-white font-bold rounded-xl px-4 py-3.5 mt-6 shadow-[0_4px_14px_0_rgba(66,133,244,0.39)]">
                  {loading ? <Loader2 className="w-5 h-5 animate-spin mx-auto" /> : (isLogin ? 'Login' : 'Sign Up')}
                </button>
              </form>
              <div className="mt-8 text-center pt-6 border-t border-border">
                <button onClick={() => setIsLogin(!isLogin)} className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                  {isLogin ? "Don't have an account? " : "Already have an account? "}
                  <span className="text-google-blue font-medium">{isLogin ? 'Sign up' : 'Login'}</span>
                </button>
              </div>
            </div>
          </motion.div>
        </section>

        {/* WHY SCHOLARFORGE SECTION (NEW) */}
        <motion.section 
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
          variants={fadeInUp}
          className="space-y-16"
        >
          <div className="text-center space-y-4">
            <h2 className="text-4xl lg:text-5xl font-display font-bold">Why ScholarForge?</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">Stop reading hundreds of papers manually. Let AI do the heavy lifting so you can focus on innovation.</p>
          </div>
          <div className="grid md:grid-cols-2 gap-8 lg:gap-12">
            <div className={`bg-card p-10 rounded-[2.5rem] border border-border ${clayShadow}`}>
              <Shield className="w-12 h-12 text-google-green mb-6" />
              <h3 className="text-3xl font-bold mb-4">Complete Privacy</h3>
              <p className="text-lg text-muted-foreground leading-relaxed">
                Your research is strictly confidential. All papers are processed securely in isolated environments. We don't train public models on your proprietary literature data.
              </p>
            </div>
            <div className={`bg-card p-10 rounded-[2.5rem] border border-border ${clayShadow}`}>
              <Zap className="w-12 h-12 text-google-yellow mb-6" />
              <h3 className="text-3xl font-bold mb-4">Lightning Fast Synthesis</h3>
              <p className="text-lg text-muted-foreground leading-relaxed">
                What used to take months of painful literature review now takes minutes. Select your library, click 'Analyze', and receive a structured JSON report instantly.
              </p>
            </div>
          </div>
        </motion.section>

        {/* FEATURES SECTION (WHAT WE DO) */}
        <motion.section 
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
          variants={fadeInUp}
          className="space-y-16"
        >
          <div className="text-center space-y-4">
            <h2 className="text-4xl lg:text-5xl font-display font-bold">What We Do</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">Bridging the gap between thousands of dense PDFs and actionable research insights.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard clayShadow={clayShadow} icon={<Network className="w-8 h-8 text-google-blue" />} title="Neural Knowledge" desc="Automatically extract entities and methods to build a fully interactive 3D map of your research." color="google-blue" />
            <FeatureCard clayShadow={clayShadow} icon={<BookOpen className="w-8 h-8 text-google-red" />} title="Literature Reviews" desc="Select multiple papers and our agents synthesize comprehensive comparative reviews in seconds." color="google-red" />
            <FeatureCard clayShadow={clayShadow} icon={<Layers className="w-8 h-8 text-google-yellow" />} title="Methodology Extraction" desc="Instantly identify datasets, metrics, and algorithms used across dozens of different papers." color="google-yellow" />
          </div>
        </motion.section>

        {/* HOW IT WORKS SECTION (NEW) */}
        <motion.section 
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
          variants={fadeInUp}
          className="space-y-16"
        >
          <div className="text-center space-y-4">
            <h2 className="text-4xl lg:text-5xl font-display font-bold">How It Works</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">Three simple steps to accelerate your academic journey.</p>
          </div>
          <div className="flex flex-col md:flex-row items-center justify-between gap-8 relative">
            <div className="absolute top-1/2 left-0 w-full h-1 bg-border -z-10 hidden md:block" />
            
            <StepCard number="1" title="Upload Library" desc="Drag and drop your PDFs into the secure vault." clayShadow={clayShadow} />
            <StepCard number="2" title="Deploy Agents" desc="Select an AI agent to analyze your literature." clayShadow={clayShadow} />
            <StepCard number="3" title="Gain Insights" desc="Export structured methodologies, graphs, and citations." clayShadow={clayShadow} />
          </div>
        </motion.section>

        {/* KNOWLEDGE GRAPH SECTION */}
        <motion.section 
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
          variants={fadeInUp}
          className="flex flex-col lg:flex-row-reverse items-center justify-between gap-16"
        >
          <div className="flex-1 space-y-6">
            <h2 className="text-4xl lg:text-5xl font-display font-bold">Neural Graph Interface</h2>
            <p className="text-lg text-muted-foreground leading-relaxed">
              Experience your literature like a living organism. Our neural network graph doesn't just link papers—it extracts the relationships between deep concepts. See data pulses firing across authors, datasets, and methodologies in real-time.
            </p>
            <ul className="space-y-6 pt-4">
              <li className="flex items-center gap-4">
                <div className={`w-8 h-8 rounded-xl bg-google-blue/10 flex items-center justify-center border border-google-blue/30 ${clayShadow}`}>
                  <div className="w-3 h-3 rounded-full bg-google-blue shadow-[0_0_8px_rgba(66,133,244,0.6)]" />
                </div>
                <span className="font-medium text-foreground text-lg">Deep hidden layers represent extracted concepts.</span>
              </li>
              <li className="flex items-center gap-4">
                <div className={`w-8 h-8 rounded-xl bg-google-red/10 flex items-center justify-center border border-google-red/30 ${clayShadow}`}>
                  <div className="w-3 h-3 rounded-full bg-google-red shadow-[0_0_8px_rgba(234,67,53,0.6)]" />
                </div>
                <span className="font-medium text-foreground text-lg">Rapidly firing synapses show conceptual links.</span>
              </li>
              <li className="flex items-center gap-4">
                <div className={`w-8 h-8 rounded-xl bg-google-yellow/10 flex items-center justify-center border border-google-yellow/30 ${clayShadow}`}>
                  <div className="w-3 h-3 rounded-full bg-google-yellow shadow-[0_0_8px_rgba(251,188,5,0.6)]" />
                </div>
                <span className="font-medium text-foreground text-lg">Hover over nodes to inspect neural weights.</span>
              </li>
            </ul>
          </div>
          <div className="flex-1 w-full relative group">
            <div className={`relative bg-card rounded-[3rem] p-8 border border-border ${clayShadow} transition-transform duration-500 hover:scale-[1.02]`}>
              <LandingGraph />
            </div>
          </div>
        </motion.section>

      </main>
    </div>
  );
}

function FeatureCard({ icon, title, desc, color, clayShadow }: any) {
  return (
    <motion.div 
      whileHover={{ y: -10, scale: 1.02 }}
      className={`bg-card p-8 rounded-[2.5rem] border border-border ${clayShadow} relative overflow-hidden group cursor-pointer transition-all duration-300`}
    >
      <div className={`absolute top-0 right-0 w-32 h-32 bg-${color}/10 rounded-bl-[4rem] -mr-8 -mt-8 transition-transform duration-500 group-hover:scale-150`} />
      <div className="mb-6 relative z-10 p-4 bg-background rounded-2xl inline-block shadow-inner">{icon}</div>
      <h3 className="text-2xl font-bold mb-3 relative z-10 text-foreground">{title}</h3>
      <p className="text-muted-foreground relative z-10 leading-relaxed">{desc}</p>
    </motion.div>
  );
}

function StepCard({ number, title, desc, clayShadow }: any) {
  return (
    <motion.div 
      whileHover={{ y: -5 }}
      className={`bg-card p-8 rounded-[2rem] border border-border ${clayShadow} text-center relative w-full md:w-1/3`}
    >
      <div className="w-16 h-16 rounded-full bg-gradient-to-br from-google-blue to-google-red text-white flex items-center justify-center text-2xl font-bold mx-auto mb-6 shadow-lg border-4 border-background relative z-10">
        {number}
      </div>
      <h3 className="text-xl font-bold mb-3">{title}</h3>
      <p className="text-muted-foreground">{desc}</p>
    </motion.div>
  );
}
