import React from "react";
import { Link } from "react-router-dom";
import { HelpCircle, ArrowLeft } from "lucide-react";

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col justify-center items-center relative overflow-hidden bg-slate-950 px-4">
      {/* Background radial effects */}
      <div className="absolute top-[-25%] left-[-25%] w-[700px] h-[700px] rounded-full bg-emerald-500/10 blur-[130px] pointer-events-none" />
      <div className="absolute bottom-[-25%] right-[-25%] w-[700px] h-[700px] rounded-full bg-emerald-600/5 blur-[130px] pointer-events-none" />

      <div className="w-full max-w-md text-center relative z-10">
        <div className="w-20 h-20 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-3xl flex items-center justify-center mx-auto mb-8 shadow-xl glow-emerald animate-bounce">
          <HelpCircle className="w-10 h-10" />
        </div>
        
        <h1 className="text-8xl font-black text-white tracking-widest mb-4">404</h1>
        <h2 className="text-2xl font-bold text-white mb-4">Route Not Configured</h2>
        <p className="text-slate-400 text-sm leading-relaxed mb-8">
          The resources you are attempting to locate are either deleted, relocated, or do not exist in this deployment instance.
        </p>

        <Link
          to="/"
          className="inline-flex py-3.5 px-6 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl items-center gap-2.5 transition-all shadow-lg hover:shadow-emerald-500/20"
        >
          <ArrowLeft className="w-4 h-4" /> Return to Safe Harbor
        </Link>
      </div>
    </div>
  );
};
