import { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Paper,
  TextField,
  Button,
  Divider,
  Chip,
  CircularProgress,
  Card,
  CardContent,
  Stack,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Dns as DnsIcon,
  VpnKey as VpnKeyIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  SmartToy as SmartToyIcon,
} from '@mui/icons-material';
import { settingsService, SystemSettings, ProviderInfo, ProviderHealthResponse } from '../services/settingsService';

export default function Settings() {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [health, setHealth] = useState<ProviderHealthResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [settingsData, providersData, healthData] = await Promise.all([
        settingsService.getSettings(),
        settingsService.getProviders(),
        settingsService.checkProvidersHealth(),
      ]);
      setSettings(settingsData);
      setProviders(providersData);
      setHealth(healthData);
    } catch (err) {
      console.error('Failed to load settings data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await settingsService.updateSettings();
      alert('Configurations saved successfully (Operational mockup applied).');
    } catch (err) {
      console.error('Failed to save settings', err);
    } finally {
      setSaving(false);
    }
  };

  const getProviderHealth = (providerName: string) => {
    const status = health.find((h) => h.provider === providerName);
    return status || { provider: providerName, status: 'unhealthy' as const, error_message: 'Not verified' };
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {/* Page Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #24304f', pb: 2.5 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: 'text.primary' }}>
            System Settings
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
            Manage core operational parameters, model configurations, and provider API credentials.
          </Typography>
        </Box>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress sx={{ color: 'accent.primary' }} />
        </Box>
      ) : (
        <Grid container spacing={3}>
          {/* Left Column: System Configurations */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper
              variant="outlined"
              component="form"
              onSubmit={handleSave}
              sx={{
                p: 3,
                bgcolor: 'brand.panel',
                borderColor: '#24304f',
                display: 'flex',
                flexDirection: 'column',
                gap: 2.5,
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1 }}>
                <SettingsIcon sx={{ color: 'accent.primary' }} /> Operational Parameters
              </Typography>
              <Divider sx={{ borderColor: '#24304f' }} />

              <TextField
                label="Project Base Name"
                value={settings?.project_name ?? ''}
                disabled
                fullWidth
                helperText="Compiled from backend settings"
                sx={{
                  '& .MuiOutlinedInput-root': {
                    bgcolor: 'brand.bg',
                    borderRadius: '8px',
                    '& fieldset': { borderColor: '#24304f' },
                  },
                }}
              />

              <TextField
                label="Base API String"
                value={settings?.api_v1_str ?? ''}
                disabled
                fullWidth
                sx={{
                  '& .MuiOutlinedInput-root': {
                    bgcolor: 'brand.bg',
                    borderRadius: '8px',
                    '& fieldset': { borderColor: '#24304f' },
                  },
                }}
              />

              <TextField
                label="Local Target Workspace Directory"
                value={settings?.workspace_dir ?? ''}
                disabled
                fullWidth
                sx={{
                  '& .MuiOutlinedInput-root': {
                    bgcolor: 'brand.bg',
                    borderRadius: '8px',
                    '& fieldset': { borderColor: '#24304f' },
                  },
                }}
              />

              <Button
                type="submit"
                variant="contained"
                disabled={saving}
                sx={{
                  bgcolor: 'accent.primary',
                  color: 'brand.bg',
                  fontWeight: 700,
                  py: 1.25,
                  borderRadius: '8px',
                  '&:hover': { bgcolor: 'accent.secondary' },
                }}
              >
                {saving ? <CircularProgress size={20} color="inherit" /> : 'Save Operational Configuration'}
              </Button>
            </Paper>
          </Grid>

          {/* Right Column: Model Providers info */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper variant="outlined" sx={{ p: 3, bgcolor: 'brand.panel', borderColor: '#24304f', display: 'flex', flexDirection: 'column', gap: 2.5 }}>
              <Typography variant="h6" sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1 }}>
                <DnsIcon sx={{ color: 'accent.purple' }} /> Model Providers Registry
              </Typography>
              <Divider sx={{ borderColor: '#24304f' }} />

              <Stack spacing={3}>
                {providers.map((provider) => {
                  const healthState = getProviderHealth(provider.name);
                  const isHealthy = healthState.status === 'healthy';

                  return (
                    <Card
                      key={provider.name}
                      variant="outlined"
                      sx={{ bgcolor: 'brand.card', borderColor: '#24304f', borderRadius: '10px' }}
                    >
                      <CardContent sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {/* Header details */}
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                          <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
                            <SmartToyIcon sx={{ color: isHealthy ? 'accent.primary' : 'text.disabled' }} />
                            <Typography variant="subtitle1" sx={{ fontWeight: 700, textTransform: 'capitalize' }}>
                              {provider.name}
                            </Typography>
                          </Stack>
                          <Chip
                            icon={isHealthy ? <CheckCircleIcon sx={{ fontSize: 16 }} /> : <CancelIcon sx={{ fontSize: 16 }} />}
                            label={isHealthy ? 'CONFIGURED' : 'UNCONFIGURED'}
                            size="small"
                            color={isHealthy ? 'success' : 'error'}
                            sx={{
                              fontSize: '0.65rem',
                              fontWeight: 700,
                              borderRadius: '4px',
                            }}
                          />
                        </Box>

                        {/* Available models list */}
                        <Box>
                          <Typography variant="caption" sx={{ color: 'text.disabled', fontWeight: 600, display: 'block', mb: 1 }}>
                            SUPPORTED MODELS
                          </Typography>
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
                            {provider.available_models.map((model) => (
                              <Chip
                                key={model}
                                label={model}
                                size="small"
                                variant="outlined"
                                sx={{
                                  fontSize: '0.7rem',
                                  fontFamily: 'Fira Code, monospace',
                                  borderColor: 'rgba(255,255,255,0.05)',
                                  bgcolor: 'brand.bg',
                                }}
                              />
                            ))}
                          </Box>
                        </Box>

                        {/* Error logs if any */}
                        {healthState.error_message && (
                          <Box
                            sx={{
                              p: 1.5,
                              bgcolor: 'rgba(239, 68, 68, 0.05)',
                              border: '1px solid rgba(239, 68, 68, 0.2)',
                              borderRadius: '6px',
                            }}
                          >
                            <Typography variant="caption" sx={{ color: 'error.main', display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <VpnKeyIcon sx={{ fontSize: 14 }} /> {healthState.error_message}
                            </Typography>
                          </Box>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </Stack>
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}
