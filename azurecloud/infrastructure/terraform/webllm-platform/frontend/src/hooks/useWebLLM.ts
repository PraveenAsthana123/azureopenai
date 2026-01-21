import { useState, useCallback, useRef, useEffect } from 'react';
import * as webllm from '@mlc-ai/web-llm';

export interface WebLLMModel {
  id: string;
  name: string;
  size: string;
  quantization: string;
  status: 'not_loaded' | 'loading' | 'ready' | 'error';
  progress: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  model?: string;
  tier?: 'browser' | 'on_premise' | 'cloud';
  latency?: number;
}

export interface WebLLMConfig {
  enableStreaming: boolean;
  maxTokens: number;
  temperature: number;
  topP: number;
}

const AVAILABLE_MODELS: WebLLMModel[] = [
  {
    id: 'Llama-3.1-8B-Instruct-q4f16_1-MLC',
    name: 'Llama 3.1 8B',
    size: '4.5 GB',
    quantization: 'q4f16_1',
    status: 'not_loaded',
    progress: 0,
  },
  {
    id: 'Phi-3-mini-4k-instruct-q4f16_1-MLC',
    name: 'Phi-3 Mini',
    size: '2.3 GB',
    quantization: 'q4f16_1',
    status: 'not_loaded',
    progress: 0,
  },
  {
    id: 'Mistral-7B-Instruct-v0.3-q4f16_1-MLC',
    name: 'Mistral 7B',
    size: '4.1 GB',
    quantization: 'q4f16_1',
    status: 'not_loaded',
    progress: 0,
  },
  {
    id: 'gemma-2-2b-it-q4f16_1-MLC',
    name: 'Gemma 2 2B',
    size: '1.5 GB',
    quantization: 'q4f16_1',
    status: 'not_loaded',
    progress: 0,
  },
];

export function useWebLLM() {
  const [models, setModels] = useState<WebLLMModel[]>(AVAILABLE_MODELS);
  const [activeModel, setActiveModel] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gpuAvailable, setGpuAvailable] = useState<boolean | null>(null);

  const engineRef = useRef<webllm.MLCEngine | null>(null);

  useEffect(() => {
    checkWebGPUSupport();
  }, []);

  const checkWebGPUSupport = async () => {
    try {
      if (!navigator.gpu) {
        setGpuAvailable(false);
        setError('WebGPU is not supported in this browser');
        return;
      }
      const adapter = await navigator.gpu.requestAdapter();
      setGpuAvailable(!!adapter);
      if (!adapter) {
        setError('No WebGPU adapter found');
      }
    } catch (err) {
      setGpuAvailable(false);
      setError('Failed to check WebGPU support');
    }
  };

  const loadModel = useCallback(async (modelId: string) => {
    if (!gpuAvailable) {
      setError('WebGPU is not available');
      return;
    }

    setModels((prev) =>
      prev.map((m) =>
        m.id === modelId ? { ...m, status: 'loading', progress: 0 } : m
      )
    );
    setError(null);

    try {
      const initProgressCallback = (progress: webllm.InitProgressReport) => {
        setModels((prev) =>
          prev.map((m) =>
            m.id === modelId
              ? { ...m, progress: Math.round(progress.progress * 100) }
              : m
          )
        );
      };

      if (engineRef.current) {
        await engineRef.current.unload();
      }

      engineRef.current = await webllm.CreateMLCEngine(modelId, {
        initProgressCallback,
      });

      setModels((prev) =>
        prev.map((m) =>
          m.id === modelId
            ? { ...m, status: 'ready', progress: 100 }
            : { ...m, status: 'not_loaded', progress: 0 }
        )
      );
      setActiveModel(modelId);
    } catch (err) {
      console.error('Failed to load model:', err);
      setModels((prev) =>
        prev.map((m) =>
          m.id === modelId ? { ...m, status: 'error', progress: 0 } : m
        )
      );
      setError(err instanceof Error ? err.message : 'Failed to load model');
    }
  }, [gpuAvailable]);

  const unloadModel = useCallback(async () => {
    if (engineRef.current) {
      await engineRef.current.unload();
      engineRef.current = null;
      setActiveModel(null);
      setModels((prev) =>
        prev.map((m) => ({ ...m, status: 'not_loaded', progress: 0 }))
      );
    }
  }, []);

  const generateResponse = useCallback(
    async (
      messages: ChatMessage[],
      config: WebLLMConfig,
      onStream?: (chunk: string) => void
    ): Promise<string> => {
      if (!engineRef.current) {
        throw new Error('No model loaded');
      }

      setIsGenerating(true);
      setError(null);

      try {
        const formattedMessages = messages.map((m) => ({
          role: m.role,
          content: m.content,
        }));

        if (config.enableStreaming && onStream) {
          let fullResponse = '';
          const asyncChunks = await engineRef.current.chat.completions.create({
            messages: formattedMessages,
            max_tokens: config.maxTokens,
            temperature: config.temperature,
            top_p: config.topP,
            stream: true,
          });

          for await (const chunk of asyncChunks) {
            const delta = chunk.choices[0]?.delta?.content || '';
            fullResponse += delta;
            onStream(delta);
          }
          return fullResponse;
        } else {
          const response = await engineRef.current.chat.completions.create({
            messages: formattedMessages,
            max_tokens: config.maxTokens,
            temperature: config.temperature,
            top_p: config.topP,
          });
          return response.choices[0]?.message?.content || '';
        }
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Generation failed';
        setError(errorMessage);
        throw err;
      } finally {
        setIsGenerating(false);
      }
    },
    []
  );

  const getModelStats = useCallback(async () => {
    if (!engineRef.current) return null;
    try {
      const stats = await engineRef.current.runtimeStatsText();
      return stats;
    } catch {
      return null;
    }
  }, []);

  return {
    models,
    activeModel,
    isGenerating,
    error,
    gpuAvailable,
    loadModel,
    unloadModel,
    generateResponse,
    getModelStats,
  };
}
