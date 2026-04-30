import React from 'react';
import {useCurrentFrame, interpolate, spring, useVideoConfig, Easing} from 'remotion';
import {colors} from '../styles/tokens';
import {ROAD_PATH} from './Highway';

interface CarProps {
  enterFrame?: number;
  startDistance?: number;
  endDistance?: number;
  travelDuration?: number;
  color?: string;
  stopped?: boolean;
  reverse?: boolean;
}

export const Car: React.FC<CarProps> = ({
  enterFrame = 15,
  startDistance = 0,
  endDistance = 100,
  travelDuration = 60,
  color = colors.white,
  stopped = false,
  reverse = false,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const enterOpacity = interpolate(frame, [enterFrame, enterFrame + 10], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const enterScale = spring({
    fps,
    frame: frame - enterFrame,
    config: {damping: 80, stiffness: 200},
  });

  const distance = stopped
    ? startDistance
    : interpolate(
        frame,
        [enterFrame + 5, enterFrame + 5 + travelDuration],
        [startDistance, endDistance],
        {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: Easing.inOut(Easing.cubic),
        },
      );

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: 1920,
        height: 1080,
      }}
    >
      <svg
        width={40}
        height={24}
        viewBox="0 0 40 24"
        style={{
          position: 'absolute',
          offsetPath: `path("${ROAD_PATH}")`,
          offsetDistance: `${distance}%`,
          offsetRotate: 'auto',
          opacity: enterOpacity,
          transform: `scale(${enterScale}) ${reverse ? 'scaleX(-1)' : ''}`,
          transformOrigin: 'center center',
        }}
      >
        {/* Simple top-down car silhouette */}
        <rect x={4} y={2} width={32} height={20} rx={6} fill={color} />
        <rect x={8} y={5} width={10} height={6} rx={2} fill={colors.coolGray} opacity={0.4} />
        <rect x={22} y={5} width={10} height={6} rx={2} fill={colors.coolGray} opacity={0.4} />
        <rect x={8} y={13} width={10} height={6} rx={2} fill={colors.coolGray} opacity={0.4} />
        <rect x={22} y={13} width={10} height={6} rx={2} fill={colors.coolGray} opacity={0.4} />
        {/* Wheels */}
        <rect x={6} y={0} width={6} height={4} rx={1} fill={colors.yellow} opacity={0.8} />
        <rect x={28} y={0} width={6} height={4} rx={1} fill={colors.yellow} opacity={0.8} />
        <rect x={6} y={20} width={6} height={4} rx={1} fill={colors.yellow} opacity={0.8} />
        <rect x={28} y={20} width={6} height={4} rx={1} fill={colors.yellow} opacity={0.8} />
      </svg>
    </div>
  );
};
