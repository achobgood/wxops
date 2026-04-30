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
}) => {
  const frame = useCurrentFrame();

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

  const scale = isPastTrigger
    ? interpolate(
        frame,
        [colorTriggerFrame!, colorTriggerFrame! + 8, colorTriggerFrame! + 16],
        [1, 1.15, 1],
        {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
      )
    : 1;

  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        opacity,
        transform: `translate(-50%, -50%) scale(${scale})`,
        fontFamily: fonts.mono,
        fontSize: 72,
        fontWeight: 500,
        color: textColor,
        letterSpacing: '0.05em',
        transition: 'color 0.3s ease',
      }}
    >
      {display}
    </div>
  );
};
