(() => {
  "use strict";

  // Vercel Functions accept a maximum 4.5 MB request body. Leave room for
  // multipart headers by keeping browser-compressed uploads below 4 MB.
  const SAFE_REQUEST_BYTES = 4 * 1024 * 1024;
  const MAX_CLIENT_FILE_BYTES = 500 * 1024 * 1024;
  const AUDIO_MIME_TYPES = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/ogg",
  ];

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

  function supportedRecorderType() {
    if (!window.MediaRecorder || typeof MediaRecorder.isTypeSupported !== "function") return "";
    return AUDIO_MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type)) || "";
  }

  function waitFor(target, eventName) {
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

  async function compressMediaToAudio(file) {
    const recorderType = supportedRecorderType();
    if (!recorderType) {
      throw new Error(
        "This browser cannot compress a large video locally. Try a shorter recording or use the Docker deployment."
      );
    }

    const sourceUrl = URL.createObjectURL(file);
    const media = document.createElement("video");
    media.preload = "auto";
    media.playsInline = true;
    media.muted = true;
    media.src = sourceUrl;

    let context;
    let recorder;
    let chunks = [];
    try {
      await waitFor(media, "loadedmetadata");
      if (!Number.isFinite(media.duration) || media.duration <= 0) {
        throw new Error("The browser could not determine the video duration.");
      }

      context = new AudioContext();
      const source = context.createMediaElementSource(media);
      const capture = context.createMediaStreamDestination();
      const silentGain = context.createGain();
      silentGain.gain.value = 0;
      source.connect(capture);
      source.connect(silentGain);
      silentGain.connect(context.destination);

      recorder = new MediaRecorder(capture.stream, {
        mimeType: recorderType,
        audioBitsPerSecond: 32000,
      });
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size) chunks.push(event.data);
      };

      const stopped = new Promise((resolve, reject) => {
        recorder.addEventListener("stop", resolve, { once: true });
        recorder.addEventListener("error", () => reject(new Error("The browser could not encode the audio.")), { once: true });
      });

      await context.resume();
      recorder.start(250);
      media.addEventListener("ended", () => {
        if (recorder.state !== "inactive") recorder.stop();
      }, { once: true });
      await media.play();
      await stopped;

      const audioBlob = new Blob(chunks, { type: recorderType });
      if (!audioBlob.size) throw new Error("No audio track was found in this video.");
      if (audioBlob.size > SAFE_REQUEST_BYTES) {
        throw new Error(
          `The compressed audio is ${readableSize(audioBlob.size)}. Try a shorter recording; the free site needs it below 4 MB.`
        );
      }
      return audioBlob;
    } finally {
      if (recorder && recorder.state !== "inactive") recorder.stop();
      if (context) await context.close().catch(() => {});
      media.pause();
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
    setStatus(`Compressing ${readableSize(file.size)} of video audio locally…`, "working");

    try {
      const audioBlob = await compressMediaToAudio(file);
      const data = new FormData(form);
      data.set("file", audioBlob, `${file.name.replace(/\.[^.]+$/, "")}.webm`);
      data.set("original_filename", file.name);
      setStatus(`Uploading ${readableSize(audioBlob.size)} of browser-compressed audio…`, "working");

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
