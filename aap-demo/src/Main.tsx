import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {chapters} from './styles/tokens';
import {TheCall} from './scenes/TheCall';
import {TheStore} from './scenes/TheStore';
import {TheHold} from './scenes/TheHold';
import {TheRecall} from './scenes/TheRecall';
import {TheScale} from './scenes/TheScale';

export const Main: React.FC = () => (
  <AbsoluteFill>
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
