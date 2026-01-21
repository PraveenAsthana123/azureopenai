import React from 'react';
import { Download, Trash2, Check, AlertCircle, Loader2, HardDrive } from 'lucide-react';
import { WebLLMModel } from '../hooks/useWebLLM';

interface ModelManagerProps {
  models: WebLLMModel[];
  activeModel: string | null;
  gpuAvailable: boolean | null;
  onLoadModel: (modelId: string) => void;
  onUnloadModel: () => void;
}

export const ModelManager: React.FC<ModelManagerProps> = ({
  models,
  activeModel,
  gpuAvailable,
  onLoadModel,
  onUnloadModel,
}) => {
  const getStatusIcon = (status: WebLLMModel['status']) => {
    switch (status) {
      case 'ready':
        return <Check className="w-5 h-5 text-green-500" />;
      case 'loading':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <HardDrive className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusText = (status: WebLLMModel['status'], progress: number) => {
    switch (status) {
      case 'ready':
        return 'Ready';
      case 'loading':
        return `Loading... ${progress}%`;
      case 'error':
        return 'Error';
      default:
        return 'Not loaded';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-800">Browser Models</h2>
        {gpuAvailable === false && (
          <div className="flex items-center gap-2 px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm">
            <AlertCircle className="w-4 h-4" />
            WebGPU not available
          </div>
        )}
        {gpuAvailable === true && (
          <div className="flex items-center gap-2 px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">
            <Check className="w-4 h-4" />
            WebGPU ready
          </div>
        )}
      </div>

      <div className="space-y-4">
        {models.map((model) => (
          <div
            key={model.id}
            className={`border rounded-lg p-4 transition-colors ${
              model.id === activeModel
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {getStatusIcon(model.status)}
                <div>
                  <h3 className="font-medium text-gray-800">{model.name}</h3>
                  <p className="text-sm text-gray-500">
                    {model.size} • {model.quantization}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span
                  className={`text-sm px-2 py-1 rounded ${
                    model.status === 'ready'
                      ? 'bg-green-100 text-green-700'
                      : model.status === 'loading'
                      ? 'bg-blue-100 text-blue-700'
                      : model.status === 'error'
                      ? 'bg-red-100 text-red-700'
                      : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {getStatusText(model.status, model.progress)}
                </span>

                {model.status === 'not_loaded' && gpuAvailable && (
                  <button
                    onClick={() => onLoadModel(model.id)}
                    className="p-2 text-blue-600 hover:bg-blue-100 rounded-lg transition-colors"
                    title="Load model"
                  >
                    <Download className="w-5 h-5" />
                  </button>
                )}

                {model.status === 'ready' && (
                  <button
                    onClick={onUnloadModel}
                    className="p-2 text-red-600 hover:bg-red-100 rounded-lg transition-colors"
                    title="Unload model"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                )}
              </div>
            </div>

            {model.status === 'loading' && (
              <div className="mt-3">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${model.progress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="font-medium text-gray-800 mb-2">About Browser Inference</h4>
        <ul className="text-sm text-gray-600 space-y-1">
          <li>• Models run entirely in your browser using WebGPU</li>
          <li>• No data leaves your device - complete privacy</li>
          <li>• First load downloads model weights (~2-5GB)</li>
          <li>• Subsequent loads use cached weights</li>
          <li>• Requires a GPU with 4GB+ VRAM for best performance</li>
        </ul>
      </div>
    </div>
  );
};
