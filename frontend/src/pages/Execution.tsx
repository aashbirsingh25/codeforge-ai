import { useEffect, useState, useRef } from 'react';
import {
  Box,
  Typography,
  Grid,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  List,
  ListItem,
  Chip,
  Paper,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Stack,
} from '@mui/material';
import {
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  Assignment as AssignmentIcon,
  Terminal as TerminalIcon,
  History as HistoryIcon,
  Visibility as VisibilityIcon,
} from '@mui/icons-material';
import {
  executionService,
  ExecutionPlan,
  PlanningResponse,
  ExecutionResponse,
  Task,
} from '../services/executionService';
import { settingsService, ProviderInfo } from '../services/settingsService';

interface ConsoleLine {
  timestamp: string;
  type: string;
  message: string;
}

export default function Execution() {
  // Goal & Plan configuration state
  const [goal, setGoal] = useState('');
  const [strategies, setStrategies] = useState<string[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState('');
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [generatingPlan, setGeneratingPlan] = useState(false);
  const [generatedPlan, setGeneratedPlan] = useState<ExecutionPlan | null>(null);

  // Active run state
  const [executing, setExecuting] = useState(false);
  const [activeExecutionId, setActiveExecutionId] = useState<string | null>(null);
  const [activeStatus, setActiveStatus] = useState<string>('');
  const [consoleLogs, setConsoleLogs] = useState<ConsoleLine[]>([]);
  const [tasksState, setTasksState] = useState<Record<string, string>>({});

  // History state
  const [history, setHistory] = useState<ExecutionResponse[]>([]);
  const consoleEndRef = useRef<HTMLDivElement>(null);
  const sseCleanupRef = useRef<(() => void) | null>(null);

  // Load initial options: strategies, providers, history
  useEffect(() => {
    const loadInitData = async () => {
      try {
        const [strategiesList, providersList, historyList] = await Promise.all([
          executionService.getStrategies(),
          settingsService.getProviders(),
          executionService.getHistory(),
        ]);
        setStrategies(strategiesList);
        if (strategiesList.length > 0) setSelectedStrategy(strategiesList[0]);

        setProviders(providersList);
        const activeProv = providersList.find((p) => p.is_configured);
        if (activeProv) setSelectedProvider(activeProv.name);
        else if (providersList.length > 0) setSelectedProvider(providersList[0].name);

        setHistory(historyList);
      } catch (err) {
        console.error('Failed to load execution setup options', err);
      }
    };
    loadInitData();

    return () => {
      if (sseCleanupRef.current) sseCleanupRef.current();
    };
  }, []);

  useEffect(() => {
    consoleEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [consoleLogs]);

  const addConsoleLog = (type: string, message: string) => {
    const newLine: ConsoleLine = {
      timestamp: new Date().toLocaleTimeString(),
      type,
      message,
    };
    setConsoleLogs((prev) => [...prev, newLine]);
  };

  const handleGeneratePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim() || generatingPlan) return;

    setGeneratingPlan(true);
    setGeneratedPlan(null);
    try {
      const response: PlanningResponse = await executionService.generatePlan({
        goal,
        strategy: selectedStrategy,
        provider: selectedProvider,
      });
      setGeneratedPlan(response.plan);
      // Map tasks to local pending state
      const initialTaskStates: Record<string, string> = {};
      response.plan.tasks.forEach((t) => {
        initialTaskStates[t.id] = 'PENDING';
      });
      setTasksState(initialTaskStates);
    } catch (err) {
      console.error('Plan generation failed', err);
    } finally {
      setGeneratingPlan(false);
    }
  };

  const handleLaunchExecution = async () => {
    if (!generatedPlan || executing) return;

    setExecuting(true);
    setConsoleLogs([]);
    addConsoleLog('INFO', 'Initializing autonomous agent execution engine...');
    
    try {
      const runResponse = await executionService.executePlan(generatedPlan);
      const executionId = runResponse.execution_id;
      setActiveExecutionId(executionId);
      setActiveStatus(runResponse.status);
      addConsoleLog('SUCCESS', `Execution run registered. ID: ${executionId}`);

      // Start streaming SSE logs
      if (sseCleanupRef.current) sseCleanupRef.current();

      const cleanup = executionService.streamEvents(
        executionId,
        (event) => {
          const { type, data } = event;
          
          if (type === 'started') {
            setActiveStatus('RUNNING');
            addConsoleLog('INFO', `Agent active reasoning loop started.`);
          } else if (type === 'thinking') {
            setTasksState((prev) => ({ ...prev, [data.task_id]: 'RUNNING' }));
            addConsoleLog('THOUGHT', `[Thinking Task: ${data.task_id}] ${data.thought}`);
          } else if (type === 'tool_call') {
            addConsoleLog('ACTION', `[Tool Call] Using tool: "${data.tool_name}" with args: ${JSON.stringify(data.tool_args)}`);
          } else if (type === 'tool_result' || type === 'observation') {
            const output = data.content || data.output || '';
            const summary = output.length > 200 ? `${output.slice(0, 200)}...` : output;
            addConsoleLog('OBSERVATION', `[Observation] Tool returned: ${summary}`);
          } else if (type === 'completed') {
            setActiveStatus('COMPLETED');
            setTasksState((prev) => {
              const updated = { ...prev };
              Object.keys(updated).forEach((k) => {
                if (updated[k] === 'RUNNING') updated[k] = 'COMPLETED';
              });
              return updated;
            });
            addConsoleLog('SUCCESS', 'Autonomous run completed successfully!');
            setExecuting(false);
            refreshHistory();
          } else if (type === 'failed') {
            setActiveStatus('FAILED');
            addConsoleLog('ERROR', `Execution failed: ${data.error}`);
            setExecuting(false);
            refreshHistory();
          } else if (type === 'cancelled') {
            setActiveStatus('CANCELLED');
            addConsoleLog('WARN', 'Execution cancelled by user request.');
            setExecuting(false);
            refreshHistory();
          }
        },
        (error) => {
          console.error('SSE connection error:', error);
          addConsoleLog('ERROR', 'SSE Telemetry connection lost.');
        }
      );

      sseCleanupRef.current = cleanup;
    } catch (err) {
      console.error('Launch failed', err);
      setExecuting(false);
    }
  };

  const handleCancelExecution = async () => {
    if (!activeExecutionId) return;
    try {
      addConsoleLog('WARN', 'Sending cancellation request to execution manager...');
      await executionService.cancel(activeExecutionId);
    } catch (err) {
      console.error('Cancellation request failed', err);
    }
  };

  const refreshHistory = async () => {
    try {
      const historyList = await executionService.getHistory();
      setHistory(historyList);
    } catch (err) {
      console.error('Failed to reload history list', err);
    }
  };

  const viewHistoricalTrace = async (executionId: string) => {
    try {
      const trace = await executionService.getTrace(executionId);
      // Map trace list directly to logs console
      const traceLogs: ConsoleLine[] = [];
      trace.steps.forEach((step, idx) => {
        if (step.thought?.reasoning) {
          traceLogs.push({
            timestamp: `Step ${idx + 1}`,
            type: 'THOUGHT',
            message: step.thought.reasoning,
          });
        }
        if (step.action?.tool_name) {
          traceLogs.push({
            timestamp: `Step ${idx + 1}`,
            type: 'ACTION',
            message: `Called: "${step.action.tool_name}" with args: ${JSON.stringify(step.action.tool_args)}`,
          });
        }
        if (step.observation?.content) {
          traceLogs.push({
            timestamp: `Step ${idx + 1}`,
            type: 'OBSERVATION',
            message: step.observation.content,
          });
        }
      });
      setConsoleLogs(traceLogs);
      setActiveExecutionId(executionId);
      setActiveStatus('HISTORICAL TRACE');
      setGeneratedPlan(null); // Clear active plan viewer to highlight trace console
    } catch (err) {
      console.error('Failed to retrieve trace steps', err);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority.toUpperCase()) {
      case 'CRITICAL': return 'error';
      case 'HIGH': return 'warning';
      case 'MEDIUM': return 'primary';
      default: return 'default';
    }
  };

  const getStatusChip = (status: string) => {
    let color: 'success' | 'warning' | 'error' | 'info' | 'default' = 'default';
    if (status === 'COMPLETED' || status === 'SUCCESS') color = 'success';
    if (status === 'RUNNING') color = 'info';
    if (status === 'FAILED') color = 'error';
    if (status === 'CANCELLED') color = 'warning';
    return (
      <Chip
        label={status}
        size="small"
        color={color}
        sx={{
          fontFamily: 'Fira Code, monospace',
          fontWeight: 700,
          fontSize: '0.7rem',
          borderRadius: '4px',
        }}
      />
    );
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {/* Page Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #24304f', pb: 2.5 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: 'text.primary' }}>
            Orchestrator & Execution Planner
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
            Formulate detailed, graph-dependency plans and trace autonomous sub-agent execution pathways.
          </Typography>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Left Side: Draft configurations */}
        <Grid size={{ xs: 12, md: 5 }}>
          <Stack spacing={3}>
            {/* Planning request form */}
            <Paper variant="outlined" sx={{ p: 3, bgcolor: 'brand.panel', borderColor: '#24304f' }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <AssignmentIcon sx={{ color: 'accent.primary' }} /> Configure Target Goal
              </Typography>
              <Divider sx={{ borderColor: '#24304f', mb: 2.5 }} />

              <Box component="form" onSubmit={handleGeneratePlan} sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
                <TextField
                  label="What is your engineering objective?"
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  placeholder="e.g., Create a script that parses index.html and writes styles to index.css"
                  multiline
                  rows={4}
                  fullWidth
                  required
                  disabled={generatingPlan || executing}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      bgcolor: 'brand.bg',
                      borderRadius: '8px',
                      '& fieldset': { borderColor: '#24304f' },
                    },
                  }}
                />

                <Grid container spacing={2}>
                  <Grid size={6}>
                    <FormControl fullWidth size="small">
                      <InputLabel id="strategy-select-label">Strategy</InputLabel>
                      <Select
                        labelId="strategy-select-label"
                        value={selectedStrategy}
                        label="Strategy"
                        onChange={(e) => setSelectedStrategy(e.target.value)}
                        disabled={generatingPlan || executing}
                      >
                        {strategies.map((strat) => (
                          <MenuItem key={strat} value={strat} sx={{ textTransform: 'capitalize' }}>
                            {strat}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid size={6}>
                    <FormControl fullWidth size="small">
                      <InputLabel id="provider-select-label">Model Provider</InputLabel>
                      <Select
                        labelId="provider-select-label"
                        value={selectedProvider}
                        label="Model Provider"
                        onChange={(e) => setSelectedProvider(e.target.value)}
                        disabled={generatingPlan || executing}
                      >
                        {providers.map((p) => (
                          <MenuItem key={p.name} value={p.name} sx={{ textTransform: 'capitalize' }}>
                            {p.name} {p.is_configured ? '(Configured)' : '(Mock)'}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>

                <Button
                  type="submit"
                  variant="contained"
                  disabled={!goal.trim() || generatingPlan || executing}
                  sx={{
                    bgcolor: 'accent.primary',
                    color: 'brand.bg',
                    fontWeight: 700,
                    py: 1.25,
                    '&:hover': { bgcolor: 'accent.secondary' },
                  }}
                >
                  {generatingPlan ? <CircularProgress size={20} color="inherit" /> : 'Generate Execution Plan'}
                </Button>
              </Box>
            </Paper>

            {/* Generated Plan previewer */}
            {generatedPlan && (
              <Paper variant="outlined" sx={{ p: 3, bgcolor: 'brand.panel', borderColor: '#24304f' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>
                    Proposed Plan Tasks
                  </Typography>
                  <Button
                    variant="contained"
                    color="success"
                    startIcon={<PlayArrowIcon />}
                    onClick={handleLaunchExecution}
                    disabled={executing}
                    sx={{ bgcolor: 'accent.green', color: '#ffffff', fontWeight: 700 }}
                  >
                    Execute Plan
                  </Button>
                </Box>
                <Divider sx={{ borderColor: '#24304f', mb: 2 }} />

                <List sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {generatedPlan.tasks.map((task: Task) => (
                    <ListItem
                      key={task.id}
                      sx={{
                        bgcolor: 'brand.card',
                        border: '1px solid #24304f',
                        borderRadius: '8px',
                        p: 2,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'start',
                        gap: 1,
                      }}
                    >
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'accent.primary' }}>
                          [{task.id}] {task.title}
                        </Typography>
                        <Stack direction="row" spacing={1}>
                          <Chip label={task.priority} size="small" color={getPriorityColor(task.priority)} sx={{ fontSize: '0.6rem', height: 20 }} />
                          {getStatusChip(tasksState[task.id] || 'PENDING')}
                        </Stack>
                      </Box>
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                        {task.description}
                      </Typography>
                      {task.dependencies && task.dependencies.length > 0 && (
                        <Typography variant="caption" sx={{ color: 'text.disabled', fontFamily: 'Fira Code, monospace' }}>
                          Depends on: {task.dependencies.join(', ')}
                        </Typography>
                      )}
                    </ListItem>
                  ))}
                </List>
              </Paper>
            )}
          </Stack>
        </Grid>

        {/* Right Side: Console trace logs */}
        <Grid size={{ xs: 12, md: 7 }}>
          <Paper
            variant="outlined"
            sx={{
              p: 3,
              bgcolor: 'brand.panel',
              borderColor: '#24304f',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1 }}>
                <TerminalIcon sx={{ color: 'accent.primary' }} /> Live Execution Trail
              </Typography>
              {executing && (
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<StopIcon />}
                  onClick={handleCancelExecution}
                  sx={{ borderColor: 'error.main', color: 'error.main' }}
                >
                  Cancel Execution
                </Button>
              )}
            </Box>
            <Divider sx={{ borderColor: '#24304f', mb: 2 }} />

            {/* Terminal Window display */}
            <Box
              sx={{
                flex: 1,
                bgcolor: 'brand.code',
                border: '1px solid #24304f',
                borderRadius: '8px',
                p: 2.5,
                fontFamily: 'Fira Code, monospace',
                fontSize: '0.85rem',
                overflowY: 'auto',
                minHeight: '400px',
                maxHeight: '550px',
                display: 'flex',
                flexDirection: 'column',
                gap: 1.5,
              }}
            >
              {consoleLogs.length === 0 ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: 'text.disabled' }}>
                  // Live agent thoughts, tool logs, and execution traces will stream here.
                </Box>
              ) : (
                consoleLogs.map((log, i) => {
                  let typeColor = '#ffffff';
                  let msgColor = 'text.secondary';
                  if (log.type === 'SUCCESS') {
                    typeColor = '#10b981';
                    msgColor = 'accent.green';
                  } else if (log.type === 'ERROR') {
                    typeColor = '#ef4444';
                    msgColor = 'error.main';
                  } else if (log.type === 'WARN') {
                    typeColor = '#f59e0b';
                    msgColor = 'warning.main';
                  } else if (log.type === 'THOUGHT') {
                    typeColor = '#a855f7';
                    msgColor = '#ca8a04'; // highlight thought yellow or purple
                  } else if (log.type === 'ACTION') {
                    typeColor = '#00f2fe';
                    msgColor = 'text.primary';
                  }

                  return (
                    <Box key={i} sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
                        <Typography variant="caption" sx={{ color: 'text.disabled', fontFamily: 'inherit' }}>
                          [{log.timestamp}]
                        </Typography>
                        <Chip
                          label={log.type}
                          size="small"
                          sx={{
                            bgcolor: 'rgba(255,255,255,0.03)',
                            color: typeColor,
                            border: `1px solid ${typeColor}`,
                            fontSize: '0.6rem',
                            fontWeight: 700,
                            height: 18,
                          }}
                        />
                      </Box>
                      <Typography variant="body2" sx={{ color: msgColor, whiteSpace: 'pre-wrap', pl: 1, fontFamily: 'inherit', borderLeft: `2px solid ${typeColor}` }}>
                        {log.message}
                      </Typography>
                    </Box>
                  );
                })
              )}
              <div ref={consoleEndRef} />
            </Box>

            {activeStatus && (
              <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  Execution State:
                </Typography>
                {getStatusChip(activeStatus)}
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Historical Executions section */}
      <Paper variant="outlined" sx={{ p: 3, bgcolor: 'brand.panel', borderColor: '#24304f' }}>
        <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
          <HistoryIcon sx={{ color: 'accent.purple' }} /> Past Execution History
        </Typography>
        <Divider sx={{ borderColor: '#24304f', mb: 2.5 }} />

        <TableContainer component={Box}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Run ID</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Goal</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Start Time</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Duration</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {history.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ color: 'text.disabled', py: 3 }}>
                    No execution records found.
                  </TableCell>
                </TableRow>
              ) : (
                history.map((run) => (
                  <TableRow key={run.execution_id} sx={{ '&:hover': { bgcolor: 'rgba(255,255,255,0.01)' } }}>
                    <TableCell sx={{ fontFamily: 'Fira Code, monospace', fontSize: '0.75rem' }}>
                      {run.execution_id.slice(0, 8)}...
                    </TableCell>
                    <TableCell sx={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {run.plan?.goal || 'No goal specified'}
                    </TableCell>
                    <TableCell>{getStatusChip(run.status)}</TableCell>
                    <TableCell sx={{ color: 'text.secondary', fontSize: '0.8rem' }}>
                      {new Date(run.metrics?.start_time).toLocaleString()}
                    </TableCell>
                    <TableCell sx={{ fontFamily: 'Fira Code, monospace', fontSize: '0.8rem' }}>
                      {run.metrics?.duration_seconds ? `${run.metrics.duration_seconds.toFixed(1)}s` : 'N/A'}
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<VisibilityIcon />}
                        onClick={() => viewHistoricalTrace(run.execution_id)}
                        sx={{
                          borderColor: '#24304f',
                          color: 'accent.primary',
                          textTransform: 'none',
                          '&:hover': { borderColor: 'accent.primary' },
                        }}
                      >
                        Inspect Trace
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  );
}
