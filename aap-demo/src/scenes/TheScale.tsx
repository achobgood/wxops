import React from 'react';
import {AbsoluteFill, useCurrentFrame, interpolate, Easing} from 'remotion';
import {backgroundStyle, colors, fonts, fadeUp, fadeIn} from '../styles/tokens';
import {StoreMap} from '../components/StoreMap';

export const TheScale: React.FC = () => {
  const frame = useCurrentFrame();

  const statsAnim1 = fadeUp(frame, 100, 30, 20);
  const statsAnim2 = fadeUp(frame, 115, 30, 20);
  const closingRuleWidth = interpolate(
    frame,
    [200, 280],
    [0, 60],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)},
  );

  const mapOpacity = fadeIn(frame, 20, 30);

  return (
    <AbsoluteFill style={backgroundStyle}>
      {/* Network map reveals */}
      <div style={{opacity: mapOpacity}}>
        <StoreMap revealStartFrame={30} revealDuration={120} />
      </div>

      {/* Stats overlay */}
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
        <div style={{textAlign: 'center', opacity: statsAnim1.opacity, transform: statsAnim1.transform}}>
          <div style={{fontFamily: fonts.headline, fontSize: 72, fontWeight: 700, color: colors.white, textTransform: 'uppercase'}}>
            35,000
          </div>
          <div style={{fontFamily: fonts.body, fontSize: 20, color: colors.yellow, marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.1em'}}>
            phones
          </div>
        </div>
        <div style={{textAlign: 'center', opacity: statsAnim2.opacity, transform: statsAnim2.transform}}>
          <div style={{fontFamily: fonts.headline, fontSize: 72, fontWeight: 700, color: colors.white, textTransform: 'uppercase'}}>
            4,500
          </div>
          <div style={{fontFamily: fonts.body, fontSize: 20, color: colors.yellow, marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.1em'}}>
            stores
          </div>
        </div>
      </div>

      {/* Subtitle */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 220,
          textAlign: 'center',
          ...fadeUp(frame, 140, 20, 20),
        }}
      >
        <div style={{fontFamily: fonts.body, fontSize: 20, color: colors.coolGray}}>
          One webhook. Stateless middleware. Horizontal scale.
        </div>
      </div>

      {/* Closing horizontal rule */}
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

      {/* Logo area */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 60,
          textAlign: 'center',
          ...fadeUp(frame, 250, 15, 20),
        }}
      >
        <span style={{fontFamily: fonts.headline, fontSize: 16, fontWeight: 700, color: colors.coolGray, letterSpacing: '0.12em', textTransform: 'uppercase'}}>
          Webex Contact Center + Webex Calling + AI Agent Studio
        </span>
      </div>
    </AbsoluteFill>
  );
};
