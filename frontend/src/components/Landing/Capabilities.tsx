import { Cpu, Mic, Workflow, Layers, Server, Blocks, Code2, Sparkles } from 'lucide-react';

export default function Capabilities() {
  const capabilities = [
    {
      title: 'Role-Aware Interaction',
      description:
        'Prevents intent pollution by isolating training namespaces per department. Vocabulary and actions specific to HR never conflict with IT Support or Admissions intents.',
      icon: Cpu,
      tag: 'Domain Isolation',
      accent: 'from-blue-500/10 text-blue-400 border-blue-500/20',
    },
    {
      title: 'Voice and Text Interaction',
      description:
        'Dual-modality conversational interface. Hands-free voice speech via Web Speech API and Google Cloud Neural2 speech synthesis, with immediate fallback to chat text.',
      icon: Mic,
      tag: 'Hands-Free Speech',
      accent: 'from-teal-500/10 text-[#2FD1C5] border-[#2FD1C5]/20',
    },
    {
      title: 'Multi-Turn Workflows',
      description:
        'Guides users step-by-step through slot collection, partial forms, and explicit confirmation safeguards before firing destructive or record-altering operations.',
      icon: Workflow,
      tag: 'Stateful Forms',
      accent: 'from-purple-500/10 text-purple-400 border-purple-500/20',
    },
    {
      title: 'HR, IT Support & Admissions Packs',
      description:
        'Pre-configured role modules handling high-volume operational queries: leave balances and requests, IT incident ticketing and password resets, and applicant tracking.',
      icon: Layers,
      tag: 'Out-of-the-Box',
      accent: 'from-indigo-500/10 text-[#8B82FF] border-[#6C63FF]/20',
    },
    {
      title: 'Enterprise Service Adapters',
      description:
        'Decoupled integration adapter layer shielding conversational models from backend implementations. Transition from mock services to production HRMS/ITSM with zero core rewrites.',
      icon: Server,
      tag: 'Swappable Backends',
      accent: 'from-amber-500/10 text-amber-300 border-amber-500/20',
    },
    {
      title: 'Extensible Architecture',
      description:
        'Add new organizational roles (Finance, Facilities, Student Affairs) purely through declarative configuration data in under 1 developer-day without core redeployments.',
      icon: Blocks,
      tag: 'Zero Redeploy',
      accent: 'from-rose-500/10 text-rose-400 border-rose-500/20',
    },
    {
      title: 'Open-Source Development',
      description:
        'Built openly under the Apache License 2.0 with reproducible Docker Compose setups, comprehensive test suites, and strict architectural documentation.',
      icon: Code2,
      tag: 'Apache-2.0',
      accent: 'from-emerald-500/10 text-emerald-400 border-emerald-500/20',
    },
  ];

  return (
    <section id="capabilities" className="py-24 bg-[#0A0D16] border-y border-white/[0.06] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.08] text-xs font-mono uppercase tracking-widest text-[#2FD1C5] mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Core Capabilities</span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight mb-5">
            Key Capabilities
          </h2>
          <p className="text-base sm:text-lg text-zinc-400 leading-relaxed max-w-2xl mx-auto">
            Architected specifically for organizational reliability, departmental independence, and rapid customization.
          </p>
        </div>

        {/* Clean Capability Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {capabilities.map((cap) => {
            const Icon = cap.icon;
            return (
              <div
                key={cap.title}
                className="p-7 rounded-2xl bg-[#0E111C]/90 border border-white/[0.08] hover:border-white/[0.18] transition-all hover:-translate-y-0.5 hover:shadow-[0_8px_30px_rgba(0,0,0,0.5)] flex flex-col justify-between group backdrop-blur-md relative overflow-hidden"
              >
                <div>
                  <div className="flex items-center justify-between mb-5">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${cap.accent} border flex items-center justify-center group-hover:scale-105 transition-transform`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-zinc-400">
                      {cap.tag}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2.5 tracking-tight">
                    {cap.title}
                  </h3>
                  <p className="text-sm text-zinc-300 leading-relaxed font-normal">
                    {cap.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
