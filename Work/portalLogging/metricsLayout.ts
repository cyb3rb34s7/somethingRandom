// =====================================================================
// 1. MOCK METRICS DATA
// =====================================================================

// src/data/mockMetrics.ts
export interface MetricData {
  label: string;
  value: number;
  change: number;
  changeType: 'increase' | 'decrease' | 'neutral';
  period: string;
}

export interface ChartData {
  timestamp: string;
  requests: number;
  alarms: number;
  notifications: number;
  errors: number;
}

export interface ServiceHealthData {
  service: string;
  status: 'healthy' | 'warning' | 'error';
  uptime: number;
  responseTime: number;
  errorRate: number;
  lastError?: string;
}

// Dashboard metrics
export const dashboardMetrics: MetricData[] = [
  {
    label: "Total Requests",
    value: 2847,
    change: 12.5,
    changeType: 'increase',
    period: "vs last 24h"
  },
  {
    label: "Alarm Success Rate",
    value: 98.2,
    change: -0.3,
    changeType: 'decrease',
    period: "vs yesterday"
  },
  {
    label: "Notification Success Rate", 
    value: 99.7,
    change: 0.8,
    changeType: 'increase',
    period: "vs yesterday"
  },
  {
    label: "Avg Response Time",
    value: 145,
    change: -8.2,
    changeType: 'decrease',
    period: "ms vs last hour"
  }
];

// Timeline chart data (last 24 hours)
export const timelineData: ChartData[] = [
  { timestamp: "00:00", requests: 45, alarms: 28, notifications: 42, errors: 2 },
  { timestamp: "02:00", requests: 32, alarms: 19, notifications: 28, errors: 1 },
  { timestamp: "04:00", requests: 28, alarms: 15, notifications: 25, errors: 0 },
  { timestamp: "06:00", requests: 52, alarms: 34, notifications: 48, errors: 3 },
  { timestamp: "08:00", requests: 89, alarms: 58, notifications: 82, errors: 5 },
  { timestamp: "10:00", requests: 156, alarms: 98, notifications: 145, errors: 8 },
  { timestamp: "12:00", requests: 201, alarms: 134, notifications: 189, errors: 12 },
  { timestamp: "14:00", requests: 178, alarms: 115, notifications: 167, errors: 9 },
  { timestamp: "16:00", requests: 195, alarms: 128, notifications: 183, errors: 11 },
  { timestamp: "18:00", requests: 167, alarms: 109, notifications: 156, errors: 7 },
  { timestamp: "20:00", requests: 134, alarms: 87, notifications: 125, errors: 6 },
  { timestamp: "22:00", requests: 98, alarms: 62, notifications: 89, errors: 4 }
];

// Service health status
export const serviceHealthData: ServiceHealthData[] = [
  {
    service: "CMS-ADMIN",
    status: "healthy",
    uptime: 99.9,
    responseTime: 125,
    errorRate: 0.8
  },
  {
    service: "CMS-HISTORY", 
    status: "warning",
    uptime: 98.5,
    responseTime: 289,
    errorRate: 2.3,
    lastError: "Database connection timeout"
  },
  {
    service: "CMS-API",
    status: "healthy",
    uptime: 99.7,
    responseTime: 98,
    errorRate: 1.1
  },
  {
    service: "CMS-WORKER",
    status: "error", 
    uptime: 95.2,
    responseTime: 445,
    errorRate: 5.7,
    lastError: "Redis cache unavailable"
  }
];

// Error type distribution
export const errorTypeData = [
  { name: "Internal Server Error", value: 45, color: "#ef4444" },
  { name: "Timeout Error", value: 23, color: "#f59e0b" }, 
  { name: "Bad Request", value: 18, color: "#f97316" },
  { name: "Validation Error", value: 12, color: "#eab308" },
  { name: "Network Error", value: 8, color: "#84cc16" }
];

// =====================================================================
// 2. LAYOUT COMPONENTS 
// =====================================================================

// src/components/layout/Sidebar.tsx
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  Home,
  BarChart3,
  Search,
  FileText,
  Settings,
  Activity
} from 'lucide-react';

interface SidebarProps {
  className?: string;
}

const navigation = [
  { name: 'Overview', href: '/', icon: Home },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Logs Explorer', href: '/logs', icon: Search },
  { name: 'Reports', href: '/reports', icon: FileText },
  { name: 'Service Health', href: '/health', icon: Activity },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar({ className }: SidebarProps) {
  const location = useLocation();

  return (
    <div className={cn(
      "pb-12 min-h-screen w-64 bg-card border-r border-border",
      "flex flex-col animate-slide-in",
      className
    )}>
      {/* Logo/Brand */}
      <div className="px-6 py-6">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <Activity className="w-5 h-5 text-primary-foreground" />
          </div>
          <h1 className="text-xl font-bold text-foreground">
            CMS Monitor
          </h1>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 space-y-1">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          const Icon = item.icon;
          
          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                "group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200",
                "hover:bg-accent hover:text-accent-foreground",
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon className={cn(
                "mr-3 h-5 w-5 transition-colors",
                isActive ? "text-primary-foreground" : "text-muted-foreground group-hover:text-foreground"
              )} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Status Indicator */}
      <div className="px-6 py-4 border-t border-border">
        <div className="flex items-center space-x-2 text-sm text-muted-foreground">
          <div className="w-2 h-2 bg-success rounded-full animate-pulse-success"></div>
          <span>All systems operational</span>
        </div>
      </div>
    </div>
  );
}

