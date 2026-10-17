'use client';

import { useEffect, useRef, useState } from 'react';

/**
 * Seconds elapsed (one decimal, e.g. "3.0") since `running` last became true, ticking once per
 * second. When `running` turns false the last value is kept.
 */
export function useElapsedTimer(running: boolean): string {
  const [elapsed, setElapsed] = useState(0);
  const [wasRunning, setWasRunning] = useState(running);
  const startRef = useRef<number>(0);

  // Reset to 0 when a new run starts (adjusting state during render, per React docs,
  // instead of a synchronous setState inside the effect).
  if (running !== wasRunning) {
    setWasRunning(running);
    if (running) setElapsed(0);
  }

  useEffect(() => {
    if (!running) return;
    startRef.current = Date.now();
    const interval = setInterval(() => {
      setElapsed(Date.now() - startRef.current);
    }, 1000);
    return () => clearInterval(interval);
  }, [running]);

  return (elapsed / 1000).toFixed(1);
}
