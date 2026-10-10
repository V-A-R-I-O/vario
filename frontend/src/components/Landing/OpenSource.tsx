'use client';

import { useState } from 'react';
import { Scale, BookOpen, ExternalLink, ArrowRight, Copy, Check, Terminal } from 'lucide-react';
import Link from 'next/link';

export default function OpenSource() {
  const [copied, setCopied] = useState(false);
  const cloneCmd = 'git clone https://github.com/V-A-R-I-O/vario.git';

  const handleCopy = () => {
    navigator.clipboard?.writeText(cloneCmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="open-source" className="py-24 bg-[#080B14] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto rounded-3xl bg-[#0E111C]/90 border border-white/[0.09] p-8 sm:p-12 shadow-[0_20px_60px_rgba(0,0,0,0.6)] backdrop-blur-xl relative overflow-hidden">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs font-mono text-zinc-300 mb-4 shadow-sm">
              <Scale className="w-3.5 h-3.5 text-[#2FD1C5]" />
              <span>Apache License 2.0</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-4">
              Open Source &amp; Community Driven
            </h2>
            <p className="text-sm sm:text-base text-zinc-400 leading-relaxed font-normal">
              VARIO is an open-source research and engineering framework released under the permissive Apache License 2.0.
              Designed for transparency, extensibility, and auditability in organizational deployments.
            </p>
          </div>

          {/* Interactive Clone Terminal Box */}
          <div className="max-w-xl mx-auto mb-10 p-3.5 rounded-xl bg-black/60 border border-white/[0.08] flex items-center justify-between font-mono text-xs text-zinc-300 shadow-inner">
            <div className="flex items-center gap-2.5 overflow-x-auto">
              <Terminal className="w-4 h-4 text-[#2FD1C5] flex-shrink-0" />
              <span className="text-zinc-500">$</span>
              <span className="truncate">{cloneCmd}</span>
            </div>
            <button
              onClick={handleCopy}
              className="ml-2 px-2.5 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] text-zinc-300 hover:text-white transition-all flex items-center gap-1.5 flex-shrink-0 text-[11px]"
              aria-label="Copy clone command"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-emerald-400" />
                  <span className="text-emerald-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            {/* GitHub Card */}
            <a
              href="https://github.com/V-A-R-I-O/vario"
              target="_blank"
              rel="noopener noreferrer"
              className="p-6 rounded-2xl bg-[#0A0D16]/90 border border-white/[0.08] hover:border-white/[0.18] transition-all hover:-translate-y-0.5 group flex flex-col justify-between shadow-sm"
              aria-label="GitHub Repository"
            >
              <div>
                <div className="w-10 h-10 rounded-xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-center text-white mb-4 group-hover:scale-105 transition-transform">
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      clipRule="evenodd"
                      d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                    />
                  </svg>
                </div>
                <h3 className="text-base font-bold text-white mb-1.5 flex items-center gap-1.5">
                  <span>GitHub Repository</span>
                  <ExternalLink className="w-3.5 h-3.5 text-zinc-500 group-hover:text-white" />
                </h3>
                <p className="text-xs text-zinc-400 leading-relaxed font-normal">
                  Explore source code, submit issues, and inspect sprint implementation slices.
                </p>
              </div>
              <span className="text-xs font-mono text-[#2FD1C5] mt-5 flex items-center gap-1 font-medium">
                <span>View Repository</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </a>

            {/* Documentation Card */}
            <a
              href="https://github.com/V-A-R-I-O/vario#readme"
              target="_blank"
              rel="noopener noreferrer"
              className="p-6 rounded-2xl bg-[#0A0D16]/90 border border-white/[0.08] hover:border-white/[0.18] transition-all hover:-translate-y-0.5 group flex flex-col justify-between shadow-sm"
              aria-label="Documentation"
            >
              <div>
                <div className="w-10 h-10 rounded-xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-center text-white mb-4 group-hover:scale-105 transition-transform">
                  <BookOpen className="w-5 h-5 text-[#8B82FF]" />
                </div>
                <h3 className="text-base font-bold text-white mb-1.5 flex items-center gap-1.5">
                  <span>Documentation</span>
                  <ExternalLink className="w-3.5 h-3.5 text-zinc-500 group-hover:text-white" />
                </h3>
                <p className="text-xs text-zinc-400 leading-relaxed font-normal">
                  Comprehensive architectural specs (ADD), PRD requirements, and API contracts.
                </p>
              </div>
              <span className="text-xs font-mono text-[#8B82FF] mt-5 flex items-center gap-1 font-medium">
                <span>Read Docs</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </a>

            {/* Apache License Card */}
            <a
              href="https://github.com/V-A-R-I-O/vario/blob/main/LICENSE"
              target="_blank"
              rel="noopener noreferrer"
              className="p-6 rounded-2xl bg-[#0A0D16]/90 border border-white/[0.08] hover:border-white/[0.18] transition-all hover:-translate-y-0.5 group flex flex-col justify-between shadow-sm"
              aria-label="License"
            >
              <div>
                <div className="w-10 h-10 rounded-xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-center text-white mb-4 group-hover:scale-105 transition-transform">
                  <Scale className="w-5 h-5 text-emerald-400" />
                </div>
                <h3 className="text-base font-bold text-white mb-1.5 flex items-center gap-1.5">
                  <span>Apache License 2.0</span>
                  <ExternalLink className="w-3.5 h-3.5 text-zinc-500 group-hover:text-white" />
                </h3>
                <p className="text-xs text-zinc-400 leading-relaxed font-normal">
                  Free and permissive for organizational customization, academic research, and extension.
                </p>
              </div>
              <span className="text-xs font-mono text-emerald-400 mt-5 flex items-center gap-1 font-medium">
                <span>License Terms</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </a>
          </div>

          {/* Academic Context & CTA Banner */}
          <div className="pt-8 border-t border-white/[0.08] flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
            <div>
              <p className="text-xs font-mono text-zinc-400">
                PES University · Jackfruit Mini-Project · UE24CS341A Software Engineering
              </p>
              <p className="text-xs text-zinc-400 mt-0.5">
                Developed by Team PIPELINE (Project ID 42)
              </p>
            </div>
            <Link
              href="/login"
              className="inline-flex items-center gap-2 bg-gradient-to-r from-[#2FD1C5] to-[#6C63FF] text-[#0C1220] font-bold px-5 py-2.5 rounded-xl text-xs sm:text-sm hover:opacity-95 active:scale-[0.98] transition-all shadow-[0_2px_12px_rgba(47,209,197,0.25)] flex-shrink-0"
            >
              <span>Launch Application</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
