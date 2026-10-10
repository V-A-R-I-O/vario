import { Layout, Shield, Cpu, Layers, Server, Terminal, Database, CheckCircle2, Network } from 'lucide-react';

export default function Architecture() {
  const layers = [
    {
      name: 'Frontend Client',
      role: 'Next.js 14 · React · Tailwind CSS',
      description:
        'Interactive web client supporting text chat, hands-free talk mode via Web Speech API, and a role-scoped administrative console.',
      icon: Layout,
      color: 'text-teal-400 border-teal-500/20 bg-teal-500/5',
      badge: 'Browser Native',
      protocol: 'Web Speech API · SSE',
    },
    {
      name: 'API Gateway',
      role: 'FastAPI Single Entrypoint',
      description:
        'Validates identity tokens, enforces client rate limits, and standardizes all responses into an auditable {status, data, error} envelope.',
      icon: Shield,
      color: 'text-purple-400 border-purple-500/20 bg-purple-500/5',
      badge: 'Auth & Envelope',
      protocol: 'REST / HTTPS · JWT',
    },
    {
      name: 'Core Orchestration',
      role: 'Session Manager · Dialogue Router · Renderer',
      description:
        'Coordinates state across turns. Restores session form slots from Postgres, routes utterances to the target role, and renders randomized template variants.',
      icon: Cpu,
      color: 'text-blue-400 border-blue-500/20 bg-blue-500/5',
      badge: 'Multi-Turn Core',
      protocol: 'Stateful Routing Machine',
    },
    {
      name: 'Role Packs',
      role: '3x Isolated Rasa Open Source Instances',
      description:
        'Dedicated departmental NLU classifiers for HR, IT Support, and Admissions, eliminating vocabulary overlap and model drift.',
      icon: Layers,
      color: 'text-[#2FD1C5] border-[#2FD1C5]/20 bg-[#2FD1C5]/5',
      badge: 'Zero Drift',
      protocol: 'Isolated Rasa NLU Port',
    },
    {
      name: 'Integration Adapters',
      role: 'AuthAdapter · HRMS · ITSM · Admissions',
      description:
        'Standardized translation layer isolating core dialogue logic from enterprise backend schema nuances.',
      icon: Server,
      color: 'text-amber-300 border-amber-500/20 bg-amber-500/5',
      badge: 'Decoupled',
      protocol: 'Python RPC Adapters',
    },
    {
      name: 'Mock Enterprise Services',
      role: 'Isolated FastAPI Microservices',
      description:
        'Self-contained mock systems replicating production HRMS leave engines, ITSM ticket workflows, and student information systems.',
      icon: Terminal,
      color: 'text-rose-400 border-rose-500/20 bg-rose-500/5',
      badge: 'High Fidelity',
      protocol: 'Internal REST Endpoints',
    },
    {
      name: 'PostgreSQL Database',
      role: 'Authoritative Single Source of Truth',
      description:
        'Durable persistence for conversations, session slots, intent configurations, template variants, and append-only audit logs.',
      icon: Database,
      color: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5',
      badge: 'ACID Audit Log',
      protocol: 'asyncpg · Strict Schemas',
    },
  ];

  return (
    <section id="architecture" className="py-24 bg-[#080B14] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.08] text-xs font-mono uppercase tracking-widest text-[#8B82FF] mb-4">
            <Network className="w-3.5 h-3.5" />
            <span>System Design</span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight mb-5">
            Architecture Overview
          </h2>
          <p className="text-base sm:text-lg text-zinc-400 leading-relaxed max-w-2xl mx-auto">
            A modular, multi-tier system engineered with clear boundaries between user presentation, dialogue orchestration, and backend enterprise integrations.
          </p>
        </div>

        {/* Structural Layer Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto mb-12">
          {layers.map((layer, index) => {
            const Icon = layer.icon;
            return (
              <div
                key={layer.name}
                className="p-7 rounded-2xl bg-[#0E111C]/90 border border-white/[0.08] hover:border-white/[0.18] transition-all hover:shadow-[0_8px_32px_rgba(0,0,0,0.5)] flex flex-col justify-between group backdrop-blur-md relative overflow-hidden"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className={`p-2.5 rounded-xl border ${layer.color} flex items-center justify-center group-hover:scale-105 transition-transform`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.06] text-zinc-400">
                        {layer.badge}
                      </span>
                      <span className="text-xs font-mono text-zinc-400">LAYER 0{index + 1}</span>
                    </div>
                  </div>
                  <h3 className="text-lg font-bold text-white mb-1 tracking-tight">
                    {layer.name}
                  </h3>
                  <p className="text-xs font-mono text-zinc-400 mb-3">{layer.role}</p>
                  <p className="text-sm text-zinc-300 leading-relaxed font-normal mb-4">{layer.description}</p>
                </div>

                <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] font-mono text-zinc-400">
                  <span>Interface:</span>
                  <span className="text-zinc-300">{layer.protocol}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Security & Auditability Callout */}
        <div className="max-w-4xl mx-auto p-6 rounded-2xl bg-[#0E111C]/90 border border-white/[0.08] flex items-start gap-3.5 shadow-lg backdrop-blur-md">
          <CheckCircle2 className="w-5 h-5 text-[#2FD1C5] flex-shrink-0 mt-0.5" />
          <p className="text-xs sm:text-sm text-zinc-300 leading-relaxed">
            <span className="font-semibold text-white">Enterprise Privacy &amp; Decoupling:</span> The architecture preserves user privacy by maintaining strict boundary contracts. Session data is persisted with configurable time-to-live (TTL), administrative actions require scoped credentials, and destructive record changes always require explicit user confirmation.
          </p>
        </div>
      </div>
    </section>
  );
}
