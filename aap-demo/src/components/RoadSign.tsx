import React from 'react';
import {useCurrentFrame} from 'remotion';
import {colors, fonts, fadeUp} from '../styles/tokens';

interface RoadSignProps {
  label: string;
  x: number;
  y: number;
  enterFrame?: number;
  variant?: 'default' | 'emphasis';
}

export const RoadSign: React.FC<RoadSignProps> = ({
  label,
  x,
  y,
  enterFrame = 0,
  variant = 'default',
}) => {
  const frame = useCurrentFrame();
  const anim = fadeUp(frame, enterFrame, 20, 15);
  const borderColor = variant === 'emphasis' ? colors.yellow : colors.coolGray;
  const textColor = variant === 'emphasis' ? colors.yellow : colors.white;

  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        opacity: anim.opacity,
        transform: anim.transform,
      }}
    >
      <div
        style={{
          border: `2px solid ${borderColor}`,
          borderRadius: 6,
          padding: '8px 16px',
          backgroundColor: colors.darkGray,
          fontFamily: fonts.headline,
          fontSize: 16,
          fontWeight: 700,
          color: textColor,
          letterSpacing: '0.05em',
          textTransform: 'uppercase' as const,
          whiteSpace: 'nowrap',
        }}
      >
        {label}
      </div>
      {/* Sign post */}
      <div
        style={{
          width: 2,
          height: 20,
          backgroundColor: colors.coolGray,
          margin: '0 auto',
          opacity: 0.3,
        }}
      />
    </div>
  );
};
