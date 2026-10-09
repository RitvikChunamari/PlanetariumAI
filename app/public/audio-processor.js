class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bufferSize = 2048; // About 128ms at 16kHz
    this.buffer = new Int16Array(this.bufferSize);
    this.bytesWritten = 0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (input.length > 0) {
      const channel = input[0];
      for (let i = 0; i < channel.length; i++) {
        // Convert Float32 [-1.0, 1.0] to Int16 [-32768, 32767]
        let s = Math.max(-1, Math.min(1, channel[i]));
        this.buffer[this.bytesWritten++] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        
        if (this.bytesWritten >= this.bufferSize) {
          this.port.postMessage(this.buffer.buffer, [this.buffer.buffer]);
          this.buffer = new Int16Array(this.bufferSize);
          this.bytesWritten = 0;
        }
      }
    }
    return true;
  }
}

registerProcessor('audio-processor', AudioProcessor);
