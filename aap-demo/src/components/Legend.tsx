import React from 'react';
import {useCurrentFrame} from 'remotion';
import {colors, fonts, fadeUp} from '../styles/tokens';

interface LegendItem {
  color: string;
  label: string;
}

interface LegendProps {
  items: LegendItem[];
  x: number;
  y: number;
  enterFrame?: number;
}

export const Legend: React.FC<LegendProps> = ({
  items,
  x,
  y,
  enterFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const anim = fadeUp(frame, enterFrame, 15, 15);

  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        opacity: anim.opacity,
        transform: anim.transform,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        padding: '12px 16px',
        border: `1px solid ${colors.coolGray}`,
        borderRadius: 8,
        backgroundColor: colors.darkGray,
      }}
    >
      {items.map((item) => (
        <div
          key={item.label}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <div
            style={{
              width: 12,
              height: 12,
              borderRadius: 3,
              backgroundColor: item.color,
              flexShrink: 0,
            }}
          />
          <span
            style={{
              fontFamily: fonts.body,
              fontSize: 14,
              color: colors.coolGray,
            }}
          >
            {item.label}
          </span>
        </div>
      ))}
    </div>
  );
};
