import React, { useState, useEffect, useRef } from "react";
import { Header } from "../components/Header";
import { api } from "../services/api";
import { Send, Bot, User, Sparkles, Loader2, Info } from "lucide-react";

export const ChatbotPage: React.FC = () => {
  const [messages, setMessages] = useState<any[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const quickQuestions = [
    "Why is my risk level what it is?",
    "Should I prioritize investing or repaying debt?",
    "How can I improve my financial health score?",
    "What is the best way to structure an emergency fund?"
  ];

  const loadHistory = async () => {
    try {
      const data = await api.getChatHistory();
      setMessages(data || []);
    } catch (err) {
      console.error("Failed to load chat history:", err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSendMessage = async (text: string) => {
    if (!text.trim() || loading) return;
    setLoading(true);

    // Append user message immediately
    const userMsg = { sender: "user", message: text, created_at: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");

    try {
      const response = await api.sendChatMessage({ message: text });
      setMessages((prev) => [...prev, response]);
    } catch (err: any) {
      console.error("Chat error:", err);
      // Append system error response
      setMessages((prev) => [
        ...prev,
        {
          sender: "assistant",
          message: "⚠️ Sorry, I encountered an error communicating with the advisor model. Please check your network connection.",
          created_at: new Date().toISOString()
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative pb-16">
      {/* Background glow */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-emerald-500/5 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] rounded-full bg-emerald-600/5 blur-[120px] pointer-events-none" />

      <Header />

      <main className="max-w-6xl mx-auto w-full px-6 md:px-12 pt-8 flex-1 flex flex-col gap-6 relative z-10">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-emerald-400" />
            <h1 className="text-2xl font-black text-white">AI Financial Coaching Advisor</h1>
          </div>
          <p className="text-xs text-slate-400">
            Ask queries about your budgets, risk assessment metrics, or seek personalized advice. Our AI contextually answers using your ledger records.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1 min-h-[500px]">
          {/* Sidebar suggestion dashboard */}
          <div className="lg:col-span-1 flex flex-col gap-4">
            <div className="glass-panel p-5 rounded-3xl border border-white/5 flex flex-col gap-4">
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs uppercase tracking-wider">
                <Info className="w-4 h-4" /> Suggestion Prompts
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Click any prompt below to automatically ask the advisor about your active profile configuration:
              </p>
              <div className="flex flex-col gap-2.5">
                {quickQuestions.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(q)}
                    disabled={loading || historyLoading}
                    className="text-left text-[11px] p-3 rounded-2xl bg-white/5 border border-white/5 hover:border-emerald-500/30 hover:bg-emerald-500/5 transition-all text-slate-300 font-medium"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Main chat ledger */}
          <div className="lg:col-span-3 glass-panel rounded-3xl border border-white/5 flex flex-col overflow-hidden h-[550px]">
            {/* Header */}
            <div className="px-6 py-4 border-b border-white/5 bg-slate-900/40 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
                  <Bot className="w-4.5 h-4.5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">FinRisk Chatbot</h4>
                  <span className="text-[9px] text-slate-400 font-medium flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block animate-pulse" /> Active
                  </span>
                </div>
              </div>
            </div>

            {/* Bubble logs feed */}
            <div className="flex-1 p-6 overflow-y-auto space-y-4">
              {historyLoading ? (
                <div className="h-full flex items-center justify-center flex-col gap-2">
                  <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
                  <span className="text-xs text-slate-400">Loading conversation ledger...</span>
                </div>
              ) : messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center px-8 gap-3">
                  <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center text-slate-400">
                    <Bot className="w-6 h-6" />
                  </div>
                  <h3 className="text-sm font-bold text-white">No conversation logs yet</h3>
                  <p className="text-xs text-slate-500 max-w-sm">
                    Say hello or pick a quick suggestion on the left to start planning your financial goals with AI!
                  </p>
                </div>
              ) : (
                messages.map((m, idx) => {
                  const isUser = m.sender === "user";
                  return (
                    <div
                      key={idx}
                      className={`flex gap-3 max-w-[85%] ${
                        isUser ? "ml-auto flex-row-reverse" : "mr-auto"
                      }`}
                    >
                      <div
                        className={`w-7.5 h-7.5 rounded-full shrink-0 flex items-center justify-center text-xs ${
                          isUser
                            ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                            : "bg-slate-800 border border-white/5 text-slate-300"
                        }`}
                      >
                        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                      </div>
                      <div className="flex flex-col gap-1">
                        <div
                          className={`p-3.5 rounded-3xl text-xs leading-relaxed ${
                            isUser
                              ? "bg-emerald-500/10 text-emerald-300 rounded-tr-none border border-emerald-500/20"
                              : "bg-slate-900/60 text-slate-300 rounded-tl-none border border-white/5"
                          }`}
                          style={{ whiteSpace: "pre-wrap" }}
                        >
                          {m.message}
                        </div>
                        <span className={`text-[8px] text-slate-500 ${isUser ? "text-right" : "text-left"}`}>
                          {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}

              {loading && (
                <div className="flex gap-3 mr-auto max-w-[85%] animate-pulse">
                  <div className="w-7.5 h-7.5 rounded-full bg-slate-800 border border-white/5 flex items-center justify-center text-slate-300">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="flex flex-col gap-1">
                    <div className="bg-slate-900/60 text-slate-400 p-3.5 rounded-3xl rounded-tl-none border border-white/5 flex items-center gap-2">
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                      <span className="text-xs">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage(inputValue);
              }}
              className="p-4 border-t border-white/5 bg-slate-900/20 flex gap-3"
            >
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Ask the advisor anything about your budget limits or savings goals..."
                disabled={loading || historyLoading}
                className="flex-1 bg-slate-950 border border-white/10 rounded-2xl px-4 py-3 text-xs text-white focus:outline-none focus:border-emerald-500/50 transition-colors"
              />
              <button
                type="submit"
                disabled={loading || historyLoading || !inputValue.trim()}
                className="p-3 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 hover:border-emerald-500/40 text-emerald-400 rounded-2xl transition-all flex items-center justify-center disabled:opacity-50"
              >
                <Send className="w-4.5 h-4.5" />
              </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
};
export default ChatbotPage;
