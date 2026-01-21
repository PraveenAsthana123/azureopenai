import { useState, useCallback } from 'react';
import axios from 'axios';
import { ChatMessage, WebLLMConfig } from './useWebLLM';

export type InferenceTier = 'browser' | 'on_premise' | 'cloud' | 'auto';

export interface RoutingConfig {
  preferredTier: InferenceTier;
  privacyLevel: 'low' | 'medium' | 'high';
  latencyRequirement: 'low' | 'medium' | 'high';
  costOptimization: boolean;
  fallbackEnabled: boolean;
}

export interface RoutingDecision {
  tier: InferenceTier;
  model: string;
  reason: string;
  estimatedLatency: number;
  estimatedCost: number;
}

interface HybridRouterState {
  isConnected: boolean;
  onPremiseAvailable: boolean;
  cloudAvailable: boolean;
  browserAvailable: boolean;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export function useHybridRouter(
  browserGenerate: (
    messages: ChatMessage[],
    config: WebLLMConfig,
    onStream?: (chunk: string) => void
  ) => Promise<string>,
  browserModelReady: boolean
) {
  const [routingConfig, setRoutingConfig] = useState<RoutingConfig>({
    preferredTier: 'auto',
    privacyLevel: 'medium',
    latencyRequirement: 'medium',
    costOptimization: true,
    fallbackEnabled: true,
  });

  const [state, setState] = useState<HybridRouterState>({
    isConnected: false,
    onPremiseAvailable: false,
    cloudAvailable: false,
    browserAvailable: false,
  });

  const [lastDecision, setLastDecision] = useState<RoutingDecision | null>(null);

  const checkAvailability = useCallback(async () => {
    const newState: HybridRouterState = {
      isConnected: true,
      onPremiseAvailable: false,
      cloudAvailable: false,
      browserAvailable: browserModelReady,
    };

    try {
      const response = await axios.get(`${API_BASE_URL}/v1/health`, {
        timeout: 5000,
      });
      newState.onPremiseAvailable = response.data?.on_premise?.healthy || false;
      newState.cloudAvailable = response.data?.cloud?.healthy || false;
    } catch {
      newState.isConnected = false;
    }

    setState(newState);
    return newState;
  }, [browserModelReady]);

  const determineRoute = useCallback(
    (messages: ChatMessage[]): RoutingDecision => {
      const lastMessage = messages[messages.length - 1]?.content || '';
      const messageLength = lastMessage.length;
      const containsSensitiveData =
        /\b(password|ssn|credit card|secret|private|confidential)\b/i.test(
          lastMessage
        );

      if (routingConfig.preferredTier !== 'auto') {
        return {
          tier: routingConfig.preferredTier,
          model: getModelForTier(routingConfig.preferredTier),
          reason: 'User preference',
          estimatedLatency: getEstimatedLatency(routingConfig.preferredTier),
          estimatedCost: getEstimatedCost(routingConfig.preferredTier, messageLength),
        };
      }

      if (routingConfig.privacyLevel === 'high' || containsSensitiveData) {
        if (browserModelReady) {
          return {
            tier: 'browser',
            model: 'Llama-3.1-8B-Instruct-q4f16_1-MLC',
            reason: 'Privacy-sensitive content - processing locally',
            estimatedLatency: 2000,
            estimatedCost: 0,
          };
        }
        if (state.onPremiseAvailable) {
          return {
            tier: 'on_premise',
            model: 'llama-3-1-70b',
            reason: 'Privacy-sensitive content - using on-premise',
            estimatedLatency: 500,
            estimatedCost: 0,
          };
        }
      }

      if (routingConfig.latencyRequirement === 'low') {
        if (browserModelReady && messageLength < 500) {
          return {
            tier: 'browser',
            model: 'Phi-3-mini-4k-instruct-q4f16_1-MLC',
            reason: 'Low latency requirement - browser inference',
            estimatedLatency: 100,
            estimatedCost: 0,
          };
        }
      }

      if (routingConfig.costOptimization) {
        if (browserModelReady) {
          return {
            tier: 'browser',
            model: 'Llama-3.1-8B-Instruct-q4f16_1-MLC',
            reason: 'Cost optimization - free browser inference',
            estimatedLatency: 1500,
            estimatedCost: 0,
          };
        }
        if (state.onPremiseAvailable) {
          return {
            tier: 'on_premise',
            model: 'llama-3-1-8b',
            reason: 'Cost optimization - on-premise inference',
            estimatedLatency: 300,
            estimatedCost: 0,
          };
        }
      }

      if (messageLength > 2000 || messages.length > 10) {
        if (state.cloudAvailable) {
          return {
            tier: 'cloud',
            model: 'gpt-4o',
            reason: 'Complex/long context - using cloud',
            estimatedLatency: 1000,
            estimatedCost: calculateCloudCost(messageLength),
          };
        }
        if (state.onPremiseAvailable) {
          return {
            tier: 'on_premise',
            model: 'llama-3-1-70b',
            reason: 'Complex task - using on-premise large model',
            estimatedLatency: 800,
            estimatedCost: 0,
          };
        }
      }

      if (state.onPremiseAvailable) {
        return {
          tier: 'on_premise',
          model: 'llama-3-1-8b',
          reason: 'Default routing - on-premise',
          estimatedLatency: 300,
          estimatedCost: 0,
        };
      }

      if (browserModelReady) {
        return {
          tier: 'browser',
          model: 'Llama-3.1-8B-Instruct-q4f16_1-MLC',
          reason: 'Fallback - browser inference',
          estimatedLatency: 1500,
          estimatedCost: 0,
        };
      }

      return {
        tier: 'cloud',
        model: 'gpt-4o',
        reason: 'Fallback - cloud inference',
        estimatedLatency: 1000,
        estimatedCost: calculateCloudCost(messageLength),
      };
    },
    [routingConfig, state, browserModelReady]
  );

  const generateWithRouting = useCallback(
    async (
      messages: ChatMessage[],
      config: WebLLMConfig,
      onStream?: (chunk: string) => void
    ): Promise<{ response: string; decision: RoutingDecision }> => {
      const decision = determineRoute(messages);
      setLastDecision(decision);

      const startTime = Date.now();

      try {
        let response: string;

        switch (decision.tier) {
          case 'browser':
            response = await browserGenerate(messages, config, onStream);
            break;

          case 'on_premise':
            response = await generateOnPremise(messages, config, onStream);
            break;

          case 'cloud':
            response = await generateCloud(messages, config, onStream);
            break;

          default:
            throw new Error('Invalid tier');
        }

        const actualLatency = Date.now() - startTime;
        setLastDecision({ ...decision, estimatedLatency: actualLatency });

        return { response, decision };
      } catch (error) {
        if (routingConfig.fallbackEnabled) {
          return await handleFallback(messages, config, decision, onStream);
        }
        throw error;
      }
    },
    [determineRoute, browserGenerate, routingConfig.fallbackEnabled]
  );

  const generateOnPremise = async (
    messages: ChatMessage[],
    config: WebLLMConfig,
    onStream?: (chunk: string) => void
  ): Promise<string> => {
    const formattedMessages = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    if (config.enableStreaming && onStream) {
      const response = await fetch(`${API_BASE_URL}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: formattedMessages,
          max_tokens: config.maxTokens,
          temperature: config.temperature,
          top_p: config.topP,
          stream: true,
          tier: 'on_premise',
        }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter((line) => line.startsWith('data:'));

        for (const line of lines) {
          const data = line.replace('data: ', '');
          if (data === '[DONE]') continue;

          try {
            const parsed = JSON.parse(data);
            const content = parsed.choices?.[0]?.delta?.content || '';
            fullResponse += content;
            onStream(content);
          } catch {
            // Skip invalid JSON
          }
        }
      }

      return fullResponse;
    }

    const response = await axios.post(`${API_BASE_URL}/v1/chat/completions`, {
      messages: formattedMessages,
      max_tokens: config.maxTokens,
      temperature: config.temperature,
      top_p: config.topP,
      tier: 'on_premise',
    });

    return response.data.choices[0]?.message?.content || '';
  };

  const generateCloud = async (
    messages: ChatMessage[],
    config: WebLLMConfig,
    onStream?: (chunk: string) => void
  ): Promise<string> => {
    const formattedMessages = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    if (config.enableStreaming && onStream) {
      const response = await fetch(`${API_BASE_URL}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: formattedMessages,
          max_tokens: config.maxTokens,
          temperature: config.temperature,
          top_p: config.topP,
          stream: true,
          tier: 'cloud',
        }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter((line) => line.startsWith('data:'));

        for (const line of lines) {
          const data = line.replace('data: ', '');
          if (data === '[DONE]') continue;

          try {
            const parsed = JSON.parse(data);
            const content = parsed.choices?.[0]?.delta?.content || '';
            fullResponse += content;
            onStream(content);
          } catch {
            // Skip invalid JSON
          }
        }
      }

      return fullResponse;
    }

    const response = await axios.post(`${API_BASE_URL}/v1/chat/completions`, {
      messages: formattedMessages,
      max_tokens: config.maxTokens,
      temperature: config.temperature,
      top_p: config.topP,
      tier: 'cloud',
    });

    return response.data.choices[0]?.message?.content || '';
  };

