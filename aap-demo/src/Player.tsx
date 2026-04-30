import React, {useCallback, useRef, useState} from 'react';
import {Player, PlayerRef} from '@remotion/player';
import {Main} from './Main';
import {FPS, WIDTH, HEIGHT, TOTAL_FRAMES, chapters, colors, fonts} from './styles/tokens';

const CHAPTER_LIST = [
  {id: 'theCall', label: 'The Call', frame: chapters.theCall.from},
  {id: 'theStore', label: 'The Store', frame: chapters.theStore.from},
  {id: 'theHold', label: 'The Hold', frame: chapters.theHold.from},
  {id: 'theRecall', label: 'The Recall', frame: chapters.theRecall.from},
  {id: 'theScale', label: 'The Scale', frame: chapters.theScale.from},
] as const;

export const DemoPlayer: React.FC = () => {
  const playerRef = useRef<PlayerRef>(null);
  const [currentChapter, setCurrentChapter] = useState(0);

  const jumpToChapter = useCallback((index: number) => {
    const chapter = CHAPTER_LIST[index];
    playerRef.current?.seekTo(chapter.frame);
    playerRef.current?.play();
    setCurrentChapter(index);
  }, []);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 24,
        padding: 32,
        backgroundColor: colors.black,
        minHeight: '100vh',
        fontFamily: fonts.body,
      }}
    >
      {/* Title */}
      <h1
        style={{
          fontFamily: fonts.headline,
          fontSize: 28,
          fontWeight: 700,
          color: colors.white,
          margin: 0,
          textTransform: 'uppercase',
          letterSpacing: '0.02em',
        }}
      >
        Advance Auto Parts — Call Flow Demo
      </h1>

      {/* Player */}
      <div
        style={{
          border: `1px solid ${colors.coolGray}`,
          borderRadius: 8,
          overflow: 'hidden',
          boxShadow: '0 2px 16px rgba(255,207,6,0.08)',
        }}
      >
        <Player
          ref={playerRef}
          component={Main}
          durationInFrames={TOTAL_FRAMES}
          compositionWidth={WIDTH}
          compositionHeight={HEIGHT}
          fps={FPS}
          style={{width: 960, height: 540}}
          controls
        />
      </div>

      {/* Chapter navigation */}
      <div style={{display: 'flex', gap: 8}}>
        {CHAPTER_LIST.map((chapter, i) => (
          <button
            key={chapter.id}
            onClick={() => jumpToChapter(i)}
            style={{
              padding: '10px 20px',
              border: `1px solid ${currentChapter === i ? colors.yellow : colors.coolGray}`,
              borderRadius: 6,
              backgroundColor: currentChapter === i ? colors.yellow : colors.darkGray,
              color: currentChapter === i ? colors.black : colors.coolGray,
              fontFamily: fonts.body,
              fontSize: 14,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            {i + 1}. {chapter.label}
          </button>
        ))}
      </div>

      {/* Keyboard hint */}
      <div style={{fontSize: 13, color: colors.coolGray}}>
        Click a chapter to jump. Space to play/pause.
      </div>
    </div>
  );
};
