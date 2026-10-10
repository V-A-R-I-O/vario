'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Menu, X, ArrowRight } from 'lucide-react';

export default function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: 'Overview', href: '#overview' },
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'Capabilities', href: '#capabilities' },
    { label: 'Architecture', href: '#architecture' },
    { label: 'Use Cases', href: '#use-cases' },
    { label: 'Open Source', href: '#open-source' },
  ];

  return (
    <header className="sticky top-3.5 z-50 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 transition-all">
      <div className="bg-[#0E111C]/85 backdrop-blur-xl border border-white/[0.08] rounded-2xl shadow-[0_8px_32px_rgba(0,0,0,0.6)] px-4 sm:px-5">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Name */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="relative">
              <div className="mark w-8 h-8 rounded-lg transition-transform duration-200 group-hover:scale-105" />
            </div>
            <div className="flex items-center">
              <span className="font-bold text-lg text-white tracking-tight">
                VARIO
              </span>
              <span className="hidden sm:inline-block ml-2.5 text-xs font-medium text-zinc-400 border-l border-zinc-700/60 pl-2.5 tracking-wide">
                Voice Adaptive Role &amp; Intent Orchestrator
              </span>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden lg:flex items-center gap-1 bg-white/[0.02] border border-white/[0.04] p-1 rounded-xl">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-xs font-medium text-zinc-400 hover:text-white px-3 py-1.5 rounded-lg transition-all hover:bg-white/[0.06]"
              >
                {link.label}
              </a>
            ))}
          </nav>

          {/* Actions: GitHub & Launch App */}
          <div className="hidden sm:flex items-center gap-3">
            <a
              href="https://github.com/V-A-R-I-O/vario"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-300 hover:text-white px-3 py-2 rounded-xl border border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.06] hover:border-white/[0.15] transition-all"
              aria-label="GitHub Repository"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                />
              </svg>
              <span>GitHub</span>
            </a>
            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 text-xs font-semibold bg-gradient-to-r from-[#2FD1C5] to-[#6C63FF] text-[#0C1220] px-4 py-2 rounded-xl hover:opacity-95 active:scale-[0.98] transition-all shadow-[0_2px_12px_rgba(47,209,197,0.25)] hover:shadow-[0_4px_16px_rgba(47,209,197,0.4)]"
            >
              <span>Enter Application</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <div className="flex sm:hidden items-center gap-2">
            <Link
              href="/login"
              className="text-xs font-semibold bg-gradient-to-r from-[#2FD1C5] to-[#6C63FF] text-[#0C1220] px-3 py-1.5 rounded-lg shadow-sm"
            >
              Sign In
            </Link>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="text-zinc-400 hover:text-white p-2 rounded-lg hover:bg-white/[0.06] transition-colors"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden mt-2 border border-white/[0.09] bg-[#0E111C]/95 backdrop-blur-2xl rounded-2xl p-4 shadow-2xl space-y-2">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 rounded-xl text-sm font-medium text-zinc-300 hover:text-white hover:bg-white/[0.06] transition-colors"
            >
              {link.label}
            </a>
          ))}
          <div className="pt-3 border-t border-white/[0.08] flex items-center justify-between">
            <a
              href="https://github.com/V-A-R-I-O/vario"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-medium text-zinc-300 hover:text-white flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-white/[0.06]"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                />
              </svg>
              <span>GitHub</span>
            </a>
            <Link
              href="/login"
              onClick={() => setMobileMenuOpen(false)}
              className="text-xs font-semibold bg-gradient-to-r from-[#2FD1C5] to-[#6C63FF] text-[#0C1220] px-4 py-2 rounded-xl"
            >
              Enter Application
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
