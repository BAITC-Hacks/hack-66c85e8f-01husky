"""Native media regressions: real Chrome, ffmpeg, WebRTC and AudioContext."""

import json
import os
import wave

import pytest
from playwright.sync_api import BrowserType

from bots.base import BotConfig, BotError
from bots.browser import BrowserBot
from bots.media import CAMERA_ASSET, CAMERA_HEIGHT, CAMERA_WIDTH, prepare_media

FIXTURE_URL = "https://meet.google.com/abc-defg-hij"


def test_native_input_files(tmp_path):
    camera, microphone = prepare_media(tmp_path)
    assert camera.read_bytes().startswith(f"YUV4MPEG2 W{CAMERA_WIDTH} H{CAMERA_HEIGHT} ".encode())
    with wave.open(str(microphone), "rb") as audio:
        assert (audio.getframerate(), audio.getsampwidth(), audio.getnchannels()) == (48000, 2, 1)
        assert audio.getnframes() == 48000
        assert audio.readframes(48000) == bytes(96000)
    assert camera.stat().st_mode & 0o777 == 0o600
    assert microphone.stat().st_mode & 0o777 == 0o600


def test_missing_logo_fails_before_starting_browser(tmp_path, monkeypatch):
    monkeypatch.setattr("bots.media.CAMERA_ASSET", tmp_path / "missing.png")
    bot = BrowserBot(BotConfig("meet", FIXTURE_URL, 1, "", ""))
    bot.work_dir = tmp_path
    with pytest.raises(BotError, match="browser was not started"):
        bot.open_browser()
    assert bot.playwright is None
    assert bot.context is None


