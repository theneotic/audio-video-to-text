(() => {
  "use strict";

  // Vercel Functions accept a maximum 4.5 MB request body. Leave room for
  // multipart headers by keeping browser-prepared uploads below 4 MB.
  const SAFE_REQUEST_BYTES = 4 * 1024 * 1024;
  const MAX_CLIENT_FILE_BYTES = 500 * 1024 * 1024;
  const TARGET_SAMPLE_RATE = 8000;
  const EXTRACTION_RATE = 4;

  const byId = (id) => document.getElementById(id);

  function setStatus(message, tone = "quiet") {
    const status = byId("upload-status");
    if (!status) return;
    status.textContent = message;
    status.dataset.tone = tone;
  }

  function readableSize(bytes) {
    if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function waitFor(target, eventName) {
    if (eventName === "loadedmetadata" && target.readyState >= 1) {
      return Promise.resolve();
    }
    return new Promise((resolve, reject) => {
      const onEvent = () => {
        cleanup();
        resolve();
      };
      const onError = () => {
        cleanup();
        reject(new Error("The browser could not read this media file."));
      };
      const cleanup = () => {
        target.removeEventListener(eventName, onEvent);
        target.removeEventListener("error", onError);
      };
      target.addEventListener(eventName, onEvent, { once: true });
      target.addEventListener("error", onError, { once: true });
    });
  }

  function writeAscii(view, offset, text) {
    for (let index = 0; index < text.length; index += 1) {
      view.setUint8(offset + index, text.charCodeAt(index));
    }
  }

  function wavBlob(samples, sampleRate) {
    // Compact unsigned 8-bit mono PCM is intentionally used here. It keeps
    // several minutes of speech below Vercel's request-body limit while still
    // preserving the frequency range needed for speech recognition.
    const buffer = new ArrayBuffer(44 + samples.length);
    const view = new DataView(buffer);
    writeAscii(view, 0, "RIFF");
    view.setUint32(4, 36 + samples.length, true);
    writeAscii(view, 8, "WAVE");
    writeAscii(view, 12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate, true);
    view.setUint16(32, 1, true);
    view.setUint16(34, 8, true);
    writeAscii(view, 36, "data");
    view.setUint32(40, samples.length, true);
    for (let index = 0; index < samples.length; index += 1) {
      const normalized = Math.max(-1, Math.min(1, samples[index]));
      view.setUint8(44 + index, Math.round((normalized + 1) * 127.5));
    }
    return new Blob([buffer], { type: "audio/wav" });
  }

  async function compressMediaToAudio(file) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) {
      throw new Error(
        "This browser cannot extract audio locally. Try a shorter recording or use the Docker deployment."
      );
    }

    const sourceUrl = URL.createObjectURL(file);
    const media = document.createElement("video");
    media.preload = "auto";
    media.playsInline = true;
    media.muted = true;
    media.src = sourceUrl;

    let context;
    let processor;
    let samples = [];
    let sum = 0;
    let count = 0;
    let stopped = false;

    try {
      await waitFor(media, "loadedmetadata");
      if (!Number.isFinite(media.duration) || media.duration <= 0) {
        throw new Error("The browser could not determine the media duration.");
      }

      context = new AudioContextClass();
      const step = Math.max(1, Math.round(context.sampleRate / TARGET_SAMPLE_RATE));
      const outputSampleRate = Math.round(context.sampleRate / step);
      const estimatedBytes = Math.ceil(media.duration * outputSampleRate) + 44;
      if (estimatedBytes > SAFE_REQUEST_BYTES) {
        throw new Error(
          `This recording is ${Math.round(media.duration / 60)} minutes long. The free site needs audio under 4 MB; use the Docker deployment for longer recordings.`
        );
      }

      const source = context.createMediaElementSource(media);
      // ScriptProcessorNode remains broadly available in Chromium and lets us
      // collect decoded media audio without uploading the original video.
      processor = context.createScriptProcessor(4096, 2, 1);
      const silentGain = context.createGain();
      silentGain.gain.value = 0;
      source.connect(processor);
      processor.connect(silentGain);
      silentGain.connect(context.destination);

      processor.onaudioprocess = (event) => {
        const input = event.inputBuffer;
        const channels = input.numberOfChannels;
        const frames = input.length;
        const first = input.getChannelData(0);
        const second = channels > 1 ? input.getChannelData(1) : first;
        for (let index = 0; index < frames; index += 1) {
          sum += (first[index] + second[index]) / 2;
          count += 1;
          if (count >= step) {
            samples.push(sum / count);
            sum = 0;
            count = 0;
          }
        }
      };

      const complete = new Promise((resolve, reject) => {
        media.addEventListener("ended", () => {
          stopped = true;
          resolve();
        }, { once: true });
        media.addEventListener("error", () => reject(new Error("The browser could not play this media file.")), { once: true });
      });

      await context.resume();
      media.playbackRate = EXTRACTION_RATE;
      await media.play();
      await complete;
      if (!samples.length) throw new Error("No audio track was found in this media file.");
      return wavBlob(samples, outputSampleRate);
    } finally {
      if (!stopped && media && !media.paused) media.pause();
      if (processor) processor.disconnect();
      if (context) await context.close().catch(() => {});
      media.removeAttribute("src");
      media.load();
      URL.revokeObjectURL(sourceUrl);
    }
  }

  async function submitLargeFile(form, file) {
    const button = form.querySelector("button[type=submit]");
    const loading = byId("loading-state");
    const panel = byId("app-panel");
    if (!panel) return;

    if (file.size > MAX_CLIENT_FILE_BYTES) {
      setStatus("That file is larger than the 500 MB application limit.", "error");
      return;
    }

    if (button) button.disabled = true;
    if (loading) loading.classList.remove("htmx-indicator");
    setStatus(`Preparing ${readableSize(file.size)} of media locally…`, "working");

    try {
      const audioBlob = await compressMediaToAudio(file);
      const data = new FormData(form);
      data.set("file", audioBlob, `${file.name.replace(/\.[^.]+$/, "")}.wav`);
      data.set("original_filename", file.name);
      setStatus(`Uploading ${readableSize(audioBlob.size)} of browser-prepared audio…`, "working");

      const response = await fetch(form.action, {
        method: "POST",
        body: data,
        headers: { "HX-Request": "true", "X-Upload-Mode": "browser-compressed" },
      });
      const html = await response.text();
      panel.innerHTML = html;
      if (!response.ok) return;
      setStatus("Transcription complete.", "success");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "The browser could not prepare this upload.", "error");
    } finally {
      if (button) button.disabled = false;
      if (loading) loading.classList.add("htmx-indicator");
    }
  }

  document.addEventListener("change", (event) => {
    if (event.target?.id !== "file") return;
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > SAFE_REQUEST_BYTES) {
      setStatus(
        `${readableSize(file.size)} selected. The browser will extract and compress its audio privately before upload.`,
        "working"
      );
    } else {
      setStatus("");
    }
  });

  // Capture before HTMX's bubbling submit listener so only oversized files use
  // the browser-compression path. Small files keep the normal HTMX workflow.
  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || form.id !== "transcription-form") return;
    const file = form.querySelector("#file")?.files?.[0];
    if (!file || file.size <= SAFE_REQUEST_BYTES) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    submitLargeFile(form, file);
  }, true);
})();
