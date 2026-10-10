'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowRight, ExternalLink, Mic, MessageSquare, Cpu, Layers, Sparkles, BookOpen, Volume2, Check, Copy, Terminal } from 'lucide-react';

interface SimulationExample {
  id: string;
  role: string;
  badgeColor: string;
  input: string;
  intent: string;
  confidence: string;
  adapter: string;
  response: string;
  ttsVoice: string;
}

const EXAMPLES: SimulationExample[] = [
  {
    id: 'hr',
    role: 'HR Self-Service',
    badgeColor: 'text-[#2FD1C5] bg-[#2FD1C5]/10 border-[#2FD1C5]/30',
    input: '"What is my remaining paid annual leave balance?"',
    intent: 'hr_leave_balance',
    confidence: '98.6%',
    adapter: 'HRMSAdapter.get_leave_balance(user_id="EMP-1042")',
    response: 'You currently have 14 days of annual leave and 4 days of casual leave remaining for this cycle.',
    ttsVoice: 'Google Cloud TTS · Neural2 (en-US-Neural2-F)',
  },
  {
    id: 'it',
    role: 'IT Support',
    badgeColor: 'text-[#8B82FF] bg-[#6C63FF]/15 border-[#6C63FF]/30',
    input: '"I cannot log in to the VPN and need a password reset."',
    intent: 'it_password_reset',
    confidence: '97.2%',
    adapter: 'ITSMAdapter.initiate_password_reset(category="Identity")',
    response: 'I can help reset your password. I have verified your session and sent a secure verification code to your registered device.',
    ttsVoice: 'Google Cloud TTS · Neural2 (en-US-Neural2-J)',
  },
  {
    id: 'adm',
    role: 'Admissions',
    badgeColor: 'text-amber-300 bg-amber-400/10 border-amber-400/30',
    input: '"Check application status for application ID #ADM-8291"',
    intent: 'adm_application_status',
    confidence: '99.1%',
    adapter: 'AdmissionsAdapter.get_status(app_id="ADM-8291")',
    response: 'Application #ADM-8291 for M.Tech Computer Science is currently Under Department Review. All mandatory documents have been verified.',
    ttsVoice: 'Google Cloud TTS · Neural2 (en-US-Neural2-C)',
  },
];

