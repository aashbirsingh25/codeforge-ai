import { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Paper,
  TextField,
  Button,
  Divider,
  List,
  ListItem,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  CircularProgress,
  Card,
  CardContent,
} from '@mui/material';
import {
  Search as SearchIcon,
  DeleteForever as DeleteIcon,
  Storage as StorageIcon,
  Visibility as VisibilityIcon,
  Topic as TopicIcon,
} from '@mui/icons-material';
import { memoryService, MemoryEntry, MemoryStatistics } from '../services/memoryService';

export default function Memory() {
  const [stats, setStats] = useState<MemoryStatistics | null>(null);
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [searchResults, setSearchResults] = useState<{ entry: MemoryEntry; score: number }[]>([]);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingStats, setLoadingStats] = useState(true);

  // Inspector Dialog state
  const [selectedEntry, setSelectedEntry] = useState<MemoryEntry | null>(null);

  const loadStats = async () => {
    setLoadingStats(true);
    try {
      const statsData = await memoryService.getStatistics();
      setStats(statsData);
    } catch (err) {
      console.error('Failed to load memory stats', err);
    } finally {
      setLoadingStats(false);
    }
  };

  const loadDefaultList = async () => {
    setLoading(true);
    try {
      const list = await memoryService.listEntries(
        selectedCategory || undefined,
        undefined,
        30
      );
      setEntries(list);
      setSearchResults([]);
    } catch (err) {
      console.error('Failed to list memories', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
    loadDefaultList();
  }, [selectedCategory]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      loadDefaultList();
      return;
    }

    setLoading(true);
    try {
      const results = await memoryService.search(
        searchQuery,
        selectedCategory || undefined,
        undefined,
        20
      );
      setSearchResults(results.results);
      setEntries([]);
    } catch (err) {
      console.error('Memory search failed', err);
    } finally {
      setLoading(false);
    }
  };

  const handleClearMemory = async () => {
    if (window.confirm('WARNING: Wiping the memory store is permanent. Do you want to delete all entries from disk?')) {
      try {
        await memoryService.clearMemory();
        setSearchResults([]);
        setEntries([]);
        setSearchQuery('');
        loadStats();
        loadDefaultList();
      } catch (err) {
        console.error('Failed to clear memory store', err);
      }
    }
  };

  const formatDiskSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
  };

  const getCategoryColor = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'plan': return 'primary';
      case 'execution': return 'secondary';
      case 'tool_output': return 'warning';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {/* Page Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #24304f', pb: 2.5 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: 'text.primary' }}>
            Agent Memory Manager
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
            Audit localized semantic indexes, query vector nodes, and manage disk cache allocations.
          </Typography>
        </Box>
        {(stats?.total_entries ?? 0) > 0 && (
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={handleClearMemory}
            sx={{
              borderColor: 'error.main',
              bgcolor: 'rgba(239, 68, 68, 0.05)',
              '&:hover': { bgcolor: 'rgba(239, 68, 68, 0.15)' },
            }}
          >
            Wipe Memory Store
          </Button>
        )}
      </Box>

      {/* Stats Summary cards */}
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card sx={{ bgcolor: 'brand.panel', border: '1px solid #24304f', borderRadius: '12px' }}>
            <CardContent sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2.5 }}>
              <StorageIcon sx={{ color: 'accent.primary', fontSize: 32 }} />
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, textTransform: 'uppercase' }}>
                  Index Nodes Count
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5 }}>
                  {loadingStats ? <CircularProgress size={20} /> : stats?.total_entries ?? 0}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Card sx={{ bgcolor: 'brand.panel', border: '1px solid #24304f', borderRadius: '12px' }}>
            <CardContent sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2.5 }}>
              <TopicIcon sx={{ color: 'accent.purple', fontSize: 32 }} />
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, textTransform: 'uppercase' }}>
                  Memory Store Size
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5 }}>
                  {loadingStats ? <CircularProgress size={20} /> : formatDiskSize(stats?.storage_size_bytes ?? 0)}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Card sx={{ bgcolor: 'brand.panel', border: '1px solid #24304f', borderRadius: '12px' }}>
            <CardContent sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2.5 }}>
              <VisibilityIcon sx={{ color: 'accent.green', fontSize: 32 }} />
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, textTransform: 'uppercase' }}>
                  Last Modified
                </Typography>
                <Typography variant="body1" sx={{ mt: 0.5, fontWeight: 700, color: 'text.primary', fontSize: '0.95rem' }}>
                  {loadingStats ? (
                    <CircularProgress size={20} />
                  ) : stats?.last_updated ? (
                    new Date(stats.last_updated).toLocaleString()
                  ) : (
                    'Never'
                  )}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Search block */}
      <Paper
        variant="outlined"
        sx={{
          p: 3,
          bgcolor: 'brand.panel',
          borderColor: '#24304f',
        }}
      >
        <Box
          component="form"
          onSubmit={handleSearch}
          sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}
        >
          <TextField
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search memory text or content indexes..."
            sx={{
              flex: 1,
              minWidth: '250px',
              '& .MuiOutlinedInput-root': {
                bgcolor: 'brand.bg',
                borderRadius: '8px',
                '& fieldset': { borderColor: '#24304f' },
              },
            }}
          />

          <FormControl size="medium" sx={{ minWidth: '180px' }}>
            <InputLabel id="category-filter-label">Filter Category</InputLabel>
            <Select
              labelId="category-filter-label"
              value={selectedCategory}
              label="Filter Category"
              onChange={(e) => setSelectedCategory(e.target.value)}
              sx={{ bgcolor: 'brand.bg', borderRadius: '8px' }}
            >
              <MenuItem value="">All Categories</MenuItem>
              <MenuItem value="plan">Plan blue-prints</MenuItem>
              <MenuItem value="execution">Agent execution trials</MenuItem>
              <MenuItem value="tool_output">Tool executions</MenuItem>
            </Select>
          </FormControl>

          <Button
            type="submit"
            variant="contained"
            disabled={loading}
            sx={{
              bgcolor: 'accent.primary',
              color: 'brand.bg',
              fontWeight: 700,
              px: 4,
              py: 1.5,
              borderRadius: '8px',
              '&:hover': { bgcolor: 'accent.secondary' },
            }}
          >
            {loading ? <CircularProgress size={20} color="inherit" /> : <SearchIcon />}
          </Button>
        </Box>
      </Paper>

      {/* Memory Entries List */}
      <Paper variant="outlined" sx={{ p: 3, bgcolor: 'brand.panel', borderColor: '#24304f' }}>
        <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
          Memory Entries Registry
        </Typography>
        <Divider sx={{ borderColor: '#24304f', mb: 2 }} />

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress sx={{ color: 'accent.primary' }} />
          </Box>
        ) : entries.length === 0 && searchResults.length === 0 ? (
          <Typography variant="body2" align="center" sx={{ color: 'text.disabled', py: 6 }}>
            No memory entries stored. Try launching plans or asking chat questions.
          </Typography>
        ) : (
          <List sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* If search query has results */}
            {searchResults.map(({ entry, score }) => (
              <ListItem
                key={entry.id}
                sx={{
                  bgcolor: 'brand.card',
                  border: '1px solid #24304f',
                  borderRadius: '8px',
                  p: 2.5,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'start',
                  gap: 1.5,
                }}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                  <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
                    <Chip label={entry.category} size="small" color={getCategoryColor(entry.category)} sx={{ fontSize: '0.65rem', fontWeight: 700 }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'text.primary' }}>
                      {entry.title}
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
                    <Chip
                      label={`Relevance: ${score.toFixed(2)}`}
                      size="small"
                      sx={{ bgcolor: 'rgba(0, 242, 254, 0.15)', color: 'accent.primary', fontWeight: 600, border: '1px solid #00f2fe' }}
                    />
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<VisibilityIcon />}
                      onClick={() => setSelectedEntry(entry)}
                      sx={{ borderColor: '#24304f', color: 'accent.primary' }}
                    >
                      Inspect
                    </Button>
                  </Stack>
                </Box>
                <Typography variant="body2" sx={{ color: 'text.secondary', lineClamp: 2, display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: 2, overflow: 'hidden' }}>
                  {entry.content}
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.disabled' }}>
                  Timestamp: {new Date(entry.timestamp).toLocaleString()}
                </Typography>
              </ListItem>
            ))}

            {/* Default list entries */}
            {entries.map((entry) => (
              <ListItem
                key={entry.id}
                sx={{
                  bgcolor: 'brand.card',
                  border: '1px solid #24304f',
                  borderRadius: '8px',
                  p: 2.5,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'start',
                  gap: 1.5,
                }}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                  <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
                    <Chip label={entry.category} size="small" color={getCategoryColor(entry.category)} sx={{ fontSize: '0.65rem', fontWeight: 700 }} />
                    <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'text.primary' }}>
                      {entry.title}
                    </Typography>
                  </Stack>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<VisibilityIcon />}
                    onClick={() => setSelectedEntry(entry)}
                    sx={{ borderColor: '#24304f', color: 'accent.primary' }}
                  >
                    Inspect
                  </Button>
                </Box>
                <Typography variant="body2" sx={{ color: 'text.secondary', display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: 2, overflow: 'hidden' }}>
                  {entry.content}
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.disabled' }}>
                  Timestamp: {new Date(entry.timestamp).toLocaleString()}
                </Typography>
              </ListItem>
            ))}
          </List>
        )}
      </Paper>

      {/* Inspector Details Dialog */}
      <Dialog open={!!selectedEntry} onClose={() => setSelectedEntry(null)} maxWidth="md" fullWidth>
        {selectedEntry && (
          <>
            <DialogTitle sx={{ fontWeight: 700, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Memory Details: {selectedEntry.title}
              </Typography>
              <Chip label={selectedEntry.category.toUpperCase()} size="small" color={getCategoryColor(selectedEntry.category)} />
            </DialogTitle>
            <Divider sx={{ borderColor: '#24304f' }} />
            <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 3, pt: 3 }}>
              <Box>
                <Typography variant="caption" sx={{ color: 'text.disabled', fontWeight: 600, display: 'block', mb: 1 }}>
                  RAW CONTENT INDEX
                </Typography>
                <Box
                  sx={{
                    p: 2.5,
                    bgcolor: 'brand.code',
                    border: '1px solid #24304f',
                    borderRadius: '8px',
                    fontFamily: 'Fira Code, monospace',
                    fontSize: '0.85rem',
                    lineHeight: 1.6,
                    color: '#e2e8f0',
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {selectedEntry.content}
                </Box>
              </Box>

              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Typography variant="caption" sx={{ color: 'text.disabled', fontWeight: 600, display: 'block', mb: 0.5 }}>
                    METADATA SCHEMAS
                  </Typography>
                  <Box sx={{ p: 2, bgcolor: 'brand.bg', border: '1px solid #24304f', borderRadius: '8px' }}>
                    <pre style={{ margin: 0, fontSize: '0.75rem', fontFamily: 'Fira Code, monospace', overflowX: 'auto' }}>
                      {JSON.stringify(selectedEntry.metadata, null, 2)}
                    </pre>
                  </Box>
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Typography variant="caption" sx={{ color: 'text.disabled', fontWeight: 600, display: 'block', mb: 0.5 }}>
                    ASSOCIATED INDEX TAGS
                  </Typography>
                  <Box sx={{ p: 2, bgcolor: 'brand.bg', border: '1px solid #24304f', borderRadius: '8px', display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {selectedEntry.tags.map((tag) => (
                      <Chip key={tag} label={tag} size="small" variant="outlined" sx={{ fontSize: '0.75rem', fontFamily: 'Fira Code, monospace' }} />
                    ))}
                  </Box>
                </Grid>
              </Grid>
            </DialogContent>
            <DialogActions sx={{ p: 2.5 }}>
              <Button onClick={() => setSelectedEntry(null)} sx={{ color: 'text.secondary' }}>
                Close Inspector
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
}