// src/components/layout/Header.tsx
import React from 'react';
import { Bell, Calendar, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  const currentTime = new Date().toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });

  return (
    <header className="bg-background border-b border-border px-6 py-4 animate-fade-in">
      <div className="flex items-center justify-between">
        {/* Title Section */}
        <div className="flex flex-col">
          <h2 className="text-2xl font-bold text-foreground">{title}</h2>
          {subtitle && (
            <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>
          )}
        </div>

        {/* Controls Section */}
        <div className="flex items-center space-x-4">
          {/* Time Range Selector */}
          <Select defaultValue="24h">
            <SelectTrigger className="w-32">
              <Calendar className="w-4 h-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">Last Hour</SelectItem>
              <SelectItem value="6h">Last 6 Hours</SelectItem>
              <SelectItem value="24h">Last 24 Hours</SelectItem>
              <SelectItem value="7d">Last 7 Days</SelectItem>
              <SelectItem value="30d">Last 30 Days</SelectItem>
            </SelectContent>
          </Select>

          {/* Refresh Button */}
          <Button variant="outline" size="sm" className="flex items-center space-x-2">
            <RefreshCw className="w-4 h-4" />
            <span>Refresh</span>
          </Button>

          {/* Notifications */}
          <Button variant="outline" size="sm" className="relative">
            <Bell className="w-4 h-4" />
            <Badge 
              variant="destructive" 
              className="absolute -top-2 -right-2 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs"
            >
              3
            </Badge>
          </Button>

          {/* Current Time */}
          <div className="text-sm text-muted-foreground font-mono">
            {currentTime}
          </div>
        </div>
      </div>
    </header>
  );
}

// src/components/layout/Layout.tsx
import React from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

interface LayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
}

export function Layout({ children, title, subtitle }: LayoutProps) {
  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar />
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <Header title={title} subtitle={subtitle} />
        
        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="animate-fade-in">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

// =====================================================================
// 3. ROUTING SETUP
// =====================================================================

// src/App.tsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';

// Placeholder pages (we'll create these next)
const OverviewPage = () => (
  <div className="space-y-6">
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {/* Metric cards will go here */}
      <div className="bg-card p-6 rounded-lg border border-border">
        <h3 className="text-sm font-medium text-muted-foreground">Total Requests</h3>
        <p className="text-3xl font-bold text-foreground mt-2">2,847</p>
        <p className="text-xs text-success mt-1">↗ +12.5% vs yesterday</p>
      </div>
    </div>
    
    <div className="bg-card p-6 rounded-lg border border-border">
      <h3 className="text-lg font-semibold mb-4">Request Timeline</h3>
      <div className="h-64 flex items-center justify-center text-muted-foreground">
        📊 Chart will go here
      </div>
    </div>
  </div>
);

const AnalyticsPage = () => (
  <div className="text-center py-12">
    <h2 className="text-2xl font-bold">Analytics Dashboard</h2>
    <p className="text-muted-foreground mt-2">Coming soon...</p>
  </div>
);

const LogsPage = () => (
  <div className="text-center py-12">
    <h2 className="text-2xl font-bold">Logs Explorer</h2>
    <p className="text-muted-foreground mt-2">Coming soon...</p>
  </div>
);

const ReportsPage = () => (
  <div className="text-center py-12">
    <h2 className="text-2xl font-bold">Reports</h2>
    <p className="text-muted-foreground mt-2">Coming soon...</p>
  </div>
);

function App() {
  return (
    <Router>
      <Routes>
        <Route 
          path="/" 
          element={
            <Layout title="Dashboard Overview" subtitle="Real-time monitoring and alerts">
              <OverviewPage />
            </Layout>
          } 
        />
        <Route 
          path="/analytics" 
          element={
            <Layout title="Analytics" subtitle="Performance insights and trends">
              <AnalyticsPage />
            </Layout>
          } 
        />
        <Route 
          path="/logs" 
          element={
            <Layout title="Logs Explorer" subtitle="Search and filter system logs">
              <LogsPage />
            </Layout>
          } 
        />
        <Route 
          path="/reports" 
          element={
            <Layout title="Reports" subtitle="Generate and download reports">
              <ReportsPage />
            </Layout>
          } 
        />
      </Routes>
    </Router>
  );
}

export default App;

// =====================================================================
// 4. UTILITY FUNCTIONS
// =====================================================================

// src/lib/utils.ts (if not already exists)
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// src/utils/dateUtils.ts
export const formatTimestamp = (timestamp: string): string => {
  return new Date(timestamp).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
};

export const getRelativeTime = (timestamp: string): string => {
  const now = new Date();
  const time = new Date(timestamp);
  const diff = now.getTime() - time.getTime();
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return 'Just now';
};

// =====================================================================
// 5. TYPE DEFINITIONS
// =====================================================================

// src/types/dashboard.ts
export interface DashboardData {
  metrics: MetricData[];
  timeline: ChartData[];
  serviceHealth: ServiceHealthData[];
  errorDistribution: Array<{
    name: string;
    value: number;
    color: string;
  }>;
}

export interface FilterOptions {
  timeRange: '1h' | '6h' | '24h' | '7d' | '30d';
  sourceService?: string;
  logLevel?: 'INFO' | 'WARN' | 'ERROR';
  operation?: 'ALARM_REQUEST' | 'NOTIFICATION_REQUEST' | 'ALARM_ATTEMPT' | 'NOTIFICATION_ATTEMPT';
}