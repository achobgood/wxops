import React from 'react';
import {AbsoluteFill, Loop, OffthreadVideo, staticFile, useCurrentFrame, interpolate, Easing} from 'remotion';
import {backgroundStyle, colors, fonts, fadeUp} from '../styles/tokens';
import {POSScreen} from '../components/POSScreen';
import {WaveformBar} from '../components/WaveformBar';
import {StepBadge} from '../components/StepBadge';

export const TheStore: React.FC = () => {
  const frame = useCurrentFrame();

  const storeImgOpacity = interpolate(frame, [10, 30], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const storeImgScale = interpolate(frame, [10, 30], [1.05, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  const webhookLabel = fadeUp(frame, 15, 20, 15);

  return (
    <AbsoluteFill style={backgroundStyle}>
      <StepBadge step={2} label="The Store" enterFrame={5} />

      <Loop durationInFrames={240}>
        <OffthreadVideo
          src={staticFile('video/store-counter.mp4')}
          style={{
            position: 'absolute',
            left: 40,
            top: 120,
            width: 520,
            height: 347,
            objectFit: 'cover',
            opacity: storeImgOpacity,
            transform: `scale(${storeImgScale})`,
            borderRadius: 12,
            boxShadow: '0 8px 40px rgba(255, 207, 6, 0.15)',
          }}
          volume={0}
        />
      </Loop>

      <div
        style={{
          position: 'absolute',
          left: 60,
          top: 500,
          opacity: webhookLabel.opacity,
          transform: webhookLabel.transform,
        }}
      >
        <div style={{fontFamily: fonts.headline, fontSize: 28, fontWeight: 700, color: colors.white, textTransform: 'uppercase'}}>
          Store #247
        </div>
        <div style={{fontFamily: fonts.body, fontSize: 15, color: colors.coolGray, marginTop: 4}}>
          Associate answers — webhook fires — screen pop
        </div>
      </div>

      <POSScreen
        customerName="John Smith"
        loyaltyTier="Gold — 12,400 pts"
        recentOrder="Duralast Gold DG1625 Brake Pads"
        vehicle="2019 Honda Civic EX"
        enterFrame={30}
        x={1100}
        y={140}
      />

      <WaveformBar
        x={60}
        y={600}
        enterFrame={100}
        activeFrom={100}
        activeTo={280}
        color={colors.white}
        width={180}
        height={30}
      />

      <div
        style={{
          position: 'absolute',
          left: 60,
          top: 638,
          ...fadeUp(frame, 100, 15, 10),
        }}
      >
        <span style={{fontFamily: fonts.mono, fontSize: 11, color: colors.coolGray, letterSpacing: '0.06em'}}>
          ASSOCIATE — MIKE
        </span>
      </div>

      <WaveformBar
        x={300}
        y={600}
        enterFrame={200}
        activeFrom={200}
        activeTo={380}
        color={colors.yellow}
        width={180}
        height={30}
      />

      <div
        style={{
          position: 'absolute',
          left: 300,
          top: 638,
          ...fadeUp(frame, 200, 15, 10),
        }}
      >
        <span style={{fontFamily: fonts.mono, fontSize: 11, color: colors.coolGray, letterSpacing: '0.06em'}}>
          CUSTOMER — JOHN
        </span>
      </div>
    </AbsoluteFill>
  );
};
