import React from 'react';
import {Composition, Sequence, AbsoluteFill} from 'remotion';
import {FPS, WIDTH, HEIGHT, chapters} from './styles/tokens';
import {TheCall} from './scenes/TheCall';
import {TheStore} from './scenes/TheStore';

const ScenesPreview: React.FC = () => (
  <AbsoluteFill>
    <Sequence from={chapters.theCall.from} durationInFrames={chapters.theCall.duration}>
      <TheCall />
    </Sequence>
    <Sequence from={chapters.theStore.from} durationInFrames={chapters.theStore.duration}>
      <TheStore />
    </Sequence>
  </AbsoluteFill>
);

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Scenes-1-2" component={ScenesPreview} durationInFrames={1050} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Ch1-TheCall" component={TheCall} durationInFrames={chapters.theCall.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Ch2-TheStore" component={TheStore} durationInFrames={chapters.theStore.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
  </>
);
