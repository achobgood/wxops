import React from 'react';
import {AbsoluteFill, useCurrentFrame, interpolate, Easing} from 'remotion';
import {backgroundStyle, colors, fonts, fadeUp} from '../styles/tokens';
import {Highway} from '../components/Highway';
import {Car} from '../components/Car';
import {Timer} from '../components/Timer';

export const TheHold: React.FC = () => {
  const frame = useCurrentFrame();

  const TIMEOUT_FRAME = 390;
  const TIMER_START = 60;
  const TIMER_COUNT_DURATION = TIMEOUT_FRAME - TIMER_START;

  const bgYellowOpacity = interpolate(
    frame,
    [TIMEOUT_FRAME, TIMEOUT_FRAME + 30],
    [0, 0.1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const ruleWidth = interpolate(
    frame,
    [TIMEOUT_FRAME + 5, TIMEOUT_FRAME + 40],
    [0, 100],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)},
  );

  const holdLabel = fadeUp(frame, 30, 20, 15);
  const timeoutLabel = fadeUp(frame, TIMEOUT_FRAME + 10, 25, 20);

  return (
    <AbsoluteFill style={backgroundStyle}>
      {/* Yellow flash overlay on timeout */}
      <AbsoluteFill
        style={{
          backgroundColor: colors.yellow,
          opacity: bgYellowOpacity,
        }}
      />

      {/* Highway fully drawn */}
      <Highway progress={1} />

      {/* Car stopped at ~58% (where it arrived in Ch 2) */}
      <Car enterFrame={0} startDistance={58} endDistance={58} travelDuration={1} stopped />

      {/* Hold label */}
      <div
        style={{
          position: 'absolute',
          left: 200,
          top: 200,
          opacity: holdLabel.opacity,
          transform: holdLabel.transform,
        }}
      >
        <div style={{fontFamily: fonts.headline, fontSize: 42, fontWeight: 700, color: colors.white, textTransform: 'uppercase', letterSpacing: '0.02em'}}>
          Customer on Hold
        </div>
        <div style={{fontFamily: fonts.body, fontSize: 18, color: colors.coolGray, marginTop: 6}}>
          Webhook detects hold event — timer starts
        </div>
      </div>

      {/* Countdown timer */}
      <Timer
        startSeconds={47}
        endSeconds={60}
        countStartFrame={TIMER_START}
        countDuration={TIMER_COUNT_DURATION}
        colorTriggerFrame={TIMEOUT_FRAME}
        x={960}
        y={540}
        enterFrame={TIMER_START - 10}
      />

      {/* Horizontal rule on timeout */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: 640,
          transform: 'translateX(-50%)',
          width: `${ruleWidth}%`,
          height: 2,
          backgroundColor: colors.yellow,
          opacity: 0.7,
        }}
      />

      {/* Timeout label */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 180,
          textAlign: 'center',
          opacity: timeoutLabel.opacity,
          transform: timeoutLabel.transform,
        }}
      >
        <div style={{fontFamily: fonts.body, fontSize: 20, fontWeight: 600, color: colors.yellow}}>
          60-second timeout — Service App hangs up associate's leg
        </div>
        <div style={{fontFamily: fonts.body, fontSize: 16, color: colors.coolGray, marginTop: 4}}>
          Bridged Transfer detects disconnect — call returns to WxCC flow
        </div>
      </div>
    </AbsoluteFill>
  );
};
