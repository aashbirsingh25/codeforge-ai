import { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Paper,
  Divider,
  LinearProgress,
  CircularProgress,
  Card,
  CardContent,
  Stack,
  Switch,
  FormControlLabel,
  Chip,
} from '@mui/material';
import {
  Assessment as AssessmentIcon,
  Memory as MemoryIcon,
  Speed as SpeedIcon,
  CloudQueue as CloudQueueIcon,
  AccessTime as AccessTimeIcon,
  TrendingUp as TrendingUpIcon,
  Dns as DnsIcon,
} from '@mui/icons-material';
import { metricsService, TelemetryMetrics } from '../services/metricsService';

export default function Metrics() {
  const [metrics, setMetrics] = useState<TelemetryMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchMetrics = async () => {
    try {
      const data = await metricsService.getMetrics();
      setMetrics(data);
    } catch (err) {
      console.error('Failed to fetch telemetry metrics', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchMetrics();
    }, 5000);

    return () => clearInterval(interval);
  }, [autoRefresh]);

  const formatUptime = (seconds: number) => {
    const d = Math.floor(seconds / (3600 * 24));
    const h = Math.floor((seconds % (3600 * 24)) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);

    const parts = [];
    if (d > 0) parts.push(`${d}d`);
    if (h > 0) parts.push(`${h}h`);
    if (m > 0) parts.push(`${m}m`);
    parts.push(`${s}s`);
    return parts.join(' ');
  };

  const getSuccessRate = () => {
    if (!metrics) return 100;
    const total = metrics.completed_executions + metrics.failed_executions;
    if (total === 0) return 100;
    return (metrics.completed_executions / total) * 100;
  };

  const memoryLimitMB = 512; // Base benchmark container limit
  const memoryMB = metrics ? metrics.memory_usage_bytes / (1024 * 1024) : 0;
  const memoryPercent = Math.min((memoryMB / memoryLimitMB) * 100, 100);

  // Calculate provider completions sum
  const providerStats = metrics?.provider_usage || {};
  const totalCompletions = Object.values(providerStats).reduce((a, b) => a + b, 0);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {/* Page Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #24304f', pb: 2.5 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: 'text.primary' }}>
            System Telemetry & Monitoring
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
            Real-time analytics, hardware metrics, and LLM completions metrics.
          </Typography>
        </Box>
        <FormControlLabel
          control={
            <Switch
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              color="primary"
            />
          }
          label="Auto-refresh (5s)"
          sx={{ color: 'text.secondary' }}
        />
      </Box>

      {loading && !metrics ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress sx={{ color: 'accent.primary' }} />
        </Box>
      ) : (
        <Grid container spacing={3}>
          {/* Main hardware cards */}
          <Grid size={{ xs: 12, md: 4 }}>
            <Card sx={{ bgcolor: 'brand.panel', border: '1px solid #24304f', borderRadius: '12px', height: '100%' }}>
              <CardContent sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="subtitle2" sx={{ color: 'text.secondary', fontWeight: 700, textTransform: 'uppercase' }}>
                    Process RSS Memory
                  </Typography>
                  <MemoryIcon sx={{ color: 'accent.primary' }} />
                </Box>
                <Box>
                  <Typography variant="h4" sx={{ fontWeight: 800 }}>
                    {memoryMB.toFixed(2)} MB
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    Allocated from benchmark benchmark size: {memoryLimitMB}MB
                  </Typography>
                </Box>
                <Box>
                  <LinearProgress
                    variant="determinate"
                    value={memoryPercent}
                    sx={{
                      height: 6,
                      borderRadius: 3,
                      bgcolor: 'brand.bg',
                      '& .MuiLinearProgress-bar': {
                        bgcolor: memoryPercent > 80 ? 'error.main' : 'accent.primary',
                      },
                    }}
                  />
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
                    <Typography variant="caption" sx={{ color: 'text.disabled' }}>0%</Typography>
                    <Typography variant="caption" sx={{ color: 'text.disabled' }}>{memoryPercent.toFixed(0)}% used</Typography>
                    <Typography variant="caption" sx={{ color: 'text.disabled' }}>100%</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, md: 4 }}>
            <Card sx={{ bgcolor: 'brand.panel', border: '1px solid #24304f', borderRadius: '12px', height: '100%' }}>
              <CardContent sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 2, alignItems: 'center', justifyContent: 'center' }}>
                <Box sx={{ position: 'relative', display: 'inline-flex' }}>
                  <CircularProgress
                    variant="determinate"
                    value={getSuccessRate()}
                    size={80}
                    thickness={5}
                    sx={{
                      color: 'accent.green',
                      [`& .MuiCircularProgress-circle`]: { strokeLinecap: 'round' },
                    }}
                  />
                  <Box
                    sx={{
                      top: 0,
                      left: 0,
                      bottom: 0,
                      right: 0,
                      position: 'absolute',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Typography variant="caption" component="div" color="text.primary" sx={{ fontWeight: 700, fontSize: '1rem' }}>
                      {getSuccessRate().toFixed(0)}%
                    </Typography>
                  </Box>
                </Box>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, textTransform: 'uppercase', color: 'text.secondary' }}>
                    Agent Success Rate
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.disabled' }}>
                    Based on total finished agent executions
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, md: 4 }}>
            <Card sx={{ bgcolor: 'brand.panel', border: '1px solid #24304f', borderRadius: '12px', height: '100%' }}>
              <CardContent sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 2.5 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="subtitle2" sx={{ color: 'text.secondary', fontWeight: 700, textTransform: 'uppercase' }}>
                    System Core Uptime
                  </Typography>
                  <AccessTimeIcon sx={{ color: 'accent.purple' }} />
                </Box>
                <Box>
                  <Typography variant="h4" sx={{ fontWeight: 800, fontFamily: 'Fira Code, monospace', color: 'accent.purple' }}>
                    {metrics ? formatUptime(metrics.uptime_seconds) : '0s'}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary', mt: 0.5, display: 'block' }}>
                    Uptime accumulator logs since initial API boot.
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Execution details */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper variant="outlined" sx={{ p: 3, bgcolor: 'brand.panel', borderColor: '#24304f', height: '100%' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <SpeedIcon sx={{ color: 'accent.primary' }} /> Execution Telemetry
              </Typography>
              <Divider sx={{ borderColor: '#24304f', mb: 2.5 }} />

              <Stack spacing={2}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>Active Executions</Typography>
                  <Chip label={metrics?.active_executions ?? 0} size="small" color="info" sx={{ fontWeight: 600 }} />
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>Completed Run Count</Typography>
                  <Chip label={metrics?.completed_executions ?? 0} size="small" color="success" sx={{ fontWeight: 600 }} />
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>Failed Run Count</Typography>
                  <Chip label={metrics?.failed_executions ?? 0} size="small" color="error" sx={{ fontWeight: 600 }} />
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>Cancelled Run Count</Typography>
                  <Chip label={metrics?.cancelled_executions ?? 0} size="small" color="warning" sx={{ fontWeight: 600 }} />
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>Average Run Duration</Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'Fira Code, monospace', fontWeight: 600 }}>
                    {metrics ? `${metrics.average_execution_duration_seconds.toFixed(2)}s` : 'N/A'}
                  </Typography>
                </Box>
              </Stack>
            </Paper>
          </Grid>

          {/* Provider usage details */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper variant="outlined" sx={{ p: 3, bgcolor: 'brand.panel', borderColor: '#24304f', height: '100%' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <CloudQueueIcon sx={{ color: 'accent.purple' }} /> Provider Completion Stats
              </Typography>
              <Divider sx={{ borderColor: '#24304f', mb: 2.5 }} />

              {Object.keys(providerStats).length === 0 ? (
                <Typography variant="body2" align="center" sx={{ color: 'text.disabled', py: 4 }}>
                  No LLM request logs tracked.
                </Typography>
              ) : (
                <Stack spacing={3}>
                  {Object.entries(providerStats).map(([provider, count]) => {
                    const pct = totalCompletions > 0 ? (count / totalCompletions) * 100 : 0;
                    return (
                      <Box key={provider}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.75 }}>
                          <Typography variant="body2" sx={{ textTransform: 'capitalize', fontWeight: 600 }}>
                            {provider}
                          </Typography>
                          <Typography variant="body2" sx={{ fontFamily: 'Fira Code, monospace', color: 'text.secondary' }}>
                            {count} requests ({pct.toFixed(0)}%)
                          </Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={pct}
                          sx={{
                            height: 6,
                            borderRadius: 3,
                            bgcolor: 'brand.bg',
                            '& .MuiLinearProgress-bar': {
                              bgcolor: provider === 'gemini' ? 'accent.primary' : 'accent.purple',
                            },
                          }}
                        />
                      </Box>
                    );
                  })}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pt: 1 }}>
                    <Typography variant="body2" sx={{ color: 'text.disabled', fontWeight: 600 }}>
                      Aggregate LLM Queries
                    </Typography>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, color: 'accent.primary' }}>
                      {totalCompletions} Queries
                    </Typography>
                  </Box>
                </Stack>
              )}
            </Paper>
          </Grid>

          {/* Infrastructure specs */}
          <Grid size={12}>
            <Paper variant="outlined" sx={{ p: 3, bgcolor: 'brand.panel', borderColor: '#24304f' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <DnsIcon sx={{ color: 'accent.green' }} /> Infrastructure Registry Statuses
              </Typography>
              <Divider sx={{ borderColor: '#24304f', mb: 2.5 }} />

              <Grid container spacing={3}>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}>
                    <TrendingUpIcon sx={{ color: 'accent.primary' }} />
                    <Box>
                      <Typography variant="caption" sx={{ color: 'text.disabled', fontWeight: 600 }}>
                        TELEMETRY API TRAFFIC
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 700 }}>
                        {metrics?.request_count ?? 0} API Calls Recv
                      </Typography>
                    </Box>
                  </Stack>
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}>
                    <AssessmentIcon sx={{ color: 'accent.purple' }} />
                    <Box>
                      <Typography variant="caption" sx={{ color: 'text.disabled', fontWeight: 600 }}>
                        ACTIVE DISPATCH QUEUE
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 700 }}>
                        {metrics?.active_executions ?? 0} Tasks active
                      </Typography>
                    </Box>
                  </Stack>
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}>
                    <MemoryIcon sx={{ color: 'accent.green' }} />
                    <Box>
                      <Typography variant="caption" sx={{ color: 'text.disabled', fontWeight: 600 }}>
                        TELEMETRY DRIVER
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 700 }}>
                        FastAPI Tracker Active
                      </Typography>
                    </Box>
                  </Stack>
                </Grid>
              </Grid>
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}
