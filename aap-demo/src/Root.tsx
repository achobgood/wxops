import React from 'react';
import {Composition} from 'remotion';
import {FPS, WIDTH, HEIGHT, TOTAL_FRAMES, chapters} from './styles/tokens';
import {Main} from './Main';
import {TheCall} from './scenes/TheCall';
import {TheStore} from './scenes/TheStore';
import {TheHold} from './scenes/TheHold';
import {TheRecall} from './scenes/TheRecall';
import {TheScale} from './scenes/TheScale';

export const RemotionRoot: React.FC = () => (
  <>
    {/* Full video — for rendering and Player */}
    <Composition
      id="AAP-Full"
      component={Main}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
    />

    {/* Individual chapters — for preview and isolation */}
    <Composition id="Ch1-TheCall" component={TheCall} durationInFrames={chapters.theCall.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Ch2-TheStore" component={TheStore} durationInFrames={chapters.theStore.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Ch3-TheHold" component={TheHold} durationInFrames={chapters.theHold.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Ch4-TheRecall" component={TheRecall} durationInFrames={chapters.theRecall.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Ch5-TheScale" component={TheScale} durationInFrames={chapters.theScale.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
  </>
);
