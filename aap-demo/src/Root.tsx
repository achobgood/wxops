import React from 'react';
import {Composition} from 'remotion';
import {FPS, WIDTH, HEIGHT, TOTAL_FRAMES, acts} from './styles/tokens';
import {Main} from './Main';
import {ColdOpen} from './scenes/ColdOpen';
import {TheRouting} from './scenes/TheRouting';
import {TheStore} from './scenes/TheStore';
import {TheTransition} from './scenes/TheTransition';
import {TheCountdown} from './scenes/TheCountdown';
import {TheSnap} from './scenes/TheSnap';
import {TheCatch} from './scenes/TheCatch';
import {TheScale} from './scenes/TheScale';

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="AAP-Full"
      component={Main}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
    />

    <Composition id="Sc1-ColdOpen" component={ColdOpen} durationInFrames={acts.coldOpen.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Sc2-TheRouting" component={TheRouting} durationInFrames={acts.theRouting.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Sc3-TheStore" component={TheStore} durationInFrames={acts.theStore.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Sc4-TheTransition" component={TheTransition} durationInFrames={acts.theTransition.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Sc5-TheCountdown" component={TheCountdown} durationInFrames={acts.theCountdown.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Sc6-TheSnap" component={TheSnap} durationInFrames={acts.theSnap.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Sc7-TheCatch" component={TheCatch} durationInFrames={acts.theCatch.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="Sc8-TheScale" component={TheScale} durationInFrames={acts.theScale.duration} fps={FPS} width={WIDTH} height={HEIGHT} />
  </>
);
