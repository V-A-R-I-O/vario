'use client';

// Component gallery — renders all 9 bot message types from props, in isolation.
// This is the slice-05 "component library showcase" (AC-8): the integration
// surface role packs build against. Each entry below is pure props.
import { BotMessage, type BotMessageData } from '@/components/chat';

const SAMPLES: { label: string; message: BotMessageData }[] = [
  {
    label: 'plain_text',
    message: { type: 'plain_text', text: 'Hello! How can I help you today?' },
  },
  {
    label: 'data_card',
    message: {
      type: 'data_card',
      title: 'Leave balance',
      rows: [
        { label: 'Casual', value: '5 days' },
        { label: 'Sick', value: '4 days' },
        { label: 'Earned', value: '3 days' },
        { label: 'Total', value: '12 days' },
      ],
    },
  },
  {
    label: 'slot_prompt',
    message: {
      type: 'slot_prompt',
      text: 'What type of leave would you like to request?',
      options: [{ label: 'Casual' }, { label: 'Sick' }, { label: 'Earned' }],
    },
  },
  {
    label: 'confirmation',
    message: {
      type: 'confirmation',
      title: 'Confirm leave request',
      rows: [
        { label: 'Type', value: 'Casual' },
        { label: 'Dates', value: 'Sep 10 – Sep 11' },
        { label: 'Reason', value: 'Family function' },
      ],
    },
  },
  {
    label: 'result',
    message: { type: 'result', text: 'Leave submitted! Reference', referenceId: 'LEAVE-2045' },
  },
  {
    label: 'not_found',
    message: {
      type: 'not_found',
      text: 'Leave request LEAVE-1999 not found. Contact hr@acme-corp.com if you believe this is an error.',
    },
  },
  {
    label: 'faq_answer',
    message: {
      type: 'faq_answer',
      text: 'Our WFH policy allows employees to work from home up to 3 days per week, subject to manager approval. Core hours (10am–4pm) apply regardless of location.',
    },
  },
  {
    label: 'error',
    message: { type: 'error', text: 'Something went wrong fetching that. Please try again.' },
  },
  {
    label: 'list',
    message: {
      type: 'list',
      title: "You'll need:",
      ordered: true,
      items: ['Leave policy acknowledgment form', 'Manager approval email', 'Updated emergency contact form'],
    },
  },
];

export default function ChatComponentGallery() {
  return (
    <main className="canvas role-hr">
      <div className="topbar">
        <button className="rail-toggle" onClick={() => document.querySelector('.rail')?.classList.toggle('open')} aria-label="Toggle sidebar">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
        <h1>Chat message components</h1>
      </div>
      <div className="content-scroll">
        <div className="content-pad" style={{ maxWidth: 760 }}>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 26 }}>
            All {SAMPLES.length} bot message types, rendered from props. Role packs compose these generic
            components — they are not role-specific.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
            {SAMPLES.map(({ label, message }) => (
              <section key={label} data-sample={label}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-faint)', marginBottom: 10 }}>
                  {label}
                </div>
                <div className="chat-thread" style={{ padding: 0, gap: 0 }}>
                  <BotMessage message={message} />
                </div>
              </section>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
