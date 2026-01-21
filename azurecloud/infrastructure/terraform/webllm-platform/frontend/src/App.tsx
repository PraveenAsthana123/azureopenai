import React, { useState, useCallback } from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import {
  MessageSquare,
  Settings,
  LayoutDashboard,
  HardDrive,
  Menu,
  X,
} from 'lucide-react';
import { ChatInterface } from './components/ChatInterface';
import { ModelManager } from './components/ModelManager';
import { RoutingConfig } from './components/RoutingConfig';
import { UCPDashboard } from './components/UCPDashboard';
import { useWebLLM, ChatMessage, WebLLMConfig } from './hooks/useWebLLM';
import { useHybridRouter } from './hooks/useHybridRouter';

const NavItem: React.FC<{
  to: string;
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
}> = ({ to, icon, label, onClick }) => (
  <NavLink
    to={to}
    onClick={onClick}
    className={({ isActive }) =>
      `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
        isActive
          ? 'bg-blue-600 text-white'
          : 'text-gray-600 hover:bg-gray-100'
      }`
    }
  >
    {icon}
    <span>{label}</span>
  </NavLink>
);

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentResponse, setCurrentResponse] = useState('');
  const [config, setConfig] = useState<WebLLMConfig>({
    enableStreaming: true,
    maxTokens: 2048,
    temperature: 0.7,
    topP: 0.95,
  });

  const {
    models,
    activeModel,
    isGenerating,
    error,
    gpuAvailable,
    loadModel,
    unloadModel,
    generateResponse,
  } = useWebLLM();

  const {
    routingConfig,
    setRoutingConfig,
    state: availability,
    lastDecision,
    checkAvailability,
    generateWithRouting,
  } = useHybridRouter(generateResponse, !!activeModel);

  const handleSendMessage = useCallback(
    async (content: string) => {
      const userMessage: ChatMessage = {
        role: 'user',
        content,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setCurrentResponse('');

      const startTime = Date.now();

      try {
        const allMessages = [...messages, userMessage];

        const { response, decision } = await generateWithRouting(
          allMessages,
          config,
          (chunk) => {
            setCurrentResponse((prev) => prev + chunk);
          }
        );

        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: response,
          timestamp: new Date(),
          model: decision.model,
          tier: decision.tier,
          latency: Date.now() - startTime,
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setCurrentResponse('');
      } catch (err) {
        console.error('Generation failed:', err);
        const errorMessage: ChatMessage = {
          role: 'assistant',
          content: `Error: ${err instanceof Error ? err.message : 'Generation failed'}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
        setCurrentResponse('');
      }
    },
    [messages, config, generateWithRouting]
  );

  return (
    <BrowserRouter>
      <div className="flex h-screen bg-gray-100">
        {/* Sidebar */}
        <aside
          className={`${
            sidebarOpen ? 'w-64' : 'w-0 overflow-hidden'
          } bg-white shadow-lg transition-all duration-300 flex flex-col`}
        >
          <div className="p-4 border-b">
            <h1 className="text-xl font-bold text-gray-800">WebLLM Platform</h1>
            <p className="text-sm text-gray-500">Universal Control Plane</p>
          </div>

          <nav className="flex-1 p-4 space-y-2">
            <NavItem
              to="/"
              icon={<MessageSquare className="w-5 h-5" />}
              label="Chat"
            />
            <NavItem
              to="/models"
              icon={<HardDrive className="w-5 h-5" />}
              label="Models"
            />
            <NavItem
              to="/routing"
              icon={<Settings className="w-5 h-5" />}
              label="Routing"
            />
            <NavItem
              to="/dashboard"
              icon={<LayoutDashboard className="w-5 h-5" />}
              label="Dashboard"
            />
          </nav>

          {/* Status Footer */}
          <div className="p-4 border-t">
            <div className="text-sm space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Browser</span>
                <span
                  className={`w-2 h-2 rounded-full ${
                    activeModel ? 'bg-green-500' : 'bg-gray-300'
                  }`}
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">On-Premise</span>
                <span
                  className={`w-2 h-2 rounded-full ${
                    availability.onPremiseAvailable ? 'bg-green-500' : 'bg-gray-300'
                  }`}
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Cloud</span>
                <span
                  className={`w-2 h-2 rounded-full ${
                    availability.cloudAvailable ? 'bg-green-500' : 'bg-gray-300'
                  }`}
                />
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col">
          {/* Header */}
          <header className="bg-white shadow-sm px-4 py-3 flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              {sidebarOpen ? (
                <X className="w-5 h-5 text-gray-600" />
              ) : (
                <Menu className="w-5 h-5 text-gray-600" />
              )}
            </button>

            {error && (
              <div className="flex-1 px-4 py-2 bg-red-100 text-red-700 rounded-lg text-sm">
                {error}
              </div>
            )}
          </header>

          {/* Content Area */}
          <div className="flex-1 p-6 overflow-auto">
            <Routes>
              <Route
                path="/"
                element={
                  <div className="h-full max-w-4xl mx-auto">
                    <ChatInterface
                      messages={messages}
                      onSendMessage={handleSendMessage}
                      isGenerating={isGenerating}
                      currentResponse={currentResponse}
                      lastDecision={lastDecision}
                      config={config}
                      onConfigChange={setConfig}
                    />
                  </div>
                }
              />
              <Route
                path="/models"
                element={
                  <div className="max-w-2xl mx-auto">
                    <ModelManager
                      models={models}
                      activeModel={activeModel}
                      gpuAvailable={gpuAvailable}
                      onLoadModel={loadModel}
                      onUnloadModel={unloadModel}
                    />
                  </div>
                }
              />
              <Route
                path="/routing"
                element={
                  <div className="max-w-2xl mx-auto">
                    <RoutingConfig
                      config={routingConfig}
                      onChange={setRoutingConfig}
                      onCheckAvailability={checkAvailability}
                      availability={{
                        browserAvailable: !!activeModel,
                        ...availability,
                      }}
                    />
                  </div>
                }
              />
              <Route path="/dashboard" element={<UCPDashboard />} />
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
