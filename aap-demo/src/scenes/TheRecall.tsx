import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {backgroundStyle, colors, fonts, fadeUp} from '../styles/tokens';
import {Highway} from '../components/Highway';
import {Car} from '../components/Car';
import {RoadSign} from '../components/RoadSign';
import {AIChat} from '../components/AIChat';

export const TheRecall: React.FC = () => {
  const frame = useCurrentFrame();
  const recallLabel = fadeUp(frame, 10, 25, 15);

  return (
    <AbsoluteFill style={backgroundStyle}>
      {/* Highway fully drawn */}
      <Highway progress={1} />

      {/* Car U-turns: drives from ~58% back toward ~30% (reversed) */}
      <Car
        enterFrame={0}
        startDistance={58}
        endDistance={30}
        travelDuration={70}
        reverse
      />

      {/* Road sign: AI Agent */}
      <RoadSign label="AI Agent" x={420} y={360} enterFrame={40} variant="emphasis" />
      <RoadSign label="Virtual Agent V2" x={380} y={460} enterFrame={50} />

      {/* Recall label */}
      <div
        style={{
          position: 'absolute',
          left: 100,
          top: 120,
          opacity: recallLabel.opacity,
          transform: recallLabel.transform,
        }}
      >
        <div style={{fontFamily: fonts.headline, fontSize: 38, fontWeight: 700, color: colors.yellow, textTransform: 'uppercase', letterSpacing: '0.02em'}}>
          Call Returns to Flow
        </div>
        <div style={{fontFamily: fonts.body, fontSize: 17, color: colors.coolGray, marginTop: 6}}>
          Bridged Transfer detected disconnect — same flow execution, all variables preserved
        </div>
      </div>

      {/* AI Chat card */}
      <AIChat
        messages={[
          '"Hi John, I see you were waiting at Store 247."',
          '"I can help you with those ceramic brake pads for your 2019 Civic."',
          '"Would you like me to check availability at a nearby store?"',
        ]}
        enterFrame={60}
        x={1050}
        y={200}
        lineDelay={25}
      />

      {/* Context preservation note */}
      <div
        style={{
          position: 'absolute',
          right: 100,
          bottom: 100,
          ...fadeUp(frame, 120, 15, 15),
        }}
      >
        <div
          style={{
            border: `1px solid ${colors.coolGray}`,
            borderRadius: 8,
            padding: '12px 18px',
            backgroundColor: colors.darkGray,
          }}
        >
          <div style={{fontFamily: fonts.headline, fontSize: 14, fontWeight: 700, color: colors.yellow, textTransform: 'uppercase', letterSpacing: '0.05em'}}>
            Context Preserved:
          </div>
          <div style={{fontFamily: fonts.mono, fontSize: 13, color: colors.coolGray, marginTop: 6, lineHeight: 1.6}}>
            customer_name, loyalty_tier, store_number,<br />
            order_history, hold_duration
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
