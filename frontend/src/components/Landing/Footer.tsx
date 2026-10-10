import Link from 'next/link';

export default function Footer() {
  return (
    <footer className="bg-[#06080F] border-t border-white/[0.08] py-16 text-zinc-400 text-sm relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 mb-12">
          {/* Brand & Mission */}
          <div className="md:col-span-2 space-y-4">
            <div className="flex items-center gap-3">
              <div className="mark w-7 h-7 rounded-lg shadow-sm" />
              <span className="font-bold text-white text-lg tracking-tight">VARIO</span>
            </div>
            <p className="text-xs font-mono text-zinc-300">
              Voice Adaptive Role &amp; Intent Orchestrator
            </p>
            <p className="text-xs text-zinc-400 max-w-sm leading-relaxed font-normal">
              A Role-Specific Voice Assistant Framework providing a unified conversational core with pluggable role packs for HR, IT Support, and Admissions.
            </p>

            {/* System Status Pill */}
            <div className="pt-2">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.08] text-xs font-mono text-zinc-300">
                <span className="flex h-2 w-2 rounded-full bg-emerald-400" />
                <span>All Systems Operational</span>
              </div>
            </div>
          </div>

          {/* Quick Navigation Links */}
          <div className="space-y-3">
            <h4 className="text-xs font-mono uppercase text-zinc-300 font-bold tracking-wider">
              Navigation
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <a href="#overview" className="hover:text-white transition-colors">
                  Overview
                </a>
              </li>
              <li>
                <a href="#how-it-works" className="hover:text-white transition-colors">
                  How It Works
                </a>
              </li>
              <li>
                <a href="#capabilities" className="hover:text-white transition-colors">
                  Capabilities
                </a>
              </li>
              <li>
                <a href="#architecture" className="hover:text-white transition-colors">
                  Architecture
                </a>
              </li>
              <li>
                <a href="#use-cases" className="hover:text-white transition-colors">
                  Enterprise Use Cases
                </a>
              </li>
            </ul>
          </div>

          {/* Project & Legal Links */}
          <div className="space-y-3">
            <h4 className="text-xs font-mono uppercase text-zinc-300 font-bold tracking-wider">
              Project &amp; Legal
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <a
                  href="https://github.com/V-A-R-I-O/vario"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white transition-colors"
                >
                  GitHub Repository
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/V-A-R-I-O/vario#readme"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white transition-colors"
                >
                  Documentation
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/V-A-R-I-O/vario/blob/main/LICENSE"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white transition-colors"
                >
                  Apache License 2.0
                </a>
              </li>
              <li>
                <Link href="/login" className="text-[#2FD1C5] hover:text-white transition-colors font-semibold">
                  Enter Application
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-white/[0.08] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-zinc-400">
          <p>© 2026 VARIO Contributors. Released under the Apache License 2.0.</p>
          <p className="font-mono text-zinc-400">PES University · Team PIPELINE (Project ID 42)</p>
        </div>
      </div>
    </footer>
  );
}
