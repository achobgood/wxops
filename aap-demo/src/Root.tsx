import React from 'react';
import {Composition, AbsoluteFill} from 'remotion';
import {FPS, WIDTH, HEIGHT, backgroundStyle} from './styles/tokens';
import {Highway} from './components/Highway';
import {Car} from './components/Car';

const FoundationTest: React.FC = () => (
  <AbsoluteFill style={backgroundStyle}>
    <Highway drawStartFrame={5} drawDuration={40} />
    <Car enterFrame={15} startDistance={0} endDistance={55} travelDuration={50} />
  </AbsoluteFill>
);

export const RemotionRoot: React.FC = () => (
  <Composition
    id="FoundationTest"
    component={FoundationTest}
    durationInFrames={90}
    fps={FPS}
    width={WIDTH}
    height={HEIGHT}
  />
);
