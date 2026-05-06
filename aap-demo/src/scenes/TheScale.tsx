import React from 'react';
import {AbsoluteFill, Loop, OffthreadVideo, staticFile, useCurrentFrame, interpolate, Easing} from 'remotion';
import {backgroundStyle, colors, fonts, fadeUp, fadeIn} from '../styles/tokens';
import {AnimatedCounter} from '../components/AnimatedCounter';
import {StepBadge} from '../components/StepBadge';

export const TheScale: React.FC = () => {
  const frame = useCurrentFrame();

  const dotScale = interpolate(frame, [0, 40], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.cubic),
  });
  const dotOpacity = interpolate(frame, [0, 40], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const mapScale = interpolate(frame, [30, 90], [1.4, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const mapOpacity = fadeIn(frame, 30, 30);

  const pulseIntensity = interpolate(frame % 45, [0, 22, 45], [0.7, 1, 0.7], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const closingRuleWidth = interpolate(frame, [400, 500], [0, 60], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill style={backgroundStyle}>
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          width: 10,
          height: 10,
          borderRadius: '50%',
          backgroundColor: colors.yellow,
          boxShadow: `0 0 20px ${colors.yellow}`,
          transform: `translate(-50%, -50%) scale(${dotScale})`,
          opacity: dotOpacity,
        }}
      />

      <StepBadge step={5} label="The Scale" enterFrame={5} />

      <Loop durationInFrames={240}>
        <OffthreadVideo
          src={staticFile('video/us-network.mp4')}
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            opacity: mapOpacity * pulseIntensity,
            transform: `scale(${mapScale})`,
            filter: `brightness(${0.8 + pulseIntensity * 0.4})`,
          }}
          volume={0}
        />
      </Loop>

      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 380,
          display: 'flex',
          justifyContent: 'center',
          gap: 120,
        }}
      >
        <AnimatedCounter value={35000} label="phones" startFrame={150} duration={50} />
        <AnimatedCounter value={4500} label="stores" startFrame={170} duration={45} />
      </div>

      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 220,
          textAlign: 'center',
          ...fadeUp(frame, 280, 20, 20),
        }}
      >
        <div style={{fontFamily: fonts.body, fontSize: 22, color: colors.coolGray}}>
          Every call. Every store. Every time.
        </div>
      </div>

      <div
        style={{
          position: 'absolute',
          left: '50%',
          bottom: 140,
          transform: 'translateX(-50%)',
          width: `${closingRuleWidth}%`,
          height: 1,
          backgroundColor: colors.yellow,
          opacity: 0.5,
        }}
      />

      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 60,
          textAlign: 'center',
          ...fadeUp(frame, 480, 15, 20),
        }}
      >
        <span style={{fontFamily: fonts.headline, fontSize: 16, fontWeight: 700, color: colors.coolGray, letterSpacing: '0.12em', textTransform: 'uppercase'}}>
          Webex Contact Center + Webex Calling + AI Agent Studio
        </span>
      </div>
    </AbsoluteFill>
  );
};
