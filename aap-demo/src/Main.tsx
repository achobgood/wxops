import React from 'react';
import {AbsoluteFill, Audio, interpolate, Sequence, staticFile} from 'remotion';
import {chapters, FPS, TOTAL_FRAMES} from './styles/tokens';
import {TheCall} from './scenes/TheCall';
import {TheStore} from './scenes/TheStore';
import {TheHold} from './scenes/TheHold';
import {TheRecall} from './scenes/TheRecall';
import {TheScale} from './scenes/TheScale';

const NARRATION_FILES = [
  {file: 'ch1-the-call.mp3', from: chapters.theCall.from, duration: chapters.theCall.duration},
  {file: 'ch2-the-store.mp3', from: chapters.theStore.from, duration: chapters.theStore.duration},
  {file: 'ch3-the-hold.mp3', from: chapters.theHold.from, duration: chapters.theHold.duration},
  {file: 'ch4-the-recall.mp3', from: chapters.theRecall.from, duration: chapters.theRecall.duration},
  {file: 'ch5-the-scale.mp3', from: chapters.theScale.from, duration: chapters.theScale.duration},
] as const;

const FADE_IN = FPS;
const FADE_OUT = FPS * 2;

function musicVolume(f: number): number {
  return interpolate(
    f,
    [0, FADE_IN, TOTAL_FRAMES - FADE_OUT, TOTAL_FRAMES],
    [0, 0.10, 0.10, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
}

export const Main: React.FC = () => (
  <AbsoluteFill>
    {/* Background music — loops, low volume under narration */}
    <Audio
      loop
      volume={musicVolume}
      src={staticFile('audio/background.mp3')}
    />

    {/* Per-chapter narration — placed at each chapter's start frame */}
    {NARRATION_FILES.map((n) => (
      <Sequence key={n.file} from={n.from} durationInFrames={n.duration} name={`Narration: ${n.file}`}>
        <Audio
          volume={(f) =>
            interpolate(f, [0, 8], [0, 1.0], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })
          }
          src={staticFile(`audio/${n.file}`)}
        />
      </Sequence>
    ))}

    {/* Visual scenes */}
    <Sequence from={chapters.theCall.from} durationInFrames={chapters.theCall.duration} name="Ch 1 — The Call">
      <TheCall />
    </Sequence>
    <Sequence from={chapters.theStore.from} durationInFrames={chapters.theStore.duration} name="Ch 2 — The Store">
      <TheStore />
    </Sequence>
    <Sequence from={chapters.theHold.from} durationInFrames={chapters.theHold.duration} name="Ch 3 — The Hold">
      <TheHold />
    </Sequence>
    <Sequence from={chapters.theRecall.from} durationInFrames={chapters.theRecall.duration} name="Ch 4 — The Recall">
      <TheRecall />
    </Sequence>
    <Sequence from={chapters.theScale.from} durationInFrames={chapters.theScale.duration} name="Ch 5 — The Scale">
      <TheScale />
    </Sequence>
  </AbsoluteFill>
);
