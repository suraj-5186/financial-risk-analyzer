import React from "react";
import { Link } from "react-router-dom";
import { Shield, TrendingUp, Cpu, Target, ArrowRight, Wallet, Activity } from "lucide-react";

export const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden">
      {/* Background blobs for premium glassmorphism effect */}
      <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] rounded-full bg-emerald-500/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-emerald-600/5 blur-[120px] pointer-events-none" />

      {/* Navbar */}
      <nav className="sticky top-0 z-50 w-full glass-panel border-b border-white/5 py-4 px-6 md:px-12 flex justify-between items-center transition-all duration-300">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center glow-emerald">
            <Activity className="w-6 h-6 text-emerald-400" />
          </div>
          <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-100 to-emerald-400 bg-clip-text text-transparent">
            FinRisk AI
          </span>
        </div>

        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-300">
          <a href="#features" className="hover:text-emerald-400 transition-colors">Features</a>
          <a href="#about" className="hover:text-emerald-400 transition-colors">About Project</a>
        </div>

        <div className="flex items-center gap-4">
          <Link to="/login" className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors">
            Login
          </Link>
          <Link to="/signup" className="px-5 py-2.5 text-sm font-medium bg-emerald-500 text-slate-950 rounded-xl hover:bg-emerald-400 hover:scale-[1.02] active:scale-[0.98] transition-all glow-emerald">
            Register
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="flex-1 max-w-7xl mx-auto px-6 md:px-12 pt-20 pb-16 flex flex-col items-center text-center relative z-10">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-8 animate-pulse">
          <Shield className="w-3.5 h-3.5" /> Next-Gen Behavior & Risk Modeler
        </div>
        
        <h1 className="text-4xl md:text-7xl font-extrabold tracking-tight max-w-4xl leading-[1.1] mb-6">
          Analyze Your <span className="bg-gradient-to-r from-emerald-400 to-teal-300 bg-clip-text text-transparent glow-text-emerald">Financial Behavior</span> & Risk in Real-Time
        </h1>
        
        <p className="text-slate-400 text-base md:text-xl max-w-2xl leading-relaxed mb-12">
          Leverage our intelligent scoring models to discover risk variables, optimize monthly budgets, track savings goals, and unlock tailor-made AI insights.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <Link to="/dashboard" className="group px-8 py-4 bg-emerald-500 text-slate-950 font-semibold rounded-2xl flex items-center gap-3 hover:bg-emerald-400 transition-all duration-300 hover:shadow-[0_0_30px_rgba(16,185,129,0.4)] hover:scale-[1.03] active:scale-[0.97]">
            Start Analyzing <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </Link>
          <a href="#features" className="px-8 py-4 glass-panel border border-white/10 text-slate-300 font-semibold rounded-2xl hover:bg-white/5 transition-all">
            Explore Features
          </a>
        </div>

        {/* Dashboard Graphic Mockup */}
        <div className="mt-20 w-full max-w-5xl rounded-2xl glass-panel border border-white/10 p-4 shadow-2xl relative">
          <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent opacity-60 rounded-2xl" />
          <div className="h-11 rounded-t-xl bg-slate-900/60 border-b border-white/5 flex items-center px-4 gap-2">
            <span className="w-3 h-3 rounded-full bg-red-500/50" />
            <span className="w-3 h-3 rounded-full bg-yellow-500/50" />
            <span className="w-3 h-3 rounded-full bg-emerald-500/50" />
            <span className="text-xs text-slate-500 ml-4 font-mono">dashboard.finrisk-ai.com</span>
          </div>
          <div className="bg-slate-950/80 p-6 md:p-8 rounded-b-xl grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
            <div className="glass-panel p-6 rounded-xl border border-white/5">
              <div className="text-slate-400 text-xs uppercase tracking-wider mb-2">Financial Health Score</div>
              <div className="text-4xl font-extrabold text-emerald-400">84/100</div>
              <div className="mt-4 text-xs text-slate-500">Above average. Your savings rate is optimal.</div>
            </div>
            <div className="glass-panel p-6 rounded-xl border border-white/5">
              <div className="text-slate-400 text-xs uppercase tracking-wider mb-2">Active Budget</div>
              <div className="text-4xl font-extrabold text-white">₹38,200 <span className="text-sm font-medium text-slate-400">/ ₹50,000</span></div>
              <div className="mt-4 w-full bg-slate-800 rounded-full h-1.5">
                <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: '76%' }}></div>
              </div>
            </div>
            <div className="glass-panel p-6 rounded-xl border border-white/5">
              <div className="text-slate-400 text-xs uppercase tracking-wider mb-2">AI Alert</div>
              <div className="text-sm font-medium text-amber-400">Food expenses spiked 18%</div>
              <div className="mt-4 text-xs text-slate-400">You are likely to exceed Food budget in 6 days.</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24 px-6 md:px-12 max-w-7xl mx-auto w-full relative z-10 border-t border-white/5">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-4">Powerful Features Built For Growth</h2>
          <p className="text-slate-400 text-base md:text-lg">
            Understand spending habits, calculate behavior vulnerability, and receive automated coaching.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          <div className="glass-panel p-8 rounded-2xl border border-white/5 hover:border-emerald-500/30 group hover:scale-[1.02] transition-all duration-300">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center mb-6 group-hover:bg-emerald-500/20 transition-all">
              <TrendingUp className="w-6 h-6 text-emerald-400" />
            </div>
            <h3 className="text-xl font-semibold mb-3">Health Scoring</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Consolidates savings rate, debt ratio, and emergency funds into a single, actionable score.
            </p>
          </div>

          <div className="glass-panel p-8 rounded-2xl border border-white/5 hover:border-emerald-500/30 group hover:scale-[1.02] transition-all duration-300">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center mb-6 group-hover:bg-emerald-500/20 transition-all">
              <Cpu className="w-6 h-6 text-emerald-400" />
            </div>
            <h3 className="text-xl font-semibold mb-3">AI Insights</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Monitors transactions and outputs warning parameters dynamically when anomalies or spikes occur.
            </p>
          </div>

          <div className="glass-panel p-8 rounded-2xl border border-white/5 hover:border-emerald-500/30 group hover:scale-[1.02] transition-all duration-300">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center mb-6 group-hover:bg-emerald-500/20 transition-all">
              <Wallet className="w-6 h-6 text-emerald-400" />
            </div>
            <h3 className="text-xl font-semibold mb-3">Budget Planner</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Configure and modify custom category limits, displaying safe usage zones in high-contrast visualizer.
            </p>
          </div>

          <div className="glass-panel p-8 rounded-2xl border border-white/5 hover:border-emerald-500/30 group hover:scale-[1.02] transition-all duration-300">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center mb-6 group-hover:bg-emerald-500/20 transition-all">
              <Target className="w-6 h-6 text-emerald-400" />
            </div>
            <h3 className="text-xl font-semibold mb-3">Goal Tracker</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Establish savings targets, add incremental deposits, and review timeline indicators.
            </p>
          </div>
        </div>
      </section>

      {/* About Project Section */}
      <section id="about" className="py-20 px-6 md:px-12 max-w-7xl mx-auto w-full relative z-10 border-t border-white/5">
        <div className="glass-panel rounded-3xl p-8 md:p-12 border border-white/10 bg-slate-900/40 relative overflow-hidden">
          <div className="absolute right-0 top-0 w-80 h-80 rounded-full bg-emerald-500/5 blur-3xl pointer-events-none" />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <span className="text-emerald-400 text-sm font-semibold tracking-wider uppercase mb-3 block">
                Technical Stack & Architecture
              </span>
              <h2 className="text-3xl md:text-4xl font-bold mb-6">
                Engineered for High Performance, Security & Modularity
              </h2>
              <p className="text-slate-400 text-sm md:text-base leading-relaxed mb-6">
                This project represents a full-stack engineering solution. The backend utilizes FastAPI's speed and concurrency with SQLAlchemy database sessions. The frontend compiles standard React 19 and Vite with TypeScript, styled natively through a Tailwind configuration.
              </p>
              <ul className="space-y-3.5 text-slate-300 text-sm font-medium">
                <li className="flex items-center gap-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  FastAPI backend with structured JWT Access & Refresh cycles.
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  Type-safe input processing via Zod and Pydantic schemas.
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  Dynamic financial health calculations & metrics visualization.
                </li>
              </ul>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="glass-panel p-6 rounded-2xl border border-white/5 text-center">
                <div className="text-2xl font-bold text-white mb-1">FastAPI</div>
                <div className="text-slate-500 text-xs uppercase font-semibold">API Layer</div>
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-white/5 text-center">
                <div className="text-2xl font-bold text-white mb-1">React 19</div>
                <div className="text-slate-500 text-xs uppercase font-semibold">Frontend</div>
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-white/5 text-center">
                <div className="text-2xl font-bold text-white mb-1">Tailwind</div>
                <div className="text-slate-500 text-xs uppercase font-semibold">CSS Styles</div>
              </div>
              <div className="glass-panel p-6 rounded-2xl border border-white/5 text-center">
                <div className="text-2xl font-bold text-white mb-1">JWT</div>
                <div className="text-slate-500 text-xs uppercase font-semibold">Security</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="w-full py-12 px-6 md:px-12 border-t border-white/5 relative z-10 glass-panel mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
              <Activity className="w-5 h-5 text-emerald-400" />
            </div>
            <span className="text-lg font-bold tracking-tight text-white">FinRisk AI</span>
          </div>
          <p className="text-slate-500 text-xs md:text-sm">
            &copy; {new Date().getFullYear()} Financial Behavior and Risk Analyzer. All rights reserved.
          </p>
          <div className="flex gap-6 text-sm text-slate-400 font-medium">
            <a href="#features" className="hover:text-emerald-400 transition-colors">Features</a>
            <a href="#about" className="hover:text-emerald-400 transition-colors">About</a>
          </div>
        </div>
      </footer>
    </div>
  );
};
