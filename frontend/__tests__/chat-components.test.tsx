import { render, screen, fireEvent } from '@testing-library/react';
import { BotMessage, type BotMessageData } from '../src/components/chat';
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
