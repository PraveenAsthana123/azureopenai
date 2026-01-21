import React from 'react';
import { Globe, Cpu, Cloud, Zap, Shield, DollarSign, RefreshCw } from 'lucide-react';
import { RoutingConfig as RoutingConfigType, InferenceTier } from '../hooks/useHybridRouter';

interface RoutingConfigProps {
  config: RoutingConfigType;
  onChange: (config: RoutingConfigType) => void;
  onCheckAvailability: () => void;
  availability: {
    browserAvailable: boolean;
    onPremiseAvailable: boolean;
    cloudAvailable: boolean;
    isConnected: boolean;
  };
}

const TierButton: React.FC<{
  tier: InferenceTier;
  label: string;
  icon: React.ReactNode;
  description: string;
  selected: boolean;
  available: boolean;
  onClick: () => void;
}> = ({ tier, label, icon, description, selected, available, onClick }) => (
  <button
    onClick={onClick}
    disabled={!available && tier !== 'auto'}
    className={`flex flex-col items-center p-4 rounded-lg border-2 transition-all ${
      selected
        ? 'border-blue-500 bg-blue-50'
        : available || tier === 'auto'
        ? 'border-gray-200 hover:border-gray-300 bg-white'
        : 'border-gray-100 bg-gray-50 opacity-50 cursor-not-allowed'
    }`}
  >
    <div
      className={`p-2 rounded-full mb-2 ${
        selected ? 'bg-blue-100' : 'bg-gray-100'
      }`}
    >
      {icon}
    </div>
    <span className="font-medium text-gray-800">{label}</span>
    <span className="text-xs text-gray-500 mt-1 text-center">{description}</span>
    {!available && tier !== 'auto' && (
      <span className="text-xs text-red-500 mt-1">Unavailable</span>
    )}
  </button>
);

export const RoutingConfig: React.FC<RoutingConfigProps> = ({
  config,
  onChange,
  onCheckAvailability,
  availability,
}) => {
  const tiers: {
    tier: InferenceTier;
    label: string;
    icon: React.ReactNode;
    description: string;
  }[] = [
    {
      tier: 'auto',
      label: 'Auto',
      icon: <Zap className="w-5 h-5 text-yellow-600" />,
      description: 'Smart routing based on context',
    },
    {
      tier: 'browser',
      label: 'Browser',
      icon: <Globe className="w-5 h-5 text-green-600" />,
      description: 'Local WebGPU inference',
    },
    {
      tier: 'on_premise',
      label: 'On-Premise',
      icon: <Cpu className="w-5 h-5 text-blue-600" />,
      description: 'Private GPU cluster',
    },
    {
      tier: 'cloud',
      label: 'Cloud',
      icon: <Cloud className="w-5 h-5 text-purple-600" />,
      description: 'Azure OpenAI',
    },
  ];

  const getTierAvailability = (tier: InferenceTier): boolean => {
    switch (tier) {
      case 'browser':
        return availability.browserAvailable;
      case 'on_premise':
        return availability.onPremiseAvailable;
      case 'cloud':
        return availability.cloudAvailable;
      default:
        return true;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-800">Routing Configuration</h2>
        <button
          onClick={onCheckAvailability}
          className="flex items-center gap-2 px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Check Availability
        </button>
      </div>

      {/* Preferred Tier Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Preferred Inference Tier
        </label>
        <div className="grid grid-cols-4 gap-3">
          {tiers.map((t) => (
            <TierButton
              key={t.tier}
              {...t}
              selected={config.preferredTier === t.tier}
              available={getTierAvailability(t.tier)}
              onClick={() => onChange({ ...config, preferredTier: t.tier })}
            />
          ))}
        </div>
      </div>

      {/* Privacy Level */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">
          <Shield className="w-4 h-4 inline mr-1" />
          Privacy Level
        </label>
        <div className="flex gap-3">
          {(['low', 'medium', 'high'] as const).map((level) => (
            <button
              key={level}
              onClick={() => onChange({ ...config, privacyLevel: level })}
              className={`flex-1 py-2 px-4 rounded-lg border transition-colors ${
                config.privacyLevel === level
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <span className="capitalize">{level}</span>
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-2">
          High privacy routes sensitive data to browser or on-premise only
        </p>
      </div>

      {/* Latency Requirement */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">
          <Zap className="w-4 h-4 inline mr-1" />
          Latency Requirement
        </label>
        <div className="flex gap-3">
          {(['low', 'medium', 'high'] as const).map((level) => (
            <button
              key={level}
              onClick={() => onChange({ ...config, latencyRequirement: level })}
              className={`flex-1 py-2 px-4 rounded-lg border transition-colors ${
                config.latencyRequirement === level
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <span className="capitalize">{level}</span>
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Low latency prefers browser inference for quick responses
        </p>
      </div>

      {/* Options */}
      <div className="space-y-4">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={config.costOptimization}
            onChange={(e) =>
              onChange({ ...config, costOptimization: e.target.checked })
            }
            className="w-5 h-5 rounded"
          />
          <div>
            <span className="font-medium text-gray-800 flex items-center gap-1">
              <DollarSign className="w-4 h-4" />
              Cost Optimization
            </span>
            <span className="text-sm text-gray-500">
              Prefer free tiers (browser, on-premise) when possible
            </span>
          </div>
        </label>

        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={config.fallbackEnabled}
            onChange={(e) =>
              onChange({ ...config, fallbackEnabled: e.target.checked })
            }
            className="w-5 h-5 rounded"
          />
          <div>
            <span className="font-medium text-gray-800 flex items-center gap-1">
              <RefreshCw className="w-4 h-4" />
              Enable Fallback
            </span>
            <span className="text-sm text-gray-500">
              Automatically try other tiers if preferred tier fails
            </span>
          </div>
        </label>
      </div>

      {/* Status Indicators */}
      <div className="mt-6 pt-6 border-t">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Tier Status</h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="flex items-center gap-2">
            <div
              className={`w-3 h-3 rounded-full ${
                availability.browserAvailable ? 'bg-green-500' : 'bg-gray-300'
              }`}
            />
            <span className="text-sm text-gray-600">Browser</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className={`w-3 h-3 rounded-full ${
                availability.onPremiseAvailable ? 'bg-green-500' : 'bg-gray-300'
              }`}
            />
            <span className="text-sm text-gray-600">On-Premise</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className={`w-3 h-3 rounded-full ${
                availability.cloudAvailable ? 'bg-green-500' : 'bg-gray-300'
              }`}
            />
            <span className="text-sm text-gray-600">Cloud</span>
          </div>
        </div>
      </div>
    </div>
  );
};
