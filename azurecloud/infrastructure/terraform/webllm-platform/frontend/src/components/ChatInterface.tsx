import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Settings, Cpu, Cloud, Globe } from 'lucide-react';
import { ChatMessage, WebLLMConfig } from '../hooks/useWebLLM';
import { RoutingDecision, InferenceTier } from '../hooks/useHybridRouter';

interface ChatInterfaceProps {
  messages: ChatMessage[];
  onSendMessage: (content: string) => void;
  isGenerating: boolean;
  currentResponse: string;
  lastDecision: RoutingDecision | null;
  config: WebLLMConfig;
  onConfigChange: (config: WebLLMConfig) => void;
}

const TierIcon: React.FC<{ tier: InferenceTier }> = ({ tier }) => {
  switch (tier) {
    case 'browser':
      return <Globe className="w-4 h-4 text-green-500" />;
    case 'on_premise':
      return <Cpu className="w-4 h-4 text-blue-500" />;
    case 'cloud':
      return <Cloud className="w-4 h-4 text-purple-500" />;
    default:
      return null;
  }
};

const TierBadge: React.FC<{ tier: InferenceTier; reason: string }> = ({
  tier,
  reason,
}) => {
  const colors = {
    browser: 'bg-green-100 text-green-800 border-green-200',
    on_premise: 'bg-blue-100 text-blue-800 border-blue-200',
    cloud: 'bg-purple-100 text-purple-800 border-purple-200',
    auto: 'bg-gray-100 text-gray-800 border-gray-200',
  };

  return (
    <div
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs border ${colors[tier]}`}
      title={reason}
    >
      <TierIcon tier={tier} />
      <span className="capitalize">{tier.replace('_', ' ')}</span>
    </div>
  );
};

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  messages,
  onSendMessage,
  isGenerating,
  currentResponse,
  lastDecision,
  config,
  onConfigChange,
}) => {
  const [input, setInput] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentResponse]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isGenerating) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-gray-800">WebLLM Chat</h2>
          {lastDecision && (
            <TierBadge tier={lastDecision.tier} reason={lastDecision.reason} />
          )}
        </div>
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <Settings className="w-5 h-5 text-gray-600" />
        </button>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="px-4 py-3 border-b bg-gray-50">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Temperature
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={config.temperature}
                onChange={(e) =>
                  onConfigChange({ ...config, temperature: parseFloat(e.target.value) })
                }
                className="w-full"
              />
              <span className="text-xs text-gray-500">{config.temperature}</span>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max Tokens
              </label>
              <input
                type="number"
                value={config.maxTokens}
                onChange={(e) =>
                  onConfigChange({ ...config, maxTokens: parseInt(e.target.value) })
                }
                className="w-full px-2 py-1 border rounded text-sm"
                min="1"
                max="4096"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Top P
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={config.topP}
                onChange={(e) =>
                  onConfigChange({ ...config, topP: parseFloat(e.target.value) })
                }
                className="w-full"
              />
              <span className="text-xs text-gray-500">{config.topP}</span>
            </div>
            <div className="flex items-center">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.enableStreaming}
                  onChange={(e) =>
                    onConfigChange({ ...config, enableStreaming: e.target.checked })
                  }
                  className="rounded"
                />
                <span className="text-sm text-gray-700">Enable Streaming</span>
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 py-8">
            <p className="text-lg font-medium">Start a conversation</p>
            <p className="text-sm mt-2">
              Messages are automatically routed to the best inference tier
            </p>
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
              {message.role === 'assistant' && message.tier && (
                <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-200">
                  <TierIcon tier={message.tier} />
                  <span className="text-xs text-gray-500">
                    {message.model} • {message.latency}ms
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}

        {isGenerating && currentResponse && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-lg px-4 py-2 bg-gray-100 text-gray-800">
              <p className="whitespace-pre-wrap">{currentResponse}</p>
              <span className="inline-block w-2 h-4 bg-gray-400 animate-pulse ml-1" />
            </div>
          </div>
        )}

        {isGenerating && !currentResponse && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-100">
              <Loader2 className="w-4 h-4 animate-spin text-gray-600" />
              <span className="text-gray-600">Generating...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="px-4 py-3 border-t">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            rows={1}
            className="flex-1 resize-none px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isGenerating}
          />
          <button
            type="submit"
            disabled={!input.trim() || isGenerating}
            className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {isGenerating ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
