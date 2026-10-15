import { render, screen, fireEvent } from '@testing-library/react';
import {
  BotMessage,
  type BotMessageData,
  AdmissionsStatusCard,
  AdmissionsNotFoundCard,
  AdmissionsFeeDeadlineCard,
  createAdmissionsFeeDeadlineMessage,
  HRLeaveBalanceCard,
  createHRLeaveBalanceMessage,
} from '../src/components/chat';
import ChatComponentGallery from '../src/app/home/chat/gallery/page';

// AC-8: all 9 bot message types render from props.
describe('Chat message component library', () => {
  it('renders plain_text from props', () => {
    render(<BotMessage message={{ type: 'plain_text', text: 'Hello there' }} />);
    expect(screen.getByText('Hello there')).toBeInTheDocument();
  });

  it('renders data_card with title and key/value rows from props', () => {
    render(
      <BotMessage
        message={{
          type: 'data_card',
          title: 'Leave balance',
          rows: [
            { label: 'Casual', value: '5 days' },
            { label: 'Total', value: '12 days' },
          ],
        }}
      />
    );
    expect(screen.getByText('Leave balance')).toBeInTheDocument();
    expect(screen.getByText('Casual')).toBeInTheDocument();
    expect(screen.getByText('5 days')).toBeInTheDocument();
    expect(screen.getByText('12 days')).toBeInTheDocument();
  });

  it('renders slot_prompt option buttons and fires onSelect from props', () => {
    const onSelect = jest.fn();
    render(
      <BotMessage
        message={{
          type: 'slot_prompt',
          text: 'What type of leave?',
          options: [{ label: 'Casual', value: 'casual' }, { label: 'Sick' }],
          onSelect,
        }}
      />
    );
    expect(screen.getByText('What type of leave?')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Casual' }));
    expect(onSelect).toHaveBeenCalledWith('casual');
    // Falls back to label when no value provided.
    fireEvent.click(screen.getByRole('button', { name: 'Sick' }));
    expect(onSelect).toHaveBeenCalledWith('Sick');
  });

  it('renders confirmation with confirm/cancel wired to props', () => {
    const onConfirm = jest.fn();
    const onCancel = jest.fn();
    render(
      <BotMessage
        message={{
          type: 'confirmation',
          title: 'Confirm leave request',
          rows: [{ label: 'Type', value: 'Casual' }],
          onConfirm,
          onCancel,
        }}
      />
    );
    expect(screen.getByText('Confirm leave request')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }));
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('renders result with a reference id from props', () => {
    render(<BotMessage message={{ type: 'result', text: 'Leave submitted! Reference', referenceId: 'LEAVE-2045' }} />);
    expect(screen.getByText('LEAVE-2045')).toBeInTheDocument();
  });

  it('renders not_found from props', () => {
    render(<BotMessage message={{ type: 'not_found', text: 'Application APP-9999 not found.' }} />);
    expect(screen.getByText('Application APP-9999 not found.')).toBeInTheDocument();
  });

  it('renders faq_answer from props', () => {
    render(<BotMessage message={{ type: 'faq_answer', text: 'WFH policy allows up to 3 days.' }} />);
    expect(screen.getByText('WFH policy allows up to 3 days.')).toBeInTheDocument();
  });

  it('renders error from props', () => {
    render(<BotMessage message={{ type: 'error', text: 'Something went wrong.' }} />);
    expect(screen.getByText('Something went wrong.')).toBeInTheDocument();
  });

  it('renders list items from props (ordered)', () => {
    render(
      <BotMessage
        message={{ type: 'list', title: "You'll need:", items: ['10th marksheet', '12th marksheet'] }}
      />
    );
    expect(screen.getByText("You'll need:")).toBeInTheDocument();
    expect(screen.getByText('10th marksheet')).toBeInTheDocument();
    expect(screen.getByText('12th marksheet')).toBeInTheDocument();
    expect(screen.getByRole('list').tagName).toBe('OL');
  });

  it('renders an unordered list when ordered is false', () => {
    render(<BotMessage message={{ type: 'list', ordered: false, items: ['a', 'b'] }} />);
    expect(screen.getByRole('list').tagName).toBe('UL');
  });
});

// AC-8 (showcase): the gallery renders every type in one surface.
describe('Chat component gallery', () => {
  const ALL_TYPES: BotMessageData['type'][] = [
    'plain_text',
    'data_card',
    'slot_prompt',
    'confirmation',
    'result',
    'not_found',
    'faq_answer',
    'error',
    'list',
  ];

  it('renders all 9 bot message types', () => {
    const { container } = render(<ChatComponentGallery />);
    const samples = container.querySelectorAll('[data-sample]');
    expect(samples).toHaveLength(9);
    ALL_TYPES.forEach((type) => {
      expect(container.querySelector(`[data-sample="${type}"]`)).not.toBeNull();
    });
  });
});

describe('Admissions components (slice-24)', () => {
  it('renders AdmissionsStatusCard with application ID, status, and next step', () => {
    render(
      <AdmissionsStatusCard
        applicationId="APP-1001"
        status="Under Review"
        nextStep="Document verification in progress."
        program="B.Tech Computer Science"
      />
    );
    expect(screen.getByText('Application APP-1001 Status')).toBeInTheDocument();
    expect(screen.getByText('APP-1001')).toBeInTheDocument();
    expect(screen.getByText('Under Review')).toBeInTheDocument();
    expect(screen.getByText('Document verification in progress.')).toBeInTheDocument();
    expect(screen.getByText('B.Tech Computer Science')).toBeInTheDocument();
  });

  it('renders AdmissionsNotFoundCard with graceful next step (FR-17)', () => {
    render(
      <AdmissionsNotFoundCard
        applicationId="APP-9999"
        suggestedNextStep="Please contact admissions@org.example.com"
      />
    );
    expect(
      screen.getByText('Application APP-9999 not found. Suggested next step: Please contact admissions@org.example.com')
    ).toBeInTheDocument();
  });
});

describe('Admissions document checklist components (slice-25)', () => {
  it('renders document checklist as an ordered list with program title (AC-1)', () => {
    const docs = [
      'Class 10 Grade Sheet / Birth Certificate',
      'Class 12 / Higher Secondary Marksheet',
      'Entrance Exam Scorecard (JEE / CET)',
      'Transfer Certificate & Conduct Certificate',
      'Valid Government Photo ID',
    ];

    render(
      <BotMessage
        message={{
          type: 'list',
          title: 'Computer Science (B.Tech) Required Documents:',
          ordered: true,
          items: docs,
        }}
      />
    );

    expect(screen.getByText('Computer Science (B.Tech) Required Documents:')).toBeInTheDocument();
    docs.forEach((doc) => {
      expect(screen.getByText(doc)).toBeInTheDocument();
    });
    expect(screen.getByRole('list').tagName).toBe('OL');
  });

  it('renders slot prompt when no program is specified and triggers option selection (AC-2)', () => {
    const onSelect = jest.fn();
    render(
      <BotMessage
        message={{
          type: 'slot_prompt',
          text: 'Which program would you like the document checklist for? (e.g. B.Tech, M.Tech, MBA)',
          options: [
            { label: 'Computer Science (B.Tech)', value: 'Computer Science (B.Tech)' },
            { label: 'Data Science (M.Tech)', value: 'Data Science (M.Tech)' },
            { label: 'MBA', value: 'MBA' },
          ],
          onSelect,
        }}
      />
    );

    expect(
      screen.getByText('Which program would you like the document checklist for? (e.g. B.Tech, M.Tech, MBA)')
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Computer Science (B.Tech)' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Data Science (M.Tech)' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'MBA' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'MBA' }));
    expect(onSelect).toHaveBeenCalledWith('MBA');
  });

  it('renders graceful not found card for unknown program without crashing (AC-3)', () => {
    render(
      <BotMessage
        message={{
          type: 'not_found',
          text: "No document checklist found for program 'Astrophysics'. Available programs: Computer Science (B.Tech), Data Science (M.Tech), MBA.",
        }}
      />
    );

    expect(
      screen.getByText(
        "No document checklist found for program 'Astrophysics'. Available programs: Computer Science (B.Tech), Data Science (M.Tech), MBA."
      )
    ).toBeInTheDocument();
  });
});