export default function Hero() {
  const [selectedExample, setSelectedExample] = useState<SimulationExample>(EXAMPLES[0]);
  const [copied, setCopied] = useState(false);

  const handleCopyAdapter = () => {
    navigator.clipboard?.writeText(selectedExample.adapter);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="relative overflow-hidden pt-12 pb-20 md:pt-20 md:pb-32">
      {/* Subtle top ambient glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[400px] bg-[radial-gradient(ellipse_at_top,rgba(47,209,197,0.08)_0%,rgba(108,99,255,0.05)_45%,transparent_70%)] pointer-events-none -z-10" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto">
          {/* Announcement Badge Pill */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.08] text-xs font-medium text-zinc-300 mb-6 backdrop-blur-md shadow-sm hover:border-white/[0.16] transition-colors">
            <span className="flex h-2 w-2 rounded-full bg-emerald-400" />
            <span className="font-semibold text-white">Voice Adaptive Role &amp; Intent Orchestrator</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.06] text-zinc-400">v1.0-prod</span>
          </div>

          {/* Main Hero Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white tracking-tight leading-[1.12] mb-6">
            One Voice Assistant Brain.{' '}
            <span className="bg-gradient-to-r from-[#2FD1C5] via-teal-200 to-[#8B82FF] bg-clip-text text-transparent">
              Pluggable Roles
            </span>{' '}
            for Every Department.
          </h1>

          {/* Value Proposition */}
          <p className="text-base sm:text-lg lg:text-xl text-zinc-300 mb-8 leading-relaxed max-w-2xl mx-auto font-normal">
            Eliminate repetitive transactional queries across <span className="text-white font-medium">HR</span>,{' '}
            <span className="text-white font-medium">IT Support</span>, and{' '}
            <span className="text-white font-medium">Admissions</span>. VARIO unifies browser-native voice and text with a reusable,
            role-adaptive orchestration core and modular backend adapters.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3.5 mb-12">
            {/* Primary CTA */}
            <Link
              href="/login"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-gradient-to-r from-[#2FD1C5] to-[#6C63FF] text-[#0C1220] font-bold px-7 py-3.5 rounded-xl hover:opacity-95 active:scale-[0.98] transition-all text-sm sm:text-base shadow-[0_2px_16px_rgba(47,209,197,0.3)] hover:shadow-[0_4px_24px_rgba(47,209,197,0.45)]"
            >
              <span>Enter Application</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            {/* Secondary CTA: GitHub */}
            <a
              href="https://github.com/V-A-R-I-O/vario"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-white/[0.03] text-zinc-200 font-semibold px-6 py-3.5 rounded-xl border border-white/[0.09] hover:bg-white/[0.07] hover:border-white/[0.18] transition-all text-sm sm:text-base backdrop-blur-md"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                />
              </svg>
              <span>View on GitHub</span>
              <ExternalLink className="w-3.5 h-3.5 text-zinc-400" />
            </a>

            {/* Documentation Quick Link */}
            <a
              href="#architecture"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 text-zinc-400 hover:text-white font-medium px-4 py-3.5 rounded-xl hover:bg-white/[0.05] transition-colors text-sm sm:text-base"
            >
              <BookOpen className="w-4 h-4 text-[#2FD1C5]" />
              <span>Architecture Docs</span>
            </a>
          </div>

          {/* Metric Ribbon */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-2xl mx-auto mb-14 text-left">
            <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] backdrop-blur-sm">
              <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider">Latency</div>
              <div className="text-base sm:text-lg font-bold text-white">&lt; 180ms</div>
              <div className="text-[11px] text-zinc-400">Web Speech STT</div>
            </div>
            <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] backdrop-blur-sm">
              <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider">Isolation</div>
              <div className="text-base sm:text-lg font-bold text-white">100%</div>
              <div className="text-[11px] text-zinc-400">Rasa per-role NLU</div>
            </div>
            <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] backdrop-blur-sm">
              <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider">Role Packs</div>
              <div className="text-base sm:text-lg font-bold text-white">3 Modules</div>
              <div className="text-[11px] text-zinc-400">HR · IT · Admissions</div>
            </div>
            <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] backdrop-blur-sm">
              <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider">Extensibility</div>
              <div className="text-base sm:text-lg font-bold text-white">0 Redeploy</div>
              <div className="text-[11px] text-zinc-400">Declarative adapters</div>
            </div>
          </div>
        </div>

        {/* Live Orchestration Simulation Console */}
        <div className="max-w-4xl mx-auto bg-[#0E111C]/90 border border-white/[0.09] rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.7)] p-5 sm:p-7 overflow-hidden backdrop-blur-xl relative">
          {/* Window Chrome & Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-white/[0.07]">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 inline-block" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 inline-block" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 inline-block" />
              </div>
              <span className="text-xs font-mono text-zinc-400 tracking-wider flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <span>Live Orchestration Simulation</span>
              </span>
            </div>

            {/* Segmented Role Switcher */}
            <div className="flex items-center gap-1 p-1 rounded-xl bg-black/40 border border-white/[0.06] overflow-x-auto">
              <span className="text-[11px] font-mono text-zinc-400 px-2 hidden sm:inline">Role:</span>
              {EXAMPLES.map((ex) => {
                const isActive = selectedExample.id === ex.id;
                return (
                  <button
                    key={ex.id}
                    onClick={() => setSelectedExample(ex)}
                    className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all ${
                      isActive
                        ? 'bg-white text-zinc-950 font-bold shadow-sm'
                        : 'text-zinc-400 hover:text-white hover:bg-white/[0.05]'
                    }`}
                  >
                    {ex.role}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Simulation Content Body */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-6">
            {/* Input & Routing Pipeline (Left Panel) */}
            <div className="lg:col-span-7 space-y-4">
              <div>
                <div className="flex items-center gap-2 text-xs font-semibold text-zinc-400 mb-2">
                  <Mic className="w-3.5 h-3.5 text-[#2FD1C5]" />
                  <span>VOICE / TEXT INPUT</span>
                  <div className="flex items-center gap-1 ml-2">
                    <span className="w-1 bg-[#2FD1C5] rounded-full animate-audio-1 h-3 inline-block" />
                    <span className="w-1 bg-[#2FD1C5] rounded-full animate-audio-2 h-4 inline-block" />
                    <span className="w-1 bg-[#2FD1C5] rounded-full animate-audio-3 h-2 inline-block" />
                    <span className="w-1 bg-[#2FD1C5] rounded-full animate-audio-4 h-3 inline-block" />
                  </div>
                  <span className="ml-auto text-[10px] font-mono text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded border border-emerald-400/20">
                    Web Speech Active
                  </span>
                </div>
                <div className="p-4 rounded-xl bg-black/40 border border-white/[0.07] text-sm font-mono text-white shadow-inner">
                  {selectedExample.input}
                </div>
              </div>

              {/* Orchestration Telemetry Stack */}
              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05] space-y-3 text-xs font-mono">
                <div className="flex items-center justify-between text-zinc-400">
                  <span className="flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-[#8B82FF]" />
                    <span>Role Pack</span>
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${selectedExample.badgeColor}`}>
                    {selectedExample.role}
                  </span>
                </div>

                <div className="flex items-center justify-between text-zinc-400">
                  <span className="flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                    <span>Intent Classified</span>
                  </span>
                  <span className="text-white font-semibold">
                    {selectedExample.intent} <span className="text-[#2FD1C5] font-normal">({selectedExample.confidence})</span>
                  </span>
                </div>

                <div className="flex items-center justify-between text-zinc-400 gap-2">
                  <span className="flex items-center gap-1.5 flex-shrink-0">
                    <Layers className="w-3.5 h-3.5 text-teal-400" />
                    <span>Backend Adapter</span>
                  </span>
                  <div className="flex items-center gap-1.5 max-w-[260px]">
                    <span className="text-teal-300 truncate font-mono text-[11px]" title={selectedExample.adapter}>
                      {selectedExample.adapter}
                    </span>
                    <button
                      onClick={handleCopyAdapter}
                      className="p-1 text-zinc-400 hover:text-white transition-colors"
                      title="Copy Adapter Call"
                      aria-label="Copy Adapter Call"
                    >
                      {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Synthesized Response (Right Panel) */}
            <div className="lg:col-span-5 flex flex-col justify-between p-4.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
              <div>
                <div className="flex items-center justify-between text-xs font-semibold text-zinc-400 mb-3">
                  <span className="flex items-center gap-1.5">
                    <MessageSquare className="w-3.5 h-3.5 text-[#8B82FF]" />
                    <span>ASSISTANT RESPONSE</span>
                  </span>
                  <span className="text-[10px] font-mono text-zinc-400 bg-white/[0.04] px-1.5 py-0.5 rounded">
                    ~140ms
                  </span>
                </div>
                <p className="text-sm text-zinc-200 leading-relaxed font-sans mb-4">
                  {selectedExample.response}
                </p>
              </div>

              {/* TTS Audio Waveform Bar */}
              <div className="pt-3 border-t border-white/[0.06]">
                <div className="flex items-center justify-between text-[11px] text-zinc-400">
                  <div className="flex items-center gap-2">
                    <Volume2 className="w-3.5 h-3.5 text-[#2FD1C5]" />
                    <span className="truncate max-w-[190px]">{selectedExample.ttsVoice}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-1 bg-[#8B82FF] rounded-full animate-audio-2 h-2 inline-block" />
                    <span className="w-1 bg-[#8B82FF] rounded-full animate-audio-1 h-3 inline-block" />
                    <span className="w-1 bg-[#8B82FF] rounded-full animate-audio-5 h-2 inline-block" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
