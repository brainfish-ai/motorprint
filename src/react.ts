import { useEffect, useRef, useState } from 'react';
import { createBotDetector, type BotDetector, type BotDetectorOptions, type BotScore } from './detector';

/**
 * React hook: returns the live bot score (null until enough input has been seen).
 * Everything runs on-device; nothing is sent anywhere.
 */
export function useBotScore(opts: Omit<BotDetectorOptions, 'onScore' | 'autoStart'> = {}): BotScore | null {
  const [score, setScore] = useState<BotScore | null>(null);
  const det = useRef<BotDetector | null>(null);
  useEffect(() => {
    det.current = createBotDetector({ ...opts, onScore: setScore });
    return () => det.current?.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opts.intervalMs, opts.windowMs, opts.minEvents, opts.smoothing, opts.model]);
  return score;
}
export type { BotScore, BotDetectorOptions } from './detector';