describe('HR Leave Balance components (slice-14)', () => {
  it('renders HRLeaveBalanceCard with total, casual, sick, and earned breakdown', () => {
    render(<HRLeaveBalanceCard total={22} casual={4} sick={6} earned={12} />);
    expect(screen.getByText('Your Leave Balance')).toBeInTheDocument();
    expect(screen.getByText('Total Leave')).toBeInTheDocument();
    expect(screen.getByText('22 days')).toBeInTheDocument();
    expect(screen.getByText('Casual')).toBeInTheDocument();
    expect(screen.getByText('4 days')).toBeInTheDocument();
    expect(screen.getByText('Sick')).toBeInTheDocument();
    expect(screen.getByText('6 days')).toBeInTheDocument();
    expect(screen.getByText('Earned')).toBeInTheDocument();
    expect(screen.getByText('12 days')).toBeInTheDocument();
  });

  it('renders BotMessage with createHRLeaveBalanceMessage', () => {
    const msg = createHRLeaveBalanceMessage({ total: 22, casual: 4, sick: 6, earned: 12 });
    render(<BotMessage message={msg} />);
    expect(screen.getByText('Your Leave Balance')).toBeInTheDocument();
    expect(screen.getByText('22 days')).toBeInTheDocument();
    expect(screen.getByText('4 days')).toBeInTheDocument();
  });
});

