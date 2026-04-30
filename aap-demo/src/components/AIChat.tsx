import React from 'react';
import {useCurrentFrame, interpolate, Easing} from 'remotion';
import {colors, fonts, fadeUp} from '../styles/tokens';

interface AIChatProps {
  messages: string[];
  enterFrame?: number;
  x?: number;
  y?: number;
  lineDelay?: number;
}

export const AIChat: React.FC<AIChatProps> = ({
  messages,
  enterFrame = 0,
  x = 1100,
  y = 250,
  lineDelay = 20,
}) => {
  const frame = useCurrentFrame();
  const cardAnim = fadeUp(frame, enterFrame, 25, 20);

  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: 680,
        opacity: cardAnim.opacity,
        transform: cardAnim.transform,
      }}
    >
      {/* Card header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          marginBottom: 16,
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            backgroundColor: colors.yellow,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: fonts.headline,
            fontSize: 14,
            fontWeight: 700,
            color: colors.black,
          }}
        >
          AI
        </div>
        <div
          style={{
            fontFamily: fonts.headline,
            fontSize: 14,
            fontWeight: 700,
            color: colors.yellow,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          AI Agent — Virtual Agent V2
        </div>
      </div>

      {/* Chat card */}
      <div
        style={{
          border: `1px solid ${colors.coolGray}`,
          borderRadius: 12,
          padding: '20px 24px',
          backgroundColor: colors.darkGray,
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
        }}
      >
        {messages.map((msg, i) => {
          const msgEnter = enterFrame + 15 + i * lineDelay;
          const msgOpacity = interpolate(
            frame,
            [msgEnter, msgEnter + 12],
            [0, 1],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
          );
          const msgY = interpolate(
            frame,
            [msgEnter, msgEnter + 12],
            [8, 0],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)},
          );

          return (
            <div
              key={i}
              style={{
                fontFamily: fonts.body,
                fontSize: 20,
                fontStyle: 'italic',
                color: colors.white,
                lineHeight: 1.5,
                opacity: msgOpacity,
                transform: `translateY(${msgY}px)`,
              }}
            >
              {msg}
            </div>
          );
        })}
      </div>
    </div>
  );
};
