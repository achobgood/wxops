import React from 'react';
import {useCurrentFrame, interpolate, spring, useVideoConfig, Easing, Img, staticFile} from 'remotion';
import {colors} from '../styles/tokens';
import {ROAD_PATH} from './Highway';

interface CarProps {
  enterFrame?: number;
  startDistance?: number;
  endDistance?: number;
  travelDuration?: number;
  stopped?: boolean;
  reverse?: boolean;
  hazards?: boolean;
  turnSignal?: 'left' | 'right' | null;
}

export const Car: React.FC<CarProps> = ({
  enterFrame = 15,
  startDistance = 0,
  endDistance = 100,
  travelDuration = 60,
  stopped = false,
  reverse = false,
  hazards = false,
  turnSignal = null,
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

  const hazardBlink = hazards ? Math.sin(frame * 0.4) > 0 : false;
  const signalBlink = turnSignal ? Math.sin(frame * 0.5) > 0 : false;
  const imgSrc = (hazards && hazardBlink)
    ? staticFile('images/car-topdown-hazards.png')
    : staticFile('images/car-topdown-night.png');

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
      {/* Headlight beams */}
      <svg
        width={200}
        height={200}
        viewBox="0 0 200 200"
        style={{
          position: 'absolute',
          width: 200,
          height: 200,
          marginLeft: -100,
          marginTop: -160,
          offsetPath: `path("${ROAD_PATH}")`,
          offsetDistance: `${distance}%`,
          offsetRotate: 'auto',
          opacity: enterOpacity * (stopped ? 0.4 : 0.7),
          pointerEvents: 'none',
        }}
      >
        <defs>
          <radialGradient id="headlight-beam" cx="50%" cy="100%" r="80%">
            <stop offset="0%" stopColor={colors.white} stopOpacity="0.5" />
            <stop offset="40%" stopColor={colors.yellow} stopOpacity="0.2" />
            <stop offset="100%" stopColor={colors.yellow} stopOpacity="0" />
          </radialGradient>
        </defs>
        <ellipse cx={100} cy={60} rx={50} ry={70} fill="url(#headlight-beam)" />
      </svg>

      {/* Car image */}
      <Img
        src={imgSrc}
        style={{
          position: 'absolute',
          width: 90,
          height: 90,
          marginLeft: -45,
          marginTop: -45,
          offsetPath: `path("${ROAD_PATH}")`,
          offsetDistance: `${distance}%`,
          offsetRotate: 'auto',
          opacity: enterOpacity,
          transform: `scale(${enterScale * 0.9}) ${reverse ? 'scaleX(-1)' : ''}`,
          transformOrigin: 'center center',
          filter: 'drop-shadow(0 0 12px rgba(255, 207, 6, 0.3))',
        }}
      />

      {/* Turn signal indicator */}
      {turnSignal && signalBlink && (
        <div
          style={{
            position: 'absolute',
            width: 12,
            height: 12,
            borderRadius: '50%',
            backgroundColor: '#FFA500',
            boxShadow: '0 0 12px 4px rgba(255, 165, 0, 0.6)',
            offsetPath: `path("${ROAD_PATH}")`,
            offsetDistance: `${distance}%`,
            offsetRotate: 'auto',
            marginLeft: turnSignal === 'left' ? -50 : 38,
            marginTop: -5,
            opacity: enterOpacity,
          }}
        />
      )}
    </div>
  );
};
