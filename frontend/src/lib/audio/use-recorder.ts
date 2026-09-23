"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type RecorderState = "idle" | "requesting" | "recording" | "stopped" | "denied";

const HISTORY = 56;

function pickMime(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"].find((m) =>
    MediaRecorder.isTypeSupported(m),
  );
}

/**
 * Microphone recorder with a live level meter (AnalyserNode RMS).
 * `onChunk` receives timeslice chunks (for WS streaming); `stop()` resolves
 * with the full Blob (for voiceprint upload).
 */
export function useRecorder({ timeslice = 1000, onChunk }: { timeslice?: number; onChunk?: (b: Blob) => void } = {}) {
  const [state, setState] = useState<RecorderState>("idle");
  const [elapsed, setElapsed] = useState(0);
  const [levels, setLevels] = useState<number[]>(() => Array(HISTORY).fill(0));
  const [bytes, setBytes] = useState(0);

  const rec = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const ctx = useRef<AudioContext | null>(null);
  const raf = useRef<number>(0);
  const chunks = useRef<Blob[]>([]);
  const startedAt = useRef(0);
  const onChunkRef = useRef(onChunk);
  onChunkRef.current = onChunk;

  const cleanup = useCallback(() => {
    cancelAnimationFrame(raf.current);
    stream.current?.getTracks().forEach((t) => t.stop());
    ctx.current?.close().catch(() => {});
    stream.current = null;
    ctx.current = null;
  }, []);

  useEffect(() => cleanup, [cleanup]);

  const start = useCallback(async () => {
    setState("requesting");
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
      });
      stream.current = s;
      const ac = new AudioContext();
      ctx.current = ac;
      const analyser = ac.createAnalyser();
      analyser.fftSize = 1024;
      ac.createMediaStreamSource(s).connect(analyser);
      const buf = new Float32Array(analyser.fftSize);
      let last = 0;
      const loop = (ts: number) => {
        raf.current = requestAnimationFrame(loop);
        if (ts - last < 70) return;
        last = ts;
        analyser.getFloatTimeDomainData(buf);
        let sum = 0;
        for (const v of buf) sum += v * v;
        const rms = Math.min(1, Math.sqrt(sum / buf.length) * 4);
        setLevels((prev) => [...prev.slice(1), rms]);
        setElapsed((Date.now() - startedAt.current) / 1000);
      };
      raf.current = requestAnimationFrame(loop);

      const mimeType = pickMime();
      const r = new MediaRecorder(s, mimeType ? { mimeType } : undefined);
      chunks.current = [];
      r.ondataavailable = (e) => {
        if (!e.data.size) return;
        chunks.current.push(e.data);
        setBytes((b) => b + e.data.size);
        onChunkRef.current?.(e.data);
      };
      rec.current = r;
      startedAt.current = Date.now();
      setElapsed(0);
      setBytes(0);
      r.start(timeslice);
      setState("recording");
    } catch {
      cleanup();
      setState("denied");
    }
  }, [cleanup, timeslice]);

  const stop = useCallback(
    () =>
      new Promise<Blob>((resolve) => {
        const r = rec.current;
        if (!r || r.state === "inactive") {
          resolve(new Blob(chunks.current));
          return;
        }
        r.onstop = () => {
          cleanup();
          setState("stopped");
          resolve(new Blob(chunks.current, { type: r.mimeType || "audio/webm" }));
        };
        r.stop();
      }),
    [cleanup],
  );

  const reset = useCallback(() => {
    setState("idle");
    setElapsed(0);
    setBytes(0);
    setLevels(Array(HISTORY).fill(0));
  }, []);

  return { state, elapsed, levels, bytes, start, stop, reset };
}
