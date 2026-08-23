(() => {
  const form = document.getElementById('speech-form');
  if (!form) return;

  const textField = document.getElementById('speech-text');
  const voiceField = document.getElementById('speech-voice');
  const speedField = document.getElementById('speech-speed');
  const pitchField = document.getElementById('speech-pitch');
  const button = document.getElementById('speech-submit');
  const status = document.getElementById('speech-status');
  const workerPath = '/static/vendor/espeakng/espeakng.worker.js';
  const sampleRate = 22050;
  let tts;
  let readyPromise;

  const setStatus = (message, tone = 'quiet') => {
    status.textContent = message;
    status.dataset.tone = tone;
  };

  const ensureEngine = () => {
    if (readyPromise) return readyPromise;
    readyPromise = new Promise((resolve, reject) => {
      try {
        tts = new eSpeakNG(workerPath, resolve);
      } catch (error) {
        reject(error);
      }
    });
    return readyPromise;
  };

  const writeAscii = (view, offset, value) => {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index));
    }
  };

  const wavBlob = (chunks) => {
    const samples = new Float32Array(chunks.reduce((total, chunk) => total + chunk.length, 0));
    let offset = 0;
    chunks.forEach((chunk) => {
      samples.set(chunk, offset);
      offset += chunk.length;
    });

    // espeakng.js returns two identical channels. Keep one channel in the file.
    const channelCount = 1;
    const frameCount = Math.floor(samples.length / 2);
    const bytesPerSample = 2;
    const dataSize = frameCount * channelCount * bytesPerSample;
    const buffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(buffer);
    writeAscii(view, 0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    writeAscii(view, 8, 'WAVE');
    writeAscii(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, channelCount, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * channelCount * bytesPerSample, true);
    view.setUint16(32, channelCount * bytesPerSample, true);
    view.setUint16(34, 16, true);
    writeAscii(view, 36, 'data');
    view.setUint32(40, dataSize, true);

    for (let index = 0; index < frameCount; index += 1) {
      const sample = Math.max(-1, Math.min(1, samples[index * 2]));
      const pcm = sample < 0 ? sample * 32768 : sample * 32767;
      view.setInt16(44 + index * bytesPerSample, pcm, true);
    }
    return new Blob([buffer], { type: 'audio/wav' });
  };

  const synthesize = (text, voice, speed, pitch) => new Promise((resolve, reject) => {
    const chunks = [];
    try {
      tts.set_rate(speed);
      tts.set_pitch(pitch);
      tts.set_voice(voice);
      tts.synthesize(text, (samples) => {
        if (!samples) {
          resolve(wavBlob(chunks));
          return;
        }
        chunks.push(new Float32Array(samples));
      });
    } catch (error) {
      reject(error);
    }
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const text = textField.value.trim();
    const speed = Number(speedField.value);
    const pitch = Number(pitchField.value);
    if (!text) {
      setStatus('Please enter some text to speak.', 'error');
      textField.focus();
      return;
    }
    if (text.length > Number(textField.maxLength)) {
      setStatus('That passage is longer than the browser limit.', 'error');
      return;
    }
    if (!Number.isInteger(speed) || speed < 80 || speed > 400 || !Number.isInteger(pitch) || pitch < 0 || pitch > 99) {
      setStatus('Check the speed and pitch values, then try again.', 'error');
      return;
    }

    button.disabled = true;
    button.classList.add('is-working');
    setStatus('Loading the private speech engine…');
    try {
      await ensureEngine();
      setStatus('Synthesizing in this browser…');
      const audio = await synthesize(text, voiceField.value, speed, pitch);
      const url = URL.createObjectURL(audio);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'media-to-text-private-speech.wav';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setStatus('WAV download ready. Your text stayed in this browser.', 'success');
    } catch (error) {
      console.error(error);
      setStatus('The local speech engine could not start. Try the Docker deployment or refresh the page.', 'error');
    } finally {
      button.disabled = false;
      button.classList.remove('is-working');
    }
  });
})();
