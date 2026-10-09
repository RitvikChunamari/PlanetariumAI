import React, { useState, useRef, useEffect, useCallback } from 'react';
import { AudioStreamer, type ServerMessage } from './audio/AudioStreamer';
import { AstroMediaViewer, type ImageData } from './components/AstroMediaViewer';
import { CosmicBackground } from './components/CosmicBackground';
import { CelestialCore } from './components/CelestialCore';
import './index.css';

interface Message {
  id: string;
  turnId?: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  image?: ImageData;
  isStreaming?: boolean;
}

export default function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [pipelineState, setPipelineState] = useState<string>("Ready");
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init-welcome',
      turnId: 'welcome',
      sender: 'assistant',
      text: "Palomar Deep Sky Intelligence initialized. Connected to local GPU/CPU vector core and 100,000-entry cosmology repository. Tap the Celestial Core or use your microphone to explore the cosmos.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      isStreaming: false
    }
  ]);
  const [inputText, setInputText] = useState("");
  const [audioLevel, setAudioLevel] = useState(0);
  const [selectedImage, setSelectedImage] = useState<ImageData | null>(null);
  const [utcTime, setUtcTime] = useState("");

  const streamerRef = useRef<AudioStreamer | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const animFrameRef = useRef<number | null>(null);

  // Live UTC Observatory Clock
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().slice(17, 25) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Smooth Chat Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, pipelineState]);

  // Real-time Audio Level Monitor Loop
  useEffect(() => {
    if (isRecording) {
      const updateLevel = () => {
        if (streamerRef.current) {
          const lvl = streamerRef.current.getAudioLevel();
          setAudioLevel(lvl);
        }
        animFrameRef.current = requestAnimationFrame(updateLevel);
      };
      animFrameRef.current = requestAnimationFrame(updateLevel);
    } else {
      setAudioLevel(0);
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    }
    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [isRecording]);

  const handleServerMessage = useCallback((msg: ServerMessage) => {
    if (msg.state) {
      setPipelineState(msg.state);
    }

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    // 1. Authoritative User Query (Speech transcription or text input)
    if (msg.type === 'user_message') {
      const userText = (msg.text || msg.transcription || "").trim();
      const turnId = msg.turn_id || `turn-${Date.now()}`;
      if (!userText) return;

      setMessages(prev => {
        // Strict deduplication: ensure single instance per unique turn or utterance
        const exists = prev.some(m => m.turnId === turnId || (m.sender === 'user' && m.text.trim() === userText));
        if (exists) return prev;

        return [
          ...prev,
          {
            id: `usr-${turnId}`,
            turnId: turnId,
            sender: 'user',
            text: userText,
            timestamp: timeStr
          },
          {
            id: `ast-${turnId}`,
            turnId: turnId,
            sender: 'assistant',
            text: '',
            timestamp: timeStr,
            isStreaming: true
          }
        ];
      });
      return;
    }

    // 2. Stream assistant speech chunk
    if (msg.type === 'assistant_chunk' || msg.assistant_chunk) {
      const chunkText = msg.text || msg.assistant_chunk || "";
      const turnId = msg.turn_id;

      setMessages(prev => {
        if (prev.length === 0) return prev;

        let targetIdx = -1;
        if (turnId) {
          targetIdx = prev.findIndex(m => m.turnId === turnId && m.sender === 'assistant');
        }
        if (targetIdx === -1) {
          targetIdx = prev.length - 1;
        }

        const target = prev[targetIdx];
        if (target && target.sender === 'assistant') {
          const updated = {
            ...target,
            text: target.text ? `${target.text} ${chunkText}` : chunkText,
            isStreaming: true
          };
          return [...prev.slice(0, targetIdx), updated, ...prev.slice(targetIdx + 1)];
        }
        return prev;
      });
      return;
    }

    // 3. Turn complete
    if (msg.type === 'turn_complete' || msg.state === 'Listening...' || msg.state === 'Interrupted') {
      setMessages(prev =>
        prev.map(m => m.isStreaming ? { ...m, isStreaming: false } : m)
      );
    }

    // 4. Inline NASA Photographic Specimen
    if (msg.type === 'image' || msg.image) {
      const imgData: ImageData = msg.image;
      setMessages(prev => {
        if (prev.length === 0) return prev;
        const lastIdx = prev.length - 1;
        const lastMsg = prev[lastIdx];
        if (lastMsg.sender === 'assistant') {
          return [...prev.slice(0, lastIdx), { ...lastMsg, image: imgData }];
        }
        return prev;
      });
    }
  }, []);

  const getWebSocketUrl = async (): Promise<string> => {
    // Check for native Tauri desktop environment
    if (typeof window !== 'undefined' && ('__TAURI_INTERNALS__' in window || '__TAURI__' in window)) {
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        const port = await invoke<number>('get_backend_port');
        return `ws://127.0.0.1:${port}/ws/audio`;
      } catch {
        return `ws://127.0.0.1:8000/ws/audio`;
      }
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8000';
    return `${protocol}//${host}/ws/audio`;
  };

  const toggleRecording = async () => {
    if (isRecording) {
      streamerRef.current?.stop();
      setIsRecording(false);
      setPipelineState("Ready");
    } else {
      const url = await getWebSocketUrl();
      const streamer = new AudioStreamer(url, handleServerMessage);
      try {
        await streamer.start();
        streamerRef.current = streamer;
        setIsRecording(true);
        setPipelineState("Listening...");
      } catch (err) {
        console.error("Microphone initialization error:", err);
        setPipelineState("Microphone Error");
      }
    }
  };

  const handleInterrupt = () => {
    streamerRef.current?.interrupt();
    setPipelineState("Interrupted");
    setMessages(prev =>
      prev.map(m => m.isStreaming ? { ...m, isStreaming: false } : m)
    );
  };

  const handleSendText = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = inputText.trim();
    if (!query) return;

    const turnId = `client-${Date.now()}`;
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    setMessages(prev => [
      ...prev,
      {
        id: `usr-${turnId}`,
        turnId: turnId,
        sender: 'user',
        text: query,
        timestamp: timeStr
      },
      {
        id: `ast-${turnId}`,
        turnId: turnId,
        sender: 'assistant',
        text: '',
        timestamp: timeStr,
        isStreaming: true
      }
    ]);

    setInputText("");

    if (streamerRef.current && isRecording) {
      streamerRef.current.sendMessage(query, turnId);
    } else {
      getWebSocketUrl().then(url => {
        const streamer = new AudioStreamer(url, handleServerMessage);
        return streamer.start().then(() => {
          streamerRef.current = streamer;
          setIsRecording(true);
          streamer.sendMessage(query, turnId);
        });
      }).catch(err => {
        console.error("Failed to connect WebSocket for text query:", err);
      });
    }
  };

  const clearSession = () => {
    setMessages([
      {
        id: `welcome-${Date.now()}`,
        turnId: 'welcome',
        sender: 'assistant',
        text: "New observation turn cleared. Ask any question about cosmology, planets, or request NASA telescope records.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        isStreaming: false
      }
    ]);
  };

  return (
    <div className="relative min-h-screen w-full bg-[#030408] text-[#f1f3f9] flex flex-col font-sans select-text overflow-hidden">
      {/* 1. Deep Space Atmospheric Cosmic Starfield */}
      <CosmicBackground />

      {/* 2. Observatory Precision Header (Swiss International Typographic Style) */}
      <header className="relative z-20 w-full px-5 sm:px-10 py-3.5 border-b border-white/[0.06] bg-[#05070f]/80 backdrop-blur-2xl flex items-center justify-between">
        {/* Left: Observatory Node Branding */}
        <div className="flex items-center space-x-4">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500/10 to-indigo-500/20 border border-white/10 flex items-center justify-center text-cyan-300 shadow-[0_0_15px_rgba(59,130,246,0.2)]">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="9" strokeWidth="1.5" />
              <path strokeLinecap="round" strokeWidth="1.5" d="M12 3v3m0 12v3M3 12h3m12 0h3" />
              <circle cx="12" cy="12" r="3" strokeWidth="1.5" />
            </svg>
          </div>

          <div>
            <div className="flex items-center space-x-2.5">
              <h1 className="text-sm font-semibold tracking-tight text-white uppercase">
                Palomar Observatory
              </h1>
              <span className="text-[10px] font-mono tracking-widest text-cyan-400 uppercase bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-800/40">
                AI Celestial Core
              </span>
            </div>
            <p className="text-[11px] text-zinc-400 font-mono tracking-wide">
              RA 18h 36m • DEC +38° 47′ • 100K Vector Core • Local 0-Cloud Inference
            </p>
          </div>
        </div>

        {/* Right: Telemetry & Actions */}
        <div className="flex items-center space-x-3.5">
          {/* Live UTC Telemetry */}
          <div className="hidden md:flex items-center space-x-2 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.06] text-xs font-mono text-zinc-400">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span>{utcTime}</span>
          </div>

          {/* System Hardware Status */}
          <div className="flex items-center space-x-2 px-3.5 py-1 rounded-full bg-white/[0.03] border border-white/[0.08] text-xs font-mono">
            <span className={`w-2 h-2 rounded-full ${
              pipelineState === 'Speaking...' ? 'bg-sky-400 animate-ping' :
              pipelineState === 'Listening...' ? 'bg-emerald-400 animate-pulse' :
              pipelineState === 'Thinking...' ? 'bg-pink-400' :
              'bg-zinc-500'
            }`} />
            <span className="text-zinc-200">
              {pipelineState === 'Speaking...' ? 'Synthesizing' :
               pipelineState === 'Listening...' ? 'Acoustic Intercom' :
               pipelineState === 'Thinking...' ? 'Computing' :
               'Online'}
            </span>
          </div>

          {/* Reset Conversation */}
          <button
            onClick={clearSession}
            title="Clear Observation Log"
            className="p-1.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.08] text-zinc-400 hover:text-zinc-100 transition-colors"
            aria-label="Reset Conversation"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </header>

      {/* 3. Central Interactive Celestial Acoustic Core (Awwwards Centerpiece) */}
      <section className="relative z-10 shrink-0 pt-2 pb-1 flex flex-col items-center justify-center">
        <CelestialCore
          pipelineState={pipelineState}
          isRecording={isRecording}
          audioLevel={audioLevel}
          onToggleRecording={toggleRecording}
        />
      </section>

      {/* 4. Observatory Transmission Feed */}
      <main className="relative z-10 flex-1 overflow-y-auto px-4 sm:px-8 py-4 max-w-4xl w-full mx-auto space-y-5">
        {messages.map((msg) => {
          const isUser = msg.sender === 'user';
          return (
            <div
              key={msg.id}
              className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} transition-opacity duration-200`}
            >
              {/* Transmission Metadata Tag */}
              <div className="flex items-center space-x-2 mb-1 px-1 text-[11px] font-mono text-zinc-400 tracking-wider">
                <span className="uppercase text-zinc-400">
                  {isUser ? '// VISITOR TRANSMISSION' : '// OBSERVATORY SYNTHESIS'}
                </span>
                <span>•</span>
                <span>{msg.timestamp}</span>
              </div>

              {/* Transmission Body Card */}
              <div
                className={`max-w-[90%] sm:max-w-[82%] px-5 py-4 rounded-2xl text-[15px] leading-relaxed transition-all shadow-xl ${
                  isUser
                    ? 'bg-gradient-to-br from-blue-950/40 to-slate-900/60 text-white border border-blue-500/20 backdrop-blur-xl rounded-tr-xs'
                    : 'bg-[#090c16]/80 text-zinc-200 border border-white/[0.08] backdrop-blur-2xl rounded-tl-xs'
                }`}
              >
                <p className="whitespace-pre-wrap font-normal">
                  {msg.text || (msg.isStreaming ? (
                    <span className="inline-flex items-center space-x-2 text-cyan-400 text-xs font-mono py-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
                      <span>Transmitting synthesized astrophysics...</span>
                    </span>
                  ) : '')}
                </p>

                {/* Inline Museum Specimen Card */}
                {msg.image && (
                  <div className="mt-4 pt-3 border-t border-white/[0.08]">
                    <div
                      onClick={() => setSelectedImage(msg.image!)}
                      className="cursor-pointer group relative rounded-xl overflow-hidden border border-white/10 bg-black/60 hover:border-cyan-400/50 transition-all duration-300"
                    >
                      <img
                        src={msg.image.local_path}
                        alt={msg.image.title}
                        className="w-full max-h-64 object-cover group-hover:scale-[1.02] transition-transform duration-500"
                      />
                      <div className="p-3.5 bg-[#070912]/95 backdrop-blur-md">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-mono uppercase tracking-widest text-cyan-400">
                            NASA Telescopic Archive
                          </span>
                          <span className="text-[10px] font-mono text-zinc-400">
                            Inspect ↗
                          </span>
                        </div>
                        <h4 className="text-sm font-medium text-white truncate mt-1">
                          {msg.image.title}
                        </h4>
                        <p className="text-xs text-zinc-400 line-clamp-2 mt-1 leading-normal">
                          {msg.image.description}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} className="h-24" />
      </main>

      {/* 5. Curated Celestial Inquiries (Discovery Strip) */}
      <div className="relative z-10 max-w-4xl w-full mx-auto px-4 pb-2">
        <div className="flex items-center space-x-2 overflow-x-auto no-scrollbar py-1">
          <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-widest shrink-0">
            Celestial Inquiries:
          </span>
          {[
            "Show me Jupiter",
            "What is Sagittarius A*?",
            "Explain the Big Bang",
            "How do black holes form?",
            "Pillars of Creation",
            "James Webb Telescope discoveries"
          ].map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => setInputText(prompt)}
              className="shrink-0 px-3 py-1 rounded-lg bg-white/[0.03] hover:bg-cyan-500/10 border border-white/[0.08] hover:border-cyan-500/30 text-xs text-zinc-300 hover:text-cyan-200 transition-all font-mono tracking-wide"
            >
              ✦ {prompt}
            </button>
          ))}
        </div>
      </div>

      {/* 6. Hardware-Grade Voice & Command Console (Apple Vision / Minimalist Dock) */}
      <footer className="relative z-20 w-full max-w-4xl mx-auto px-4 pb-5">
        <div className="rounded-2xl p-3 sm:p-3.5 bg-[#070a14]/90 backdrop-blur-2xl border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.8)] flex flex-col space-y-3">
          {/* Controls Ribbon */}
          <div className="flex items-center justify-between gap-3 px-1">
            <div className="flex items-center space-x-3">
              {/* Primary Voice Intercom Trigger */}
              <button
                onClick={toggleRecording}
                className={`px-4 py-2 rounded-xl text-xs font-mono font-medium tracking-wider flex items-center space-x-2.5 transition-all duration-200 shadow-md ${
                  isRecording
                    ? 'bg-emerald-400 text-black hover:bg-emerald-300 shadow-[0_0_18px_rgba(52,211,153,0.4)]'
                    : 'bg-white/10 hover:bg-white/15 text-white border border-white/10'
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${isRecording ? 'bg-black animate-ping' : 'bg-cyan-400'}`} />
                <span>{isRecording ? "Live Intercom Active" : "Start Voice Intercom"}</span>
              </button>

              {/* Stereo Frequency Waveform Monitor */}
              <div className="flex items-center space-x-1 h-6 px-3 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                {[0.35, 0.7, 1.0, 0.85, 1.1, 0.65, 0.4].map((factor, i) => {
                  const isAi = pipelineState === "Speaking...";
                  const height = isRecording
                    ? isAi
                      ? Math.min(18, Math.max(3, Math.sin(Date.now() / 160 + i) * 6 + 9))
                      : Math.min(20, Math.max(3, audioLevel * 22 * factor + 3))
                    : 3;

                  return (
                    <div
                      key={i}
                      className={`w-1 rounded-full transition-all duration-75 ${
                        isAi
                          ? 'bg-sky-400'
                          : isRecording
                          ? 'bg-emerald-400'
                          : 'bg-zinc-700'
                      }`}
                      style={{ height: `${height}px` }}
                    />
                  );
                })}
              </div>

              {/* Barge-in Stop Control */}
              {pipelineState === "Speaking..." && (
                <button
                  onClick={handleInterrupt}
                  className="px-3 py-1.5 rounded-xl bg-red-500/15 hover:bg-red-500/25 border border-red-500/30 text-red-300 text-xs font-mono transition-colors flex items-center space-x-1.5"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                  <span>Interrupt</span>
                </button>
              )}
            </div>

            {/* Zero-Cloud Pipeline Badge */}
            <div className="hidden sm:flex items-center space-x-1.5 text-[11px] font-mono text-zinc-400">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              <span>100% Offline Core</span>
            </div>
          </div>

          {/* Text Input Row */}
          <form onSubmit={handleSendText} className="relative flex items-center">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask an astronomical question or type 'Show me...' for NASA imagery"
              className="w-full pl-4 pr-12 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-white placeholder-zinc-500 text-sm focus:outline-none focus:border-cyan-400/40 focus:ring-1 focus:ring-cyan-400/30 transition-all font-sans"
            />
            <button
              type="submit"
              disabled={!inputText.trim()}
              className="absolute right-2 p-1.5 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/30 disabled:opacity-20 text-cyan-200 transition-all"
              aria-label="Send inquiry"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </form>
        </div>
      </footer>

      {/* 7. Museum Specimen Deep Zoom Modal */}
      {selectedImage && (
        <AstroMediaViewer
          image={selectedImage}
          onClose={() => setSelectedImage(null)}
        />
      )}
    </div>
  );
}
