import React from 'react';
import {useCurrentFrame, interpolate} from 'remotion';
import {colors, fonts} from '../styles/tokens';

interface TimerProps {
  startSeconds: number;
  endSeconds: number;
  countStartFrame: number;
  countDuration: number;
  colorTriggerFrame?: number;
  x?: number;
  y?: number;
  enterFrame?: number;
  hero?: boolean;
}

export const Timer: React.FC<TimerProps> = ({
  startSeconds,
  endSeconds,
  countStartFrame,
  countDuration,
  colorTriggerFrame,
  x = 960,
  y = 480,
  enterFrame = 0,
  hero = false,
}) => {
  const frame = useCurrentFrame();

  const fontSize = hero ? 120 : 72;
  const baseRingRadius = hero ? 120 : 70;
  const effectiveX = hero ? 960 : x;
  const effectiveY = hero ? 540 : y;

  const opacity = interpolate(
    frame,
    [enterFrame, enterFrame + 10],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const currentSeconds = interpolate(
    frame,
    [countStartFrame, countStartFrame + countDuration],
    [startSeconds, endSeconds],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const minutes = Math.floor(currentSeconds / 60);
  const secs = Math.floor(currentSeconds % 60);
  const display = `${minutes}:${secs.toString().padStart(2, '0')}`;

  const isPastTrigger = colorTriggerFrame != null && frame >= colorTriggerFrame;
  const textColor = isPastTrigger ? colors.yellow : colors.white;

  // Urgency: progress toward trigger (0→1)
  const urgency = colorTriggerFrame != null
    ? interpolate(frame, [countStartFrame, colorTriggerFrame], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
    : 0;

  // Pulse rate accelerates as urgency builds
  const pulseSpeed = 0.1 + urgency * 0.7;
  const pulseRing = Math.sin(frame * pulseSpeed) * 0.5 + 0.5;

  // Color shifts from white → orange → red as urgency builds
  const urgencyColor = urgency < 0.5
    ? colors.white
    : urgency < 0.8
      ? '#FF8C00'
      : '#FF4444';

  const scale = isPastTrigger
    ? interpolate(
        frame,
        [colorTriggerFrame!, colorTriggerFrame! + 8, colorTriggerFrame! + 16],
        [1, 1.3, 1],
        {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
      )
    : 1 + pulseRing * urgency * 0.04;

  const ringRadius = baseRingRadius + urgency * (hero ? 40 : 20);
  const ringOpacity = frame >= countStartFrame && !isPastTrigger ? urgency * 0.6 : 0;

  return (
    <div
      style={{
        position: 'absolute',
        left: effectiveX,
        top: effectiveY,
        opacity,
        transform: `translate(-50%, -50%) scale(${scale})`,
      }}
    >
      {/* Urgency pulse ring */}
      <svg
        width={ringRadius * 2 + 20}
        height={ringRadius * 2 + 20}
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          opacity: ringOpacity,
        }}
      >
        <circle
          cx={ringRadius + 10}
          cy={ringRadius + 10}
          r={ringRadius}
          fill="none"
          stroke={urgencyColor}
          strokeWidth={2 + urgency * 2}
          strokeDasharray={`${pulseRing * 40} ${20 + (1 - pulseRing) * 30}`}
          opacity={0.4 + pulseRing * 0.4}
        />
      </svg>

      {/* Timer text */}
      <div
        style={{
          fontFamily: fonts.mono,
          fontSize,
          fontWeight: 500,
          color: isPastTrigger ? textColor : urgencyColor,
          letterSpacing: '0.05em',
          textShadow: isPastTrigger
            ? `0 0 30px ${colors.yellow}, 0 0 60px ${colors.yellow}`
            : urgency > 0.5
              ? `0 0 ${urgency * 20}px ${urgencyColor}`
              : 'none',
        }}
      >
        {display}
      </div>
    </div>
  );
};
