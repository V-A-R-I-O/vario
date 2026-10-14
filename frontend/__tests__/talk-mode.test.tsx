import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import ChatPage from '../src/app/home/chat/[id]/page';
import * as api from '../src/lib/api';

jest.mock('../src/lib/api');
const mockedApi = api as jest.Mocked<typeof api>;

// --- Web Speech API test double --------------------------------------------
// Captures the single recognition instance so tests can drive onresult/onend.
class FakeRecognition {
  static last: FakeRecognition | null = null;
  lang = '';
  interimResults = false;
  continuous = false;
  onresult: ((e: any) => void) | null = null;
  onend: (() => void) | null = null;
  onerror: ((e: any) => void) | null = null;
  start = jest.fn(() => {
    FakeRecognition.last = this;
  });
  stop = jest.fn();
  abort = jest.fn();
  constructor() {
    FakeRecognition.last = this;
  }
  // Helper: simulate the user speaking `text` then stopping.
  say(text: string) {
    this.onresult?.({ results: [{ 0: { transcript: text }, isFinal: true }] });
    this.onend?.();
  }
}

// --- Audio test double ------------------------------------------------------
class FakeAudio {
  static last: FakeAudio | null = null;
  onended: (() => void) | null = null;
  src: string;
  play = jest.fn(() => Promise.resolve());
  pause = jest.fn();
  constructor(src: string) {
    this.src = src;
    FakeAudio.last = this;
  }
}

beforeEach(() => {
  jest.clearAllMocks();
  FakeRecognition.last = null;
  FakeAudio.last = null;
  (window as any).SpeechRecognition = FakeRecognition;
  (window as any).webkitSpeechRecognition = FakeRecognition;
  (window as any).Audio = FakeAudio as any;

  mockedApi.fetchMessages.mockResolvedValue({ status: 'success', data: { messages: [] } });
  mockedApi.fetchConversations.mockResolvedValue({
    status: 'success',
    data: { conversations: [{ id: 'c1', role_pack: 'it', title: 'Ticket check' }] },
  });
});

function params() {
  return { params: { id: 'c1' } };
}

async function renderChat() {
  const utils = render(<ChatPage {...params()} />);
  // Wait for initial load to settle (empty-state appears).
  await screen.findByText(/Ask IT Support/i);
  return utils;
}

test('mic → speak → transcript shows in input bar and auto-sends in talk mode; audio auto-plays', async () => {
  mockedApi.sendChatMessage.mockResolvedValue({
    status: 'success',
    data: {
      response_text: 'Ticket TCK-4021 is In Progress.',
      tts_available: true,
      audio_base64: 'QUJD', // "ABC"
      audio_content_type: 'audio/mp3',
    },
  });

  await renderChat();

  // Tap the mic to enter talk mode.
  fireEvent.click(screen.getByRole('button', { name: 'Talk mode' }));
  expect(FakeRecognition.last).not.toBeNull();
  expect(FakeRecognition.last!.start).toHaveBeenCalled();

  // Live transcript lands in the input bar.
  act(() => {
    FakeRecognition.last!.onresult?.({
      results: [{ 0: { transcript: 'when was it updated' }, isFinal: false }],
    });
  });
  const input = screen.getByPlaceholderText(/tap the mic to talk/i) as HTMLInputElement;
  expect(input.value).toBe('when was it updated');

  // User stops speaking → auto-send with mode "talk".
  await act(async () => {
    FakeRecognition.last!.onend?.();
  });
  await waitFor(() =>
    expect(mockedApi.sendChatMessage).toHaveBeenCalledWith('c1', 'when was it updated', 'talk')
  );

  // Bot reply renders and its audio auto-plays.
  await screen.findByText('Ticket TCK-4021 is In Progress.');
  await waitFor(() => expect(FakeAudio.last).not.toBeNull());
  expect(FakeAudio.last!.play).toHaveBeenCalled();
  expect(FakeAudio.last!.src).toContain('data:audio/mp3;base64,QUJD');
});

test('hands-free loop: STT restarts after audio playback finishes', async () => {
  mockedApi.sendChatMessage.mockResolvedValue({
    status: 'success',
    data: {
      response_text: 'Done.',
      tts_available: true,
      audio_base64: 'QUJD',
      audio_content_type: 'audio/mp3',
    },
  });

  await renderChat();
  fireEvent.click(screen.getByRole('button', { name: 'Talk mode' }));
  const rec = FakeRecognition.last!;
  rec.start.mockClear();

  await act(async () => {
    rec.say('hello');
  });
  await waitFor(() => expect(FakeAudio.last).not.toBeNull());

  // Audio finishes → recognition should start again (hands-free).
  await act(async () => {
    FakeAudio.last!.onended?.();
  });
  await waitFor(() => expect(FakeRecognition.last!.start).toHaveBeenCalled());
});

test('tts_available:false shows the unavailable banner with Switch to text', async () => {
  mockedApi.sendChatMessage.mockResolvedValue({
    status: 'success',
    data: {
      response_text: 'Here is your answer.',
      tts_available: false,
      audio_base64: null,
      audio_content_type: null,
    },
  });

  await renderChat();
  fireEvent.click(screen.getByRole('button', { name: 'Talk mode' }));
  await act(async () => {
    FakeRecognition.last!.say('anything');
  });

  await screen.findByText(/Talk mode is temporarily unavailable/i);
  expect(screen.getByRole('button', { name: 'Switch to text' })).toBeInTheDocument();
  // Text reply is still shown — no crash, graceful degrade.
  expect(screen.getByText('Here is your answer.')).toBeInTheDocument();
});

test('graceful fallback: no Web Speech API → mic disabled, text chat still works', async () => {
  delete (window as any).SpeechRecognition;
  delete (window as any).webkitSpeechRecognition;

  mockedApi.sendChatMessage.mockResolvedValue({
    status: 'success',
    data: { response_text: 'Typed reply.' },
  });

  await renderChat();

  expect(screen.getByRole('button', { name: 'Talk mode' })).toBeDisabled();

  // Text input remains fully usable.
  const input = screen.getByPlaceholderText(/Message IT Support/i);
  fireEvent.change(input, { target: { value: 'hello typed' } });
  fireEvent.keyDown(input, { key: 'Enter' });

  await waitFor(() =>
    expect(mockedApi.sendChatMessage).toHaveBeenCalledWith('c1', 'hello typed', 'chat')
  );
  await screen.findByText('Typed reply.');
});
