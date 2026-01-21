import React, { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from 'recharts';
import {
  Activity,
  Cpu,
  Cloud,
  Globe,
  Users,
  MessageSquare,
  Clock,
  DollarSign,
  TrendingUp,
  AlertTriangle,
} from 'lucide-react';

interface DashboardStats {
  totalRequests: number;
  browserRequests: number;
  onPremiseRequests: number;
  cloudRequests: number;
  avgLatency: number;
  totalCost: number;
  activeUsers: number;
  errorRate: number;
}

interface UsageData {
  time: string;
  browser: number;
  onPremise: number;
  cloud: number;
}

const COLORS = ['#10B981', '#3B82F6', '#8B5CF6'];

const StatCard: React.FC<{
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: number;
  color?: string;
}> = ({ title, value, icon, trend, color = 'blue' }) => (
  <div className="bg-white rounded-lg shadow p-6">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm text-gray-500">{title}</p>
        <p className="text-2xl font-semibold text-gray-800 mt-1">{value}</p>
        {trend !== undefined && (
          <p
            className={`text-sm mt-1 ${
              trend >= 0 ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {trend >= 0 ? '+' : ''}
            {trend}% from last hour
          </p>
        )}
      </div>
      <div className={`p-3 rounded-full bg-${color}-100`}>{icon}</div>
    </div>
  </div>
);

export const UCPDashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats>({
    totalRequests: 15234,
    browserRequests: 4521,
    onPremiseRequests: 8234,
    cloudRequests: 2479,
    avgLatency: 342,
    totalCost: 127.45,
    activeUsers: 234,
    errorRate: 0.12,
  });

  const [usageData, setUsageData] = useState<UsageData[]>([]);
  const [timeRange, setTimeRange] = useState<'1h' | '24h' | '7d'>('24h');

  useEffect(() => {
    const generateUsageData = () => {
      const data: UsageData[] = [];
      const points = timeRange === '1h' ? 12 : timeRange === '24h' ? 24 : 7;

      for (let i = 0; i < points; i++) {
        data.push({
          time:
            timeRange === '7d'
              ? `Day ${i + 1}`
              : timeRange === '24h'
              ? `${i}:00`
              : `${i * 5}min`,
          browser: Math.floor(Math.random() * 200 + 100),
          onPremise: Math.floor(Math.random() * 400 + 200),
          cloud: Math.floor(Math.random() * 150 + 50),
        });
      }
      setUsageData(data);
    };

    generateUsageData();
  }, [timeRange]);

  const pieData = [
    { name: 'Browser', value: stats.browserRequests },
    { name: 'On-Premise', value: stats.onPremiseRequests },
    { name: 'Cloud', value: stats.cloudRequests },
  ];

  const latencyData = [
    { tier: 'Browser', latency: 1500, color: '#10B981' },
    { tier: 'On-Premise', latency: 300, color: '#3B82F6' },
    { tier: 'Cloud', latency: 800, color: '#8B5CF6' },
  ];

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">
              Universal Control Plane
            </h1>
            <p className="text-gray-500">WebLLM Platform Dashboard</p>
          </div>
          <div className="flex gap-2">
            {(['1h', '24h', '7d'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  timeRange === range
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-100'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Total Requests"
            value={stats.totalRequests.toLocaleString()}
            icon={<MessageSquare className="w-6 h-6 text-blue-600" />}
            trend={12}
            color="blue"
          />
          <StatCard
            title="Avg Latency"
            value={`${stats.avgLatency}ms`}
            icon={<Clock className="w-6 h-6 text-green-600" />}
            trend={-5}
            color="green"
          />
          <StatCard
            title="Total Cost"
            value={`$${stats.totalCost.toFixed(2)}`}
            icon={<DollarSign className="w-6 h-6 text-purple-600" />}
            trend={8}
            color="purple"
          />
          <StatCard
            title="Active Users"
            value={stats.activeUsers}
            icon={<Users className="w-6 h-6 text-orange-600" />}
            trend={15}
            color="orange"
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-3 gap-6 mb-8">
          {/* Usage Over Time */}
          <div className="col-span-2 bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              Request Volume by Tier
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={usageData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="browser" stackId="a" fill="#10B981" name="Browser" />
                <Bar
                  dataKey="onPremise"
                  stackId="a"
                  fill="#3B82F6"
                  name="On-Premise"
                />
                <Bar dataKey="cloud" stackId="a" fill="#8B5CF6" name="Cloud" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Tier Distribution */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              Tier Distribution
            </h3>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex justify-center gap-4 mt-4">
              {pieData.map((entry, index) => (
                <div key={entry.name} className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: COLORS[index] }}
                  />
                  <span className="text-sm text-gray-600">{entry.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Second Row */}
        <div className="grid grid-cols-3 gap-6">
          {/* Latency by Tier */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              Average Latency by Tier
            </h3>
            <div className="space-y-4">
              {latencyData.map((item) => (
                <div key={item.tier}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-600">{item.tier}</span>
                    <span className="font-medium">{item.latency}ms</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="h-2 rounded-full"
                      style={{
                        width: `${(item.latency / 2000) * 100}%`,
                        backgroundColor: item.color,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Model Usage */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              Top Models
            </h3>
            <div className="space-y-3">
              {[
                { name: 'Llama 3.1 8B', requests: 4521, tier: 'browser' },
                { name: 'Llama 3.1 70B', requests: 5234, tier: 'on_premise' },
                { name: 'GPT-4o', requests: 2479, tier: 'cloud' },
                { name: 'CodeLlama 34B', requests: 1800, tier: 'on_premise' },
                { name: 'Phi-3 Mini', requests: 1200, tier: 'browser' },
              ].map((model, index) => (
                <div
                  key={model.name}
                  className="flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400 text-sm">{index + 1}</span>
                    {model.tier === 'browser' && (
                      <Globe className="w-4 h-4 text-green-500" />
                    )}
                    {model.tier === 'on_premise' && (
                      <Cpu className="w-4 h-4 text-blue-500" />
                    )}
                    {model.tier === 'cloud' && (
                      <Cloud className="w-4 h-4 text-purple-500" />
                    )}
                    <span className="text-gray-700">{model.name}</span>
                  </div>
                  <span className="text-sm text-gray-500">
                    {model.requests.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* System Health */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              System Health
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Error Rate</span>
                <span
                  className={`font-medium ${
                    stats.errorRate < 1 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {stats.errorRate}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">GPU Utilization</span>
                <span className="font-medium text-blue-600">78%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Memory Usage</span>
                <span className="font-medium text-orange-600">65%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Queue Depth</span>
                <span className="font-medium text-gray-600">12</span>
              </div>

              <div className="pt-4 border-t">
                <div className="flex items-center gap-2 text-sm">
                  <Activity className="w-4 h-4 text-green-500" />
                  <span className="text-gray-600">All systems operational</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