describe('Admissions Fee and Deadline components (slice-26)', () => {
  it('renders AdmissionsFeeDeadlineCard with fee items', () => {
    render(
      <AdmissionsFeeDeadlineCard
        academicYear="2026-2027"
        fees={[
          { item: 'Computer Science (B.Tech) Annual Tuition', amount: '₹3,20,000' },
          { item: 'Application Fee', amount: '₹1,500' },
        ]}
      />
    );
    expect(screen.getByText('Admissions Fee Schedule (2026-2027)')).toBeInTheDocument();
    expect(screen.getByText('Computer Science (B.Tech) Annual Tuition')).toBeInTheDocument();
    expect(screen.getByText('₹3,20,000')).toBeInTheDocument();
    expect(screen.getByText('Application Fee')).toBeInTheDocument();
    expect(screen.getByText('₹1,500')).toBeInTheDocument();
  });

  it('renders AdmissionsFeeDeadlineCard with deadline milestones', () => {
    render(
      <AdmissionsFeeDeadlineCard
        academicYear="2026-2027"
        deadlines={[
          { milestone: 'Regular Application Submission Deadline', date: 'November 30, 2026' },
          { milestone: 'First Merit List', date: 'December 18, 2026' },
        ]}
      />
    );
    expect(screen.getByText('Admissions Important Deadlines (2026-2027)')).toBeInTheDocument();
    expect(screen.getByText('Regular Application Submission Deadline')).toBeInTheDocument();
    expect(screen.getByText('November 30, 2026')).toBeInTheDocument();
    expect(screen.getByText('First Merit List')).toBeInTheDocument();
    expect(screen.getByText('December 18, 2026')).toBeInTheDocument();
  });

  it('renders AdmissionsFeeDeadlineCard with refund policy as faq_answer', () => {
    render(
      <AdmissionsFeeDeadlineCard
        academicYear="2026-2027"
        refundPolicy="100% refund minus processing fee if requested 15 days before classes start."
      />
    );
    expect(
      screen.getByText('Refund Policy (2026-2027): 100% refund minus processing fee if requested 15 days before classes start.')
    ).toBeInTheDocument();
  });

  it('renders BotMessage with createAdmissionsFeeDeadlineMessage', () => {
    const msg = createAdmissionsFeeDeadlineMessage({
      academicYear: '2026-2027',
      fees: [{ item: 'MBA Tuition', amount: '₹4,50,000' }],
    });
    render(<BotMessage message={msg} />);
    expect(screen.getByText('Admissions Fee Schedule (2026-2027)')).toBeInTheDocument();
    expect(screen.getByText('MBA Tuition')).toBeInTheDocument();
    expect(screen.getByText('₹4,50,000')).toBeInTheDocument();
  });
});


