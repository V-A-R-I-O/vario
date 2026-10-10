import { Users, Laptop, GraduationCap, CheckCircle2, ArrowRight, Briefcase } from 'lucide-react';
import Link from 'next/link';

export default function UseCases() {
  const domains = [
    {
      id: 'hr',
      title: 'HR Self-Service',
      subtitle: 'Employee Workflows & Policy FAQs',
      icon: Users,
      badge: 'HR Role Pack',
      badgeColor: 'text-[#2FD1C5] bg-[#2FD1C5]/10 border-[#2FD1C5]/20',
      sampleQuery: '"What is my remaining paid annual leave balance?"',
      description:
        'Eliminates back-and-forth HR emails by resolving employee transactional queries directly through conversational voice and chat.',
      workflows: [
        {
          name: 'Leave Balance Inquiries',
          detail: 'Fetches sick, casual, and annual leave accruals directly via the HRMS adapter in natural language.',
        },
        {
          name: 'Guided Leave Application',
          detail: 'Step-by-step slot collection for leave type, date range, and reason with explicit confirmation and reference ID generation.',
        },
        {
          name: 'Curated Policy FAQs',
          detail: 'Answers questions on parental leave, remote work guidelines, healthcare benefits, and company policies.',
        },
      ],
    },
    {
      id: 'it',
      title: 'IT Support',
      subtitle: 'Incident Management & Service Desk',
      icon: Laptop,
      badge: 'IT Support Pack',
      badgeColor: 'text-[#8B82FF] bg-[#6C63FF]/15 border-[#6C63FF]/25',
      sampleQuery: '"I cannot log in to VPN and need my password reset"',
      description:
        'Reduces service desk queues by automating routine ticket creation, incident status lookups, and account access procedures.',
      workflows: [
        {
          name: 'Automated Ticket Creation',
          detail: 'Gathers issue description, auto-categorizes (Hardware, Software, Network), and returns an ITSM ticket ID.',
        },
        {
          name: 'Ticket Status Tracking',
          detail: 'Allows employees to query open ticket status, assigned technician, and latest notes using their ticket reference number.',
        },
        {
          name: 'Guided Password Reset',
          detail: 'Safely guides employees through identity verification and password reset while preventing duplicate tickets.',
        },
      ],
    },
    {
      id: 'adm',
      title: 'Admissions',
      subtitle: 'Student & Applicant Services',
      icon: GraduationCap,
      badge: 'Admissions Pack',
      badgeColor: 'text-amber-300 bg-amber-400/10 border-amber-400/20',
      sampleQuery: '"Check application status for ID #ADM-8291"',
      description:
        'Assists prospective students and applicants with high-frequency enrollment status, document requirements, and deadline questions.',
      workflows: [
        {
          name: 'Application Status Lookup',
          detail: 'Prospective students query admission status by application ID with real-time department review notes.',
        },
        {
          name: 'Program Document Checklists',
          detail: 'Dynamic document verification checklists tailored to undergraduate, postgraduate, and international programs.',
        },
        {
          name: 'Fee Deadlines & Schedules',
          detail: 'Pulls fee schedules and critical cutoff dates from the admissions calendar with graceful guidance on invalid queries.',
        },
      ],
    },
  ];

  return (
    <section id="use-cases" className="py-24 bg-[#0A0D16] border-y border-white/[0.06] relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.08] text-xs font-mono uppercase tracking-widest text-[#2FD1C5] mb-4">
            <Briefcase className="w-3.5 h-3.5" />
            <span>Domain Applications</span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight mb-5">
            Enterprise Use Cases
          </h2>
          <p className="text-base sm:text-lg text-zinc-400 leading-relaxed max-w-2xl mx-auto">
            Three pre-configured role domains handling transactional self-service workflows with complete domain isolation.
          </p>
        </div>

        {/* 3-Column Bento Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {domains.map((domain) => {
            const Icon = domain.icon;
            return (
              <div
                key={domain.id}
                className="rounded-2xl bg-[#0E111C]/90 border border-white/[0.08] p-7 sm:p-8 flex flex-col justify-between hover:border-white/[0.18] transition-all hover:shadow-[0_8px_32px_rgba(0,0,0,0.5)] group backdrop-blur-md relative overflow-hidden"
              >
                <div>
                  <div className="flex items-center justify-between mb-5">
                    <div className="w-11 h-11 rounded-xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-center text-white group-hover:scale-105 transition-transform shadow-sm">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className={`text-xs font-mono font-semibold px-2.5 py-1 rounded-full border ${domain.badgeColor}`}>
                      {domain.badge}
                    </span>
                  </div>

                  <h3 className="text-xl font-bold text-white mb-1 tracking-tight">
                    {domain.title}
                  </h3>
                  <p className="text-xs font-mono text-zinc-400 mb-3">{domain.subtitle}</p>
                  <p className="text-sm text-zinc-300 leading-relaxed mb-5 font-normal">{domain.description}</p>

                  {/* Sample Query Chip */}
                  <div className="mb-6 p-3 rounded-xl bg-black/40 border border-white/[0.06] text-xs font-mono text-zinc-400">
                    <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Sample Voice Query</div>
                    <div className="text-zinc-200">{domain.sampleQuery}</div>
                  </div>

                  <div className="space-y-4 pt-4 border-t border-white/[0.07]">
                    {domain.workflows.map((wf) => (
                      <div key={wf.name} className="space-y-1">
                        <div className="flex items-center gap-2 text-xs font-semibold text-white">
                          <CheckCircle2 className="w-4 h-4 text-[#2FD1C5] flex-shrink-0" />
                          <span>{wf.name}</span>
                        </div>
                        <p className="text-xs text-zinc-400 pl-6 leading-relaxed font-normal">{wf.detail}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="pt-6 mt-6 border-t border-white/[0.07]">
                  <Link
                    href="/login"
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#2FD1C5] hover:text-white transition-colors"
                  >
                    <span>Try {domain.title} in App</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