def test_native_camera_and_audio_over_loopback_webrtc(tmp_path, monkeypatch):
    """Even native enabled setters/clones transmit zeros; received camera is the logo.

    The only launch adjustment is the requested test Chrome channel. Browser creation,
    input file preparation, real capture devices and RTP packets are not mocked.
    """
    channel = os.getenv("KENES_TEST_BROWSER_CHANNEL")
    if channel:
        original_launch = BrowserType.launch_persistent_context

        def launch(self, *args, **kwargs):
            return original_launch(self, *args, **kwargs, channel=channel)

        monkeypatch.setattr(BrowserType, "launch_persistent_context", launch)

    class FixtureBot(BrowserBot):
        def _route(self, route):
            if route.request.url == FIXTURE_URL:
                route.fulfill(
                    content_type="text/html",
                    body="<!doctype html><body>Native media fixture</body>",
                )
            elif route.request.url == "https://meet.google.com/camera.png":
                route.fulfill(content_type="image/png", body=CAMERA_ASSET.read_bytes())
            else:
                route.abort("blockedbyclient")

        @staticmethod
        def _websocket(route):
            route.close()

    bot = FixtureBot(BotConfig("meet", FIXTURE_URL, 1, "", ""))
    bot.work_dir = tmp_path
    try:
        bot.open_browser()
        result = bot.page.evaluate(NATIVE_PROBE, {"width": CAMERA_WIDTH, "height": CAMERA_HEIGHT})
        # Log only synthetic metrics, so failures remain inspectable without credentials.
        print(json.dumps(result, sort_keys=True))
        assert result["nativeAudioEnabled"] is True
        assert result["nativeCloneEnabled"] is True
        assert result["videoEnabled"] is True
        assert result["cloneVideoEnabled"] is True
        assert result["audioPackets"] > 0
        assert result["videoFrames"] > 0
        assert result["captureWidth"] == CAMERA_WIDTH
        assert result["captureHeight"] == CAMERA_HEIGHT
        assert result["cloneWidth"] == CAMERA_WIDTH
        assert result["cloneHeight"] == CAMERA_HEIGHT
        assert result["remoteWidth"] == CAMERA_WIDTH
        assert result["remoteHeight"] == CAMERA_HEIGHT
        assert result["contentHint"] == "detail"
        assert result["cloneContentHint"] == "detail"
        assert result["remoteLogoPixelError"] < result["mirroredRemoteLogoPixelError"]
        assert result["localPeak"] == 0
        assert result["remotePeak"] == 0
        assert result["staticPixelDifference"] == 0
        assert result["logoPixelError"] < 8
        assert result["remoteLogoPixelError"] < 10
        exact = bot.page.evaluate(
            """async ({width, height}) => {
          const stream = await navigator.mediaDevices.getUserMedia({video: {
            width: {exact: width / 2}, height: {exact: height / 2}}});
          const track = stream.getVideoTracks()[0];
          const {width: actualWidth, height: actualHeight} = track.getSettings();
          stream.getTracks().forEach(track => track.stop());
          return {width: actualWidth, height: actualHeight, hint: track.contentHint};
        }""",
            {"width": CAMERA_WIDTH, "height": CAMERA_HEIGHT},
        )
        assert exact == {"width": CAMERA_WIDTH // 2, "height": CAMERA_HEIGHT // 2, "hint": "detail"}
    finally:
        bot.leave()


NATIVE_PROBE = r"""async ({width, height}) => {
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const deadline = async (action, label) => {
    let timer;
    try {
      return await Promise.race([action,
        new Promise((_, reject) => timer = setTimeout(() => reject(new Error(label)), 15000))]);
    } finally { clearTimeout(timer); }
  };
  const stream = await deadline(navigator.mediaDevices.getUserMedia({
    audio: {echoCancellation: false, noiseSuppression: false, autoGainControl: false},
    video: true
  }), 'getUserMedia timeout');
  const audio = stream.getAudioTracks()[0];
  const video = stream.getVideoTracks()[0];
  const audioClone = audio.clone();
  const videoClone = video.clone();
  // Deliberately bypass the JS property guard, proving native source silence itself.
  const enabled = Object.getOwnPropertyDescriptor(MediaStreamTrack.prototype, 'enabled');
  enabled.set.call(audio, true);
  enabled.set.call(audioClone, true);
  const nativeAudioEnabled = enabled.get.call(audio);
  const nativeCloneEnabled = enabled.get.call(audioClone);
  const sendStream = new MediaStream([audioClone, videoClone]);
  const context = new AudioContext({sampleRate: 48000});
  await context.resume();
  const analyse = sourceStream => {
    const source = context.createMediaStreamSource(sourceStream);
    const analyser = context.createAnalyser();
    analyser.fftSize = 2048;
    const silentOutput = context.createGain();
    silentOutput.gain.value = 0;
    source.connect(analyser).connect(silentOutput).connect(context.destination);
    return analyser;
  };
  const localAnalyser = analyse(new MediaStream([audio, audioClone]));
  const a = new RTCPeerConnection({iceServers: []});
  const b = new RTCPeerConnection({iceServers: []});
  const received = new MediaStream();
  b.ontrack = event => received.addTrack(event.track);
  sendStream.getTracks().forEach(track => a.addTrack(track, sendStream));
  const iceComplete = pc => pc.iceGatheringState === 'complete' ? Promise.resolve() :
    new Promise(resolve => pc.addEventListener('icegatheringstatechange', () => {
      if (pc.iceGatheringState === 'complete') resolve();
    }));
  try {
    await a.setLocalDescription(await a.createOffer());
    await deadline(iceComplete(a), 'offer ICE timeout');
    await b.setRemoteDescription(a.localDescription);
    await b.setLocalDescription(await b.createAnswer());
    await deadline(iceComplete(b), 'answer ICE timeout');
    await a.setRemoteDescription(b.localDescription);
    await deadline((async () => {
      while (b.connectionState !== 'connected' || received.getTracks().length !== 2) await sleep(30);
    })(), 'peer connection timeout');
    const remoteAnalyser = analyse(new MediaStream(received.getAudioTracks()));
    let localPeak = 0, remotePeak = 0;
    // Sample beyond the one-second WAV duration to prove Chrome loops silence.
    for (let i = 0; i < 75; i++) {
      const data = new Float32Array(2048);
      localAnalyser.getFloatTimeDomainData(data);
      for (const sample of data) localPeak = Math.max(localPeak, Math.abs(sample));
      remoteAnalyser.getFloatTimeDomainData(data);
      for (const sample of data) remotePeak = Math.max(remotePeak, Math.abs(sample));
      await sleep(40);
    }
    const attachVideo = async source => {
      const el = document.createElement('video');
      el.muted = true; el.autoplay = true; el.srcObject = source;
      document.body.append(el);
      await deadline(el.play(), 'video playback timeout');
      await deadline(new Promise(resolve => el.requestVideoFrameCallback(resolve)), 'video frame timeout');
      return el;
    };
    const localVideo = await attachVideo(new MediaStream([video]));
    const remoteVideo = await attachVideo(received);
    const pixels = source => {
      const canvas = document.createElement('canvas'); canvas.width = width; canvas.height = height;
      const draw = canvas.getContext('2d');
      draw.drawImage(source, 0, 0, width, height);
      return draw.getImageData(0, 0, width, height).data;
    };
    const expectedImage = new Image(); expectedImage.src = '/camera.png';
    await deadline(expectedImage.decode(), 'logo image timeout');
    const reference = pixels(expectedImage);
    const first = pixels(localVideo);
    await sleep(1200);
    const second = pixels(localVideo);
    const remote = pixels(remoteVideo);
    const mirroredRemote = new Uint8ClampedArray(remote.length);
    for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
      for (let c = 0; c < 4; c++)
        mirroredRemote[(y * width + x) * 4 + c] = remote[(y * width + width - x - 1) * 4 + c];
    }
    const error = (left, right) => {
      let sum = 0;
      for (let i = 0; i < left.length; i++) if (i % 4 !== 3) sum += Math.abs(left[i] - right[i]);
      return sum / (width * height * 3);
    };
    let audioPackets = 0, videoFrames = 0;
    for (const stat of (await b.getStats()).values()) {
      if (stat.type === 'inbound-rtp' && stat.kind === 'audio') audioPackets += stat.packetsReceived;
      if (stat.type === 'inbound-rtp' && stat.kind === 'video') videoFrames += stat.framesDecoded;
    }
    return {
      captureWidth: video.getSettings().width, captureHeight: video.getSettings().height,
      cloneWidth: videoClone.getSettings().width, cloneHeight: videoClone.getSettings().height,
      remoteWidth: remoteVideo.videoWidth, remoteHeight: remoteVideo.videoHeight,
      contentHint: video.contentHint, cloneContentHint: videoClone.contentHint,
      mirroredRemoteLogoPixelError: error(reference, mirroredRemote),
      nativeAudioEnabled, nativeCloneEnabled, videoEnabled: video.enabled,
      cloneVideoEnabled: videoClone.enabled, localPeak, remotePeak, audioPackets, videoFrames,
      staticPixelDifference: error(first, second), logoPixelError: error(reference, second),
      remoteLogoPixelError: error(reference, remote)
    };
  } finally {
    a.close(); b.close();
    [...stream.getTracks(), ...sendStream.getTracks(), ...received.getTracks()].forEach(track => track.stop());
    await context.close();
  }
}"""
