export interface ServerMessage {
  type?: string;
  turn_id?: string;
  state?: string;
  transcription?: string;
  text?: string;
  assistant_chunk?: string;
  image?: any;
  is_voice?: boolean;
}

export class AudioStreamer {
  private audioContext: AudioContext | null = null;
  private ws: WebSocket | null = null;
  private stream: MediaStream | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private processor: AudioWorkletNode | null = null;
  private analyser: AnalyserNode | null = null;
  private timeDomainBuffer: Uint8Array | null = null;
  
  private nextStartTime: number = 0;
  private scheduledNodes: AudioBufferSourceNode[] = [];
  
  private url: string;
  private onMessageCallback: (msg: ServerMessage) => void;

  constructor(
    url: string, 
    onMessageCallback: (msg: ServerMessage) => void
  ) {
    this.url = url;
    this.onMessageCallback = onMessageCallback;
  }

  async start() {
    this.ws = new WebSocket(this.url);
    this.ws.binaryType = 'arraybuffer';
    
    this.ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        try {
          const msg: ServerMessage = JSON.parse(event.data);
          if (msg.state === 'Interrupted') {
            this.flushAudio();
          }
          this.onMessageCallback(msg);
        } catch (e) {
          console.error("Failed to parse websocket message", e);
        }
      } else {
        // Binary audio chunk (24kHz PCM from Kokoro)
        this.playAudioChunk(event.data);
      }
    };

    await new Promise((resolve, reject) => {
      if (this.ws) {
        this.ws.onopen = resolve;
        this.ws.onerror = reject;
      }
    });

    // Native natural silence threshold: ~1.5s pause tolerance
    this.sendConfig({
      silence_threshold: 12
    });

    // Microphone capture: disable aggressive browser noise suppression to prevent swallowing soft syllables
    this.stream = await navigator.mediaDevices.getUserMedia({ 
      audio: {
        echoCancellation: true,
        noiseSuppression: false,
        autoGainControl: true,
      } 
    });
    
    // Force 16kHz sample rate for backend VAD and ASR
    this.audioContext = new AudioContext({ sampleRate: 16000 });
    this.nextStartTime = this.audioContext.currentTime;

    await this.audioContext.audioWorklet.addModule('/audio-processor.js');

    this.source = this.audioContext.createMediaStreamSource(this.stream);
    this.processor = new AudioWorkletNode(this.audioContext, 'audio-processor');

    // Setup AnalyserNode for live visualizer
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 64;
    this.analyser.smoothingTimeConstant = 0.5;
    this.timeDomainBuffer = new Uint8Array(this.analyser.fftSize);
    this.source.connect(this.analyser);

    this.processor.port.onmessage = (event) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(event.data);
      }
    };

    this.source.connect(this.processor);
    
    const dummyGain = this.audioContext.createGain();
    dummyGain.gain.value = 0;
    this.processor.connect(dummyGain);
    dummyGain.connect(this.audioContext.destination);
  }

  getAudioLevel(): number {
    if (!this.analyser || !this.timeDomainBuffer) return 0;
    this.analyser.getByteTimeDomainData(this.timeDomainBuffer as any);
    
    let sum = 0;
    for (let i = 0; i < this.timeDomainBuffer.length; i++) {
      const normalized = (this.timeDomainBuffer[i] - 128) / 128;
      sum += normalized * normalized;
    }
    const rms = Math.sqrt(sum / this.timeDomainBuffer.length);
    return Math.min(1.0, rms * 4.5); // scale to useful 0-1 visual range
  }

  sendMessage(text: string, id?: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "CHAT_MESSAGE", text, id }));
    }
  }

  sendConfig(config: Record<string, any>) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "CONFIG", ...config }));
    }
  }

  private playAudioChunk(arrayBuffer: ArrayBuffer) {
    if (!this.audioContext) return;

    // Backend (Kokoro) sends 24kHz Int16 PCM
    const int16Data = new Int16Array(arrayBuffer);
    const float32Data = new Float32Array(int16Data.length);
    for (let i = 0; i < int16Data.length; i++) {
      float32Data[i] = int16Data[i] / 32768.0;
    }

    const audioBuffer = this.audioContext.createBuffer(1, float32Data.length, 24000);
    audioBuffer.getChannelData(0).set(float32Data);

    const source = this.audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.audioContext.destination);

    const currentTime = this.audioContext.currentTime;
    if (this.nextStartTime < currentTime) {
      this.nextStartTime = currentTime + 0.08;
    }
    source.start(this.nextStartTime);
    this.scheduledNodes.push(source);
    
    source.onended = () => {
      this.scheduledNodes = this.scheduledNodes.filter(n => n !== source);
    };
    
    this.nextStartTime += audioBuffer.duration;
  }

  public flushAudio() {
    this.scheduledNodes.forEach(node => {
      try {
        node.onended = null;
        node.stop();
        node.disconnect();
      } catch (e) {}
    });
    this.scheduledNodes = [];
    if (this.audioContext) {
      this.nextStartTime = this.audioContext.currentTime;
    }
  }

  interrupt() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "INTERRUPT" }));
    }
    this.flushAudio();
  }

  stop() {
    if (this.processor) {
      this.processor.disconnect();
    }
    if (this.source) {
      this.source.disconnect();
    }
    if (this.analyser) {
      this.analyser.disconnect();
    }
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
    }
    if (this.audioContext) {
      this.audioContext.close();
    }
    if (this.ws) {
      this.ws.close();
    }
  }
}
