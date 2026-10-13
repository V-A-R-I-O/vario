'use client';

// Browser Web Speech API (STT) wrapper for talk mode (slice-06).
// STT happens entirely in the browser; the server only does TTS. If the browser
// lacks the Web Speech API this hook reports `supported: false` and the caller
// falls back to text input (which stays fully usable).
import { useCallback, useEffect, useRef, useState } from 'react';

// Minimal typings for the (non-standard) Web Speech API — not in lib.dom.
interface SpeechRecognitionResultLike {
  0: { transcript: string };
  isFinal: boolean;
}
interface SpeechRecognitionEventLike {
  results: ArrayLike<SpeechRecognitionResultLike>;
}
interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((e: SpeechRecognitionEventLike) => void) | null;
  onend: (() => void) | null;
  onerror: ((e: unknown) => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

function getRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition || w.webkitSpeechRecognition || null) as
    | (new () => SpeechRecognitionLike)
    | null;
}

export function isSpeechRecognitionSupported(): boolean {
  return getRecognitionCtor() !== null;
}

interface UseSpeechRecognitionOptions {
  // Called with the final transcript when the user stops speaking.
  onResult: (transcript: string) => void;
  lang?: string;
}

export function useSpeechRecognition({ onResult, lang = 'en-US' }: UseSpeechRecognitionOptions) {
  const supported = isSpeechRecognitionSupported();
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const finalRef = useRef('');
  // Keep the latest callback without re-creating the recognition instance.
  const onResultRef = useRef(onResult);
  useEffect(() => {
    onResultRef.current = onResult;
  }, [onResult]);

  useEffect(() => {
    const Ctor = getRecognitionCtor();
    if (!Ctor) return;

    const recognition = new Ctor();
    recognition.lang = lang;
    recognition.interimResults = true;
    recognition.continuous = false;

    recognition.onresult = (e) => {
      let text = '';
      for (let i = 0; i < e.results.length; i++) {
        text += e.results[i][0].transcript;
      }
      finalRef.current = text;
      setTranscript(text);
    };
    recognition.onend = () => {
      setListening(false);
      const text = finalRef.current.trim();
      if (text) onResultRef.current(text);
    };
    recognition.onerror = () => {
      setListening(false);
    };

    recognitionRef.current = recognition;
    return () => {
      recognition.onresult = null;
      recognition.onend = null;
      recognition.onerror = null;
      recognition.abort();
      recognitionRef.current = null;
    };
  }, [lang]);

  const start = useCallback(() => {
    const recognition = recognitionRef.current;
    if (!recognition || listening) return;
    finalRef.current = '';
    setTranscript('');
    try {
      recognition.start();
      setListening(true);
    } catch {
      // start() throws if already started — ignore.
    }
  }, [listening]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  return { supported, listening, transcript, start, stop };
}
