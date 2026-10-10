import { Mic, Layers, Cpu, Blocks, Zap, ArrowRight, ShieldCheck } from 'lucide-react';

export default function ProjectOverview() {
  return (
    <section id="overview" className="py-24 bg-[#0A0D16] border-y border-white/[0.06] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.08] text-xs font-mono uppercase tracking-widest text-[#2FD1C5] mb-4">
            <Zap className="w-3.5 h-3.5" />
            <span>Project Overview</span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight mb-5">
            A Shared Conversational Brain Without the Silos
          </h2>
          <p className="text-base sm:text-lg text-zinc-400 leading-relaxed max-w-2xl mx-auto">
            Organizations face hundreds of repetitive, transactional queries daily. VARIO solves this by coupling a shared
            dialogue routing engine with pluggable departmental packs and swappable backend adapters.
          </p>
        </div>

        {/* Asymmetric Bento Architecture Showcase */}
        <div className="space-y-6">
          {/* Top Feature Card: What VARIO Is */}
          <div className="p-8 sm:p-10 rounded-2xl bg-[#0E111C]/90 border border-white/[0.08] hover:border-white/[0.16] transition-all shadow-[0_8px_32px_rgba(0,0,0,0.5)] backdrop-blur-md relative overflow-hidden">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
              <div className="lg:col-span-7">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-[#2FD1C5]/10 border border-[#2FD1C5]/20 flex items-center justify-center text-[#2FD1C5]">
                    <Cpu className="w-5 h-5" />
                  </div>
                  <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-zinc-400">
                    Core Framework
                  </span>
                </div>
                <h3 className="text-2xl font-bold text-white mb-3 tracking-tight">
                  What VARIO Is
                </h3>
                <p className="text-sm sm:text-base text-zinc-300 leading-relaxed font-normal mb-6">
                  A Role-Specific Voice Assistant Framework designed for organizations and institutions. VARIO unifies conversational voice and text through a reusable, central orchestration engine, eliminating the need to build and maintain separate, siloed chatbots for each department.
                </p>
                <div className="grid grid-cols-3 gap-3 font-mono text-xs text-zinc-400">
                  <div className="p-3 rounded-xl bg-black/40 border border-white/[0.06]">
                    <div className="text-[11px] text-zinc-400 mb-1">Architecture</div>
                    <div className="text-white font-semibold">Modular Core</div>
                  </div>
                  <div className="p-3 rounded-xl bg-black/40 border border-white/[0.06]">
                    <div className="text-[11px] text-zinc-400 mb-1">Engine Stack</div>
                    <div className="text-white font-semibold">FastAPI + Rasa</div>
                  </div>
                  <div className="p-3 rounded-xl bg-black/40 border border-white/[0.06]">
                    <div className="text-[11px] text-zinc-400 mb-1">Deployment</div>
                    <div className="text-emerald-400 font-semibold">Docker Ready</div>
                  </div>
                </div>
              </div>

              {/* Visual Blueprint Comparison */}
              <div className="lg:col-span-5 p-5 rounded-xl bg-black/50 border border-white/[0.07] font-mono text-xs space-y-3.5">
                <div className="flex items-center justify-between pb-2 border-b border-white/[0.08] text-zinc-400 text-[11px]">
                  <span>TRADITIONAL SILOED MODEL</span>
                  <span className="text-rose-400">High Drift &amp; Redundancy</span>
                </div>
                <div className="flex items-center justify-between text-zinc-400 text-[11px] opacity-75">
                  <span>HR Bot · IT Bot · Admission Bot</span>
                  <span className="line-through">3x Duplicated Engines</span>
                </div>

                <div className="pt-2 flex items-center justify-between pb-2 border-b border-white/[0.08] text-[#2FD1C5] text-[11px] font-semibold">
                  <span>VARIO UNIFIED PARADIGM</span>
                  <span className="text-emerald-400">Single Central Brain</span>
                </div>
                <div className="space-y-2 text-zinc-300">
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-400">Core Runtime</span>
                    <span className="text-white">FastAPI Gateway + Rasa Core</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-400">Orchestration</span>
                    <span className="text-teal-300">Context &amp; Role Aware</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-400">Isolation Policy</span>
                    <span className="text-indigo-300">100% Zero Namespace Drift</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom 3-Card Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Card 2: Dual Voice & Text */}
            <div className="p-7 rounded-2xl bg-[#0E111C]/90 border border-white/[0.08] hover:border-white/[0.16] transition-all flex flex-col justify-between backdrop-blur-md">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-[#2FD1C5]">
                    <Mic className="w-5 h-5" />
                  </div>
                  <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-zinc-400">
                    Multimodal
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white mb-2 tracking-tight">
                  Dual Voice &amp; Text Interaction
                </h3>
                <p className="text-sm text-zinc-300 leading-relaxed font-normal mb-5">
                  Built for hands-free and multimodal workflows. Uses browser-native Web Speech API for low-latency Speech-to-Text (STT) and Google Cloud Text-to-Speech (Neural2) for audio responses, with instant, seamless fallback to text chat.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-black/40 border border-white/[0.06] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#2FD1C5]" />
                  <span className="text-xs font-mono text-zinc-300">Web Speech STT</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-1 bg-[#2FD1C5] rounded-full animate-audio-1 h-3" />
                  <span className="w-1 bg-[#2FD1C5] rounded-full animate-audio-2 h-5" />
                  <span className="w-1 bg-[#2FD1C5] rounded-full animate-audio-3 h-2" />
                  <span className="w-1 bg-[#2FD1C5] rounded-full animate-audio-4 h-4" />
                </div>
                <span className="text-[11px] font-mono text-zinc-400">Neural2 TTS</span>
              </div>
            </div>

            {/* Card 3: Role-Aware Enterprise Orchestration */}
            <div className="p-7 rounded-2xl bg-[#0E111C]/90 border border-white/[0.08] hover:border-white/[0.16] transition-all flex flex-col justify-between backdrop-blur-md">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-[#8B82FF]">
                    <Layers className="w-5 h-5" />
                  </div>
                  <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-zinc-400">
                    Context-Aware
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white mb-2 tracking-tight">
                  Role-Aware Enterprise Orchestration
                </h3>
                <p className="text-sm text-zinc-300 leading-relaxed font-normal mb-5">
                  Different departments have distinct vocabularies, slots, and validation policies. Role-aware orchestration isolates intent models so HR, IT, and Admissions never cross-contaminate each other while maintaining state across multi-turn workflows.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-black/40 border border-white/[0.06] flex items-center justify-around font-mono text-xs">
                <span className="px-2 py-1 rounded bg-[#2FD1C5]/10 border border-[#2FD1C5]/20 text-[#2FD1C5]">
                  HR Space
                </span>
                <span className="text-zinc-600">|</span>
                <span className="px-2 py-1 rounded bg-[#6C63FF]/15 border border-[#6C63FF]/25 text-[#8B82FF]">
                  IT Support
                </span>
                <span className="text-zinc-600">|</span>
                <span className="px-2 py-1 rounded bg-amber-400/10 border border-amber-400/20 text-amber-300">
                  Admissions
                </span>
              </div>
            </div>

            {/* Card 4: Modular & Extensible by Design */}
            <div className="p-7 rounded-2xl bg-[#0E111C]/90 border border-white/[0.08] hover:border-white/[0.16] transition-all flex flex-col justify-between backdrop-blur-md">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                    <Blocks className="w-5 h-5" />
                  </div>
                  <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-zinc-400">
                    Config-Driven
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white mb-2 tracking-tight">
                  Modular &amp; Extensible by Design
                </h3>
                <p className="text-sm text-zinc-300 leading-relaxed font-normal mb-5">
                  Easily extensible for new organizational entities (Finance, Facilities, Student Affairs). New role packs can be registered via configuration data in under one developer-day without touching or redeploying core engine code.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-black/40 border border-white/[0.06] font-mono text-[11px] text-zinc-400 leading-relaxed">
                <div><span className="text-teal-400">role_pack</span>: &quot;finance_v1&quot;</div>
                <div><span className="text-[#8B82FF]">adapter</span>: &quot;ERPAdapter.get_invoice&quot;</div>
                <div><span className="text-emerald-400">status</span>: &quot;registered_active&quot;</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
