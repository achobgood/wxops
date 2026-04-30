import {TextToSpeechClient} from '@google-cloud/text-to-speech';
import {writeFile, mkdir} from 'fs/promises';
import {join, dirname} from 'path';
import {fileURLToPath} from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUTPUT_DIR = join(__dirname, '..', 'public', 'audio');

const VOICE = 'en-US-Chirp3-HD-Alnilam';
const SPEAKING_RATE = 1.02;

const chapters = [
  {
    id: 'ch1-the-call',
    text: `Every day, thousands of customers call Advance Auto Parts stores across the country. Each call enters through a Webex Contact Center IVR, where the customer is instantly identified — name, loyalty tier, order history — before being connected to their local store.`,
  },
  {
    id: 'ch2-the-store',
    text: `When the associate answers, a webhook fires — and in under a second, the customer's full profile pops right onto the POS screen. The associate knows exactly who's calling and what they need.`,
  },
  {
    id: 'ch3-the-hold',
    text: `But what happens when the customer gets put on hold? A webhook starts a sixty-second countdown. When it expires, the system disconnects the associate — and the call flows back into Webex Contact Center. No dropped calls.`,
  },
  {
    id: 'ch4-the-recall',
    text: `The call returns to the same flow — every variable preserved. An AI Agent picks up: "Hi John, I see you were waiting at Store 247. I can help with those brake pads." Context-aware. No starting over.`,
  },
  {
    id: 'ch5-the-scale',
    text: `And this scales. Thirty-five thousand phones. Forty-five hundred stores. Webex Contact Center, Webex Calling, and AI Agent Studio.`,
  },
];

async function main() {
  if (!process.env.GOOGLE_CLOUD_TTS_CREDENTIALS) {
    console.error('Error: GOOGLE_CLOUD_TTS_CREDENTIALS environment variable not set.');
    console.error('Set it to your Google Cloud service account JSON.');
    process.exit(1);
  }

  const client = new TextToSpeechClient({
    credentials: JSON.parse(process.env.GOOGLE_CLOUD_TTS_CREDENTIALS),
  });

  await mkdir(OUTPUT_DIR, {recursive: true});

  for (const chapter of chapters) {
    console.log(`Generating: ${chapter.id}...`);

    const textWithPauses = chapter.text
      .replace(/\.\s+/g, '.[pause short] ')
      .replace(/\?\s+/g, '?[pause short] ')
      .replace(/—/g, ' — [pause short]');

    const [response] = await client.synthesizeSpeech({
      input: {text: textWithPauses},
      voice: {
        languageCode: 'en-US',
        name: VOICE,
      },
      audioConfig: {
        audioEncoding: 'MP3',
        speakingRate: SPEAKING_RATE,
      },
    });

    const outputPath = join(OUTPUT_DIR, `${chapter.id}.mp3`);
    await writeFile(outputPath, Buffer.from(response.audioContent));
    console.log(`  → ${outputPath}`);
  }

  console.log('\nDone! All narration files generated.');
}

main().catch((err) => {
  console.error('TTS generation failed:', err.message);
  process.exit(1);
});
