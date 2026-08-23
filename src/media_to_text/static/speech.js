(() => {
  const form = document.getElementById('speech-form');
  if (!form) return;

  const textField = document.getElementById('speech-text');
  const voiceField = document.getElementById('speech-voice');
  const speedField = document.getElementById('speech-speed');
  const pitchField = document.getElementById('speech-pitch');
  const button = document.getElementById('speech-submit');
  const status = document.getElementById('speech-status');
  const listenVoiceField = document.getElementById('listen-voice');
  const listenButton = document.getElementById('listen-speech');
  const pauseButton = document.getElementById('pause-speech');
  const stopButton = document.getElementById('stop-speech');
  const listenStatus = document.getElementById('listen-status');
  const player = document.getElementById('speech-player');
  const playerWrap = document.getElementById('speech-player-wrap');
  const downloadLink = document.getElementById('speech-download-link');
  const workerPath = '/static/vendor/espeakng/espeakng.worker.js';
  const sampleRate = 22050;
  let tts;
  let readyPromise;
  let deviceVoices = [];
  let currentAudioUrl;

  const setStatus = (message, tone = 'quiet') => {
    status.textContent = message;
    status.dataset.tone = tone;
  };

  const setListenStatus = (message, tone = 'quiet') => {
    listenStatus.textContent = message;
    listenStatus.dataset.tone = tone;
  };

  const populateDeviceVoices = () => {
    if (!('speechSynthesis' in window) || !listenVoiceField) {
      setListenStatus('Device voice preview is unavailable in this browser.', 'error');
      listenButton.disabled = true;
      pauseButton.disabled = true;
      stopButton.disabled = true;
      return;
    }
    deviceVoices = window.speechSynthesis.getVoices();
    if (!deviceVoices.length) {
      setListenStatus('Loading voices available on this device…');
      return;
    }
    const previousValue = listenVoiceField.value;
    listenVoiceField.replaceChildren();
    deviceVoices.forEach((voice, index) => {
      const option = document.createElement('option');
      option.value = String(index);
      option.textContent = `${voice.name} · ${voice.lang}${voice.default ? ' · default' : ''}`;
      listenVoiceField.appendChild(option);
    });
    const englishIndex = deviceVoices.findIndex((voice) => /^en(-|_)/i.test(voice.lang));
    listenVoiceField.value = deviceVoices[Number(previousValue)] ? previousValue : String(Math.max(englishIndex, 0));
    setListenStatus('Uses a voice available through your browser or operating system.');
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

  const stopDeviceSpeech = () => {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  };

  if ('speechSynthesis' in window) {
    populateDeviceVoices();
    window.speechSynthesis.addEventListener('voiceschanged', populateDeviceVoices);
  } else {
    populateDeviceVoices();
  }

  listenButton.addEventListener('click', () => {
    const text = textField.value.trim();
    if (!text) {
      setListenStatus('Please enter some text to listen to.', 'error');
      textField.focus();
      return;
    }
    stopDeviceSpeech();
    const utterance = new SpeechSynthesisUtterance(text);
    const selectedVoice = deviceVoices[Number(listenVoiceField.value)];
    if (selectedVoice) utterance.voice = selectedVoice;
    utterance.rate = Math.max(0.5, Math.min(2, Number(speedField.value) / 175));
    utterance.pitch = Math.max(0.5, Math.min(2, Number(pitchField.value) / 50));
    utterance.onstart = () => setListenStatus('Playing with the selected device voice…', 'success');
    utterance.onend = () => setListenStatus('Listen preview finished.');
    utterance.onerror = () => setListenStatus('The device voice could not play this passage.', 'error');
    window.speechSynthesis.speak(utterance);
  });

  pauseButton.addEventListener('click', () => {
    if (!('speechSynthesis' in window)) return;
    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
      setListenStatus('Resumed device-voice preview.');
    } else {
      window.speechSynthesis.pause();
      setListenStatus('Device-voice preview paused.');
    }
  });

  stopButton.addEventListener('click', () => {
    stopDeviceSpeech();
    setListenStatus('Device-voice preview stopped.');
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
      if (currentAudioUrl) URL.revokeObjectURL(currentAudioUrl);
      currentAudioUrl = URL.createObjectURL(audio);
      player.src = currentAudioUrl;
      downloadLink.href = currentAudioUrl;
      playerWrap.hidden = false;
      playerWrap.classList.remove('hidden');
      const link = document.createElement('a');
      link.href = currentAudioUrl;
      link.download = 'media-to-text-private-speech.wav';
      document.body.appendChild(link);
      link.click();
      link.remove();
      setStatus('WAV download ready. You can also listen below; your text stayed in this browser.', 'success');
    } catch (error) {
      console.error(error);
      setStatus('The local speech engine could not start. Try refreshing the page.', 'error');
    } finally {
      button.disabled = false;
      button.classList.remove('is-working');
    }
  });
})();
