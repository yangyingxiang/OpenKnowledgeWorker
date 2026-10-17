import type { PddPhase, PddStep } from '@/lib/pdd/parse';

/** Called when the user asks to open the detail panel for a step. */
export type StepClickHandler = (step: PddStep, phase: PddPhase) => void;
