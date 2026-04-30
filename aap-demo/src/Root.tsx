import React from 'react';
import {Composition, AbsoluteFill} from 'remotion';
import {fonts, colors, backgroundStyle, FPS, WIDTH, HEIGHT} from './styles/tokens';

const FontTest: React.FC = () => (
  <AbsoluteFill style={{...backgroundStyle, justifyContent: 'center', alignItems: 'center', flexDirection: 'column', gap: 20}}>
    <div style={{fontFamily: fonts.headline, fontSize: 60, fontWeight: 700, color: colors.white, textTransform: 'uppercase', letterSpacing: '-0.02em'}}>BARLOW CONDENSED — HEADLINE</div>
    <div style={{fontFamily: fonts.body, fontSize: 36, color: colors.coolGray}}>Inter — Body text</div>
    <div style={{fontFamily: fonts.mono, fontSize: 28, color: colors.yellow}}>IBM Plex Mono — 0:47</div>
  </AbsoluteFill>
);

export const RemotionRoot: React.FC = () => (
  <Composition id="FontTest" component={FontTest} durationInFrames={90} fps={FPS} width={WIDTH} height={HEIGHT} />
);
