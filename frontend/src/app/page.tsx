import type { Metadata } from 'next';
import Navbar from '@/components/Landing/Navbar';
import Hero from '@/components/Landing/Hero';
import ProjectOverview from '@/components/Landing/ProjectOverview';
import HowItWorks from '@/components/Landing/HowItWorks';
import Capabilities from '@/components/Landing/Capabilities';
import Architecture from '@/components/Landing/Architecture';
import UseCases from '@/components/Landing/UseCases';
import OpenSource from '@/components/Landing/OpenSource';
import Footer from '@/components/Landing/Footer';

export const metadata: Metadata = {
  title: 'V.A.R.I.O. — Voice Adaptive Role & Intent Orchestrator',
  description: 'Role-Specific Voice Assistant Framework for Organizations and Entities.',
};

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#080B14] text-zinc-100 flex flex-col selection:bg-[#2FD1C5]/20 selection:text-white relative overflow-x-hidden">
      {/* Subtle structural grid pattern */}
      <div className="fixed inset-0 bg-grid-white opacity-40 pointer-events-none [mask-image:radial-gradient(ellipse_70%_50%_at_50%_0%,#000_60%,transparent_100%)] z-0" />

      <Navbar />
      <main className="flex-1 relative z-10">
        <Hero />
        <ProjectOverview />
        <HowItWorks />
        <Capabilities />
        <Architecture />
        <UseCases />
        <OpenSource />
      </main>
      <Footer />
    </div>
  );
}
