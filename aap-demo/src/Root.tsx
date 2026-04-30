import React from 'react';
import {Composition, AbsoluteFill} from 'remotion';
import {FPS, WIDTH, HEIGHT, backgroundStyle} from './styles/tokens';
import {Highway} from './components/Highway';

const HighwayTest: React.FC = () => (
  <AbsoluteFill style={backgroundStyle}>
    <Highway drawStartFrame={10} drawDuration={50} />
  </AbsoluteFill>
);

export const RemotionRoot: React.FC = () => (
  <Composition id="HighwayTest" component={HighwayTest} durationInFrames={90} fps={FPS} width={WIDTH} height={HEIGHT} />
);
