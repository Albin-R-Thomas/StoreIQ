import { useEffect, useRef, useState } from "react";
import { LoaderCircle, Mic, RotateCcw, Square, X } from "lucide-react";

type Props = {
  customerId: string; version: number; disabled: boolean;
  onReady: (text: string) => void;
  onBusy: (busy: boolean) => void;
  onStatus: (text: string, error?: boolean) => void;
};
type Recording = { recorder: MediaRecorder; stream: MediaStream; canceled: boolean; timer?: number };
type Clip = { audio: Blob; id: string; version: number };

export function VoiceNote({ customerId, version, disabled, onReady, onBusy, onStatus }: Props) {
  const [phase, setPhase] = useState<"idle" | "requesting" | "recording" | "processing" | "retry">("idle");
  const recording = useRef<Recording | null>(null);
  const clip = useRef<Clip | null>(null);
  const controller = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const locked = useRef(false);

  function release(session: Recording | null, cancel = false) {
    if (!session) return;
    session.canceled ||= cancel;
    window.clearTimeout(session.timer);
    if (session.recorder.state !== "inactive") session.recorder.stop();
    session.stream.getTracks().forEach(track => track.stop());
  }
  useEffect(() => () => {
    generation.current++;
    release(recording.current, true);
    controller.current?.abort();
    clip.current = null;
  }, [customerId]);

  function cancel() {
    generation.current++;
    release(recording.current, true);
    recording.current = null;
    clip.current = null;
    locked.current = false;
    setPhase("idle");
    onBusy(false);
    onStatus("Recording discarded.");
  }

  async function process(current: Clip) {
    const abort = new AbortController();
    controller.current = abort;
    locked.current = true;
    setPhase("processing");
    onBusy(true);
    onStatus("Transcribing and translating to English…");
    try {
      const query = new URLSearchParams({ event_id: current.id, version: String(current.version),
        source_language: "auto", target_language: "en" });
      const response = await fetch(`/api/customers/${customerId}/voice?${query}`, {
        method: "POST", credentials: "same-origin", signal: abort.signal,
        headers: { "Content-Type": current.audio.type }, body: current.audio,
      });
      const draft = await response.json();
      if (!response.ok) throw new Error(typeof draft.detail === "string" ? draft.detail : "Voice processing failed.");
      if (typeof draft.translation !== "string" || !draft.translation.trim()) {
        throw new Error("No English translation returned.");
      }
      if (abort.signal.aborted) return;
      onReady(draft.translation.trim());
      onStatus("Voice note translated to English. Review it, then send.");
      clip.current = null;
      setPhase("idle");
    } catch (error) {
      if (!abort.signal.aborted) {
        onStatus(`${error instanceof Error ? error.message : "Voice processing failed."} Retry or discard the recording.`, true);
        setPhase("retry");
      }
    } finally {
      controller.current = null;
      if (!abort.signal.aborted) { locked.current = false; onBusy(false); }
    }
  }

  async function start() {
    if (disabled || locked.current) return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      onStatus("Microphone recording needs a supported browser on localhost or HTTPS.", true);
      return;
    }
    locked.current = true;
    const token = ++generation.current;
    setPhase("requesting");
    onBusy(true);
    onStatus("Allow microphone access to record a voice note.");
    let stream: MediaStream | undefined;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (generation.current !== token) { stream.getTracks().forEach(track => track.stop()); return; }
      const type = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"]
        .find(value => MediaRecorder.isTypeSupported(value));
      if (!type) throw new Error("This browser cannot record a supported audio format.");
      const recorder = new MediaRecorder(stream, { mimeType: type });
      const session: Recording = { recorder, stream, canceled: false };
      recording.current = session;
      const chunks: Blob[] = [];
      let bytes = 0;
      recorder.ondataavailable = event => {
        if (session.canceled || !event.data.size) return;
        bytes += event.data.size;
        if (bytes > 10 * 1024 * 1024) {
          cancel();
          onStatus("Recording exceeded 10 MiB. Please record a shorter note.", true);
          return;
        }
        chunks.push(event.data);
      };
      recorder.onerror = () => {
        if (session.canceled) return;
        cancel();
        onStatus("Microphone recording failed. Check your microphone and try again.", true);
      };
      recorder.onstop = () => {
        session.stream.getTracks().forEach(track => track.stop());
        window.clearTimeout(session.timer);
        if (session.canceled || generation.current !== token) return;
        recording.current = null;
        if (!bytes) {
          locked.current = false; setPhase("idle"); onBusy(false);
          onStatus("No audio captured. Record again.", true);
          return;
        }
        const current = { audio: new Blob(chunks, { type: recorder.mimeType }),
          id: crypto.randomUUID(), version };
        clip.current = current;
        void process(current);
      };
      recorder.start(250);
      session.timer = window.setTimeout(() => release(session), 119000);
      setPhase("recording");
      onStatus("Recording… Click Stop when finished. Maximum two minutes.");
    } catch (error) {
      stream?.getTracks().forEach(track => track.stop());
      if (generation.current !== token) return;
      locked.current = false; setPhase("idle"); onBusy(false);
      const name = error instanceof DOMException ? error.name : "";
      onStatus(name === "NotAllowedError" ? "Microphone access denied. Allow it in your browser's site settings and try again."
        : name === "NotFoundError" ? "No microphone found. Connect a microphone and try again."
        : error instanceof Error ? error.message : "Unable to start recording.", true);
    }
  }

  const label = phase === "recording" ? "Stop recording" : phase === "retry" ? "Retry voice note" : "Record voice note";
  return <>
    <button type="button" className={`voice-upload-button ${phase === "recording" ? "is-recording" : ""}`}
      aria-label={label} title={label} aria-pressed={phase === "recording"}
      disabled={phase === "processing" || phase === "requesting" || (disabled && phase !== "recording")}
      onClick={() => {
        if (phase === "recording") release(recording.current);
        else if (phase === "retry" && clip.current && !locked.current) void process(clip.current);
        else void start();
      }}>
      {phase === "processing" || phase === "requesting" ? <LoaderCircle size={20} className="spin" />
        : phase === "recording" ? <Square size={18} fill="currentColor" />
        : phase === "retry" ? <RotateCcw size={20} /> : <Mic size={20} />}
    </button>
    {["recording", "requesting", "retry"].includes(phase) &&
      <button type="button" className="voice-upload-button" aria-label="Discard recording" title="Discard recording" onClick={cancel}><X size={18} /></button>}
  </>;
}