  const handleFallback = async (
    messages: ChatMessage[],
    config: WebLLMConfig,
    originalDecision: RoutingDecision,
    onStream?: (chunk: string) => void
  ): Promise<{ response: string; decision: RoutingDecision }> => {
    const fallbackOrder: InferenceTier[] = ['on_premise', 'cloud', 'browser'];
    const remainingTiers = fallbackOrder.filter((t) => t !== originalDecision.tier);

    for (const tier of remainingTiers) {
      try {
        const decision: RoutingDecision = {
          tier,
          model: getModelForTier(tier),
          reason: `Fallback from ${originalDecision.tier}`,
          estimatedLatency: getEstimatedLatency(tier),
          estimatedCost: getEstimatedCost(tier, messages[messages.length - 1]?.content.length || 0),
        };

        let response: string;
        switch (tier) {
          case 'browser':
            if (!browserModelReady) continue;
            response = await browserGenerate(messages, config, onStream);
            break;
          case 'on_premise':
            if (!state.onPremiseAvailable) continue;
            response = await generateOnPremise(messages, config, onStream);
            break;
          case 'cloud':
            if (!state.cloudAvailable) continue;
            response = await generateCloud(messages, config, onStream);
            break;
          default:
            continue;
        }

        return { response, decision };
      } catch {
        continue;
      }
    }

    throw new Error('All inference tiers failed');
  };

  return {
    routingConfig,
    setRoutingConfig,
    state,
    lastDecision,
    checkAvailability,
    generateWithRouting,
    determineRoute,
  };
}

function getModelForTier(tier: InferenceTier): string {
  switch (tier) {
    case 'browser':
      return 'Llama-3.1-8B-Instruct-q4f16_1-MLC';
    case 'on_premise':
      return 'llama-3-1-8b';
    case 'cloud':
      return 'gpt-4o';
    default:
      return 'auto';
  }
}

function getEstimatedLatency(tier: InferenceTier): number {
  switch (tier) {
    case 'browser':
      return 1500;
    case 'on_premise':
      return 300;
    case 'cloud':
      return 1000;
    default:
      return 500;
  }
}

function getEstimatedCost(tier: InferenceTier, messageLength: number): number {
  if (tier === 'cloud') {
    return calculateCloudCost(messageLength);
  }
  return 0;
}

function calculateCloudCost(messageLength: number): number {
  const estimatedTokens = messageLength / 4;
  return estimatedTokens * 0.00001;
}
