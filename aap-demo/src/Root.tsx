import React from 'react';
import {Composition, Sequence, AbsoluteFill} from 'remotion';
import {FPS, WIDTH, HEIGHT, chapters} from './styles/tokens';
import {TheCall} from './scenes/TheCall';
import {TheStore} from './scenes/TheStore';
import {TheHold} from './scenes/TheHold';
import {TheRecall} from './scenes/TheRecall';
import {TheScale} from './scenes/TheScale';

const ScenesPreview: React.FC = () => (
  <AbsoluteFill>
    <Sequence from={chapters.theCall.from} durationInFrames={chapters.theCall.duration}>
      <TheCall />
    </Sequence>
    <Sequence from={chapters.theStore.from} durationInFrames={chapters.theStore.duration}>
      <TheStore />
    </Sequence>
    <Sequence from={chapters.theHold.from} durationInFrames={chapters.theHold.duration}>
      <TheHold />
    </Sequence>
  </AbsoluteFill>
);

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Scenes-1-3" component={ScenesPreview} durationInFrames={1650} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Ch1-TheCall" component={TheCall} durationInFrames={chapters.theCall.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Ch2-TheStore" component={TheStore} durationInFrames={chapters.theStore.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Ch3-TheHold" component={TheHold} durationInFrames={chapters.theHold.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Ch4-TheRecall" component={TheRecall} durationInFrames={chapters.theRecall.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Ch5-TheScale" component={TheScale} durationInFrames={chapters.theScale.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
  </>
);
