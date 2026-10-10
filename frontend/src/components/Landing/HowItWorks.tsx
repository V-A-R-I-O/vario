import { Users, Mic, Sparkles, Cpu, Layers, Server, MessageSquare, ChevronRight, Activity, ArrowDown } from 'lucide-react';

export default function HowItWorks() {
  const steps = [
    {
      step: '01',
      title: 'User',
      subtitle: 'Employee / Student / Applicant',
      description: 'The user begins a session via web browser, expressing a transactional query or workflow intent.',
      icon: Users,
      color: 'from-blue-500/15 text-blue-400 border-blue-500/25',
      telemetry: 'Web Client · Browser Session',
    },
    {
      step: '02',
      title: 'Voice / Text',
      subtitle: 'Multimodal Input Layer',
      description: 'Web Speech API transcribes spoken speech into text; typed text passes through with instant latency.',
      icon: Mic,
      color: 'from-teal-500/15 text-[#2FD1C5] border-teal-500/25',
      telemetry: 'Web Speech STT · Instant Stream',
    },
    {
      step: '03',
      title: 'Intent + Context',
      subtitle: 'Gateway & Session Manager',
      description: 'FastAPI Gateway validates auth/envelope; Session Manager restores active form, step, and slots from PostgreSQL.',
      icon: Sparkles,
      color: 'from-purple-500/15 text-purple-400 border-purple-500/25',
      telemetry: 'JWT Envelope · DB Slot Restore',
    },
    {
      step: '04',
      title: 'Role-aware Orchestration',
      subtitle: 'Core Dialogue Router',
      description: 'The Dialogue Router evaluates conversation role context and routes the utterance to the designated department engine.',
      icon: Cpu,
      color: 'from-cyan-500/15 text-cyan-400 border-cyan-500/25',
      telemetry: 'Zero Pollution Routing · Context State',
    },
    {
      step: '05',
      title: 'Role Pack',
      subtitle: 'Isolated Rasa NLU Runtime',
      description: 'Domain-isolated Rasa instance extracts entities, classifies intent, and manages multi-turn slot policies.',
      icon: Layers,
      color: 'from-indigo-500/15 text-[#8B82FF] border-indigo-500/25',
      telemetry: 'Dedicated Namespace · Slot Filling',
    },
    {
      step: '06',
      title: 'Enterprise Service',
      subtitle: 'Integration Adapter Layer',
      description: 'Standardized adapter executes the transactional operation against mock or production enterprise backends.',
      icon: Server,
      color: 'from-amber-500/15 text-amber-300 border-amber-500/25',
      telemetry: 'HRMS / ITSM / Admissions Adapters',
    },
    {
      step: '07',
      title: 'Response',
      subtitle: 'Renderer & Neural TTS',
      description: 'Response Renderer selects a paraphrased template variant, Google Cloud TTS synthesizes audio, and response returns.',
      icon: MessageSquare,
      color: 'from-emerald-500/15 text-emerald-400 border-emerald-500/25',
      telemetry: 'Neural2 Audio + Visual Card Payload',
    },
  ];

  return (
    <section id="how-it-works" className="py-24 bg-[#080B14] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.08] text-xs font-mono uppercase tracking-widest text-[#8B82FF] mb-4">
            <Activity className="w-3.5 h-3.5" />
            <span>System Workflow</span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight mb-5">
            How VARIO Works
          </h2>
          <p className="text-base sm:text-lg text-zinc-400 leading-relaxed max-w-2xl mx-auto">
            From the initial spoken sentence to enterprise fulfillment: a deterministic, role-isolated conversational loop.
          </p>
        </div>

        {/* Visual Stepped Signal Pipeline */}
        <div className="relative max-w-4xl mx-auto">
          {/* Subtle vertical connector line */}
          <div className="absolute left-6 sm:left-9 top-8 bottom-8 w-[1px] bg-gradient-to-b from-[#2FD1C5]/40 via-[#6C63FF]/30 to-emerald-400/40 -z-0" />

          <div className="space-y-4 relative z-10">
            {steps.map((item, idx) => {
              const Icon = item.icon;
              const isLast = idx === steps.length - 1;
              return (
                <div
                  key={item.step}
                  className="relative flex items-start gap-4 sm:gap-6 bg-[#0E111C]/90 border border-white/[0.08] rounded-2xl p-5 sm:p-6 hover:border-white/[0.16] transition-all shadow-[0_4px_24px_rgba(0,0,0,0.4)] group backdrop-blur-md"
                >
                  {/* Step Node Icon Badge */}
                  <div
                    className={`w-12 h-12 sm:w-14 sm:h-14 rounded-xl bg-gradient-to-br ${item.color} border flex-shrink-0 flex items-center justify-center font-mono font-bold text-sm sm:text-base group-hover:scale-105 transition-transform relative`}
                  >
                    <Icon className="w-5 h-5 sm:w-6 sm:h-6" />
                    <span className="absolute -top-1.5 -right-1.5 px-1.5 py-0.5 rounded-full bg-black/80 border border-white/[0.1] text-[9px] font-mono text-zinc-400">
                      {item.step}
                    </span>
                  </div>

                  {/* Step Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight">
                        {item.title}
                      </h3>
                      <ChevronRight className="w-3.5 h-3.5 text-zinc-600 hidden sm:inline" />
                      <span className="text-xs px-2.5 py-0.5 rounded-md bg-white/[0.04] text-zinc-300 font-medium border border-white/[0.06]">
                        {item.subtitle}
                      </span>
                      <span className="ml-auto text-[11px] font-mono text-zinc-400 bg-black/40 px-2 py-0.5 rounded border border-white/[0.05] hidden md:inline">
                        {item.telemetry}
                      </span>
                    </div>
                    <p className="text-sm sm:text-base text-zinc-300 leading-relaxed font-normal">
                      {item.description}
                    </p>
                  </div>

                  {/* Direction Arrow */}
                  {!isLast && (
                    <div className="hidden lg:flex items-center text-zinc-600 group-hover:text-zinc-400 transition-colors pt-2">
                      <ArrowDown className="w-4 h-4" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
