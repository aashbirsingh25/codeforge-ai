import { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Paper,
  TextField,
  Button,
  IconButton,
  Divider,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
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
} from '@mui/material';
import {
  Folder as FolderIcon,
  InsertDriveFile as FileIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
  Add as AddIcon,
  Search as SearchIcon,
  Code as CodeIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { workspaceService, FilesListResponse } from '../services/workspaceService';

export default function Workspace() {
  const [loading, setLoading] = useState(true);
  const [workspaceData, setWorkspaceData] = useState<FilesListResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Active file editing state
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState('');
  const [readingFile, setReadingFile] = useState(false);
  const [savingFile, setSavingFile] = useState(false);

  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newFilePath, setNewFilePath] = useState('');
  const [newFileContent, setNewFileContent] = useState('');
  const [creatingFile, setCreatingFile] = useState(false);

  const [projectDialogOpen, setProjectDialogOpen] = useState(false);
  const [projectType, setProjectType] = useState('fastapi');
  const [projectName, setProjectName] = useState('');
  const [generatingProject, setGeneratingProject] = useState(false);

  const loadWorkspaceFiles = async () => {
    setLoading(true);
    try {
      const data = await workspaceService.listFiles('.');
      setWorkspaceData(data);
    } catch (err) {
      console.error('Failed to load workspace files', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkspaceFiles();
  }, []);

  const handleSelectFile = async (path: string) => {
    setReadingFile(true);
    setSelectedFilePath(path);
    try {
      const data = await workspaceService.readFile(path);
      setFileContent(data.content);
    } catch (err) {
      console.error('Failed to read file', err);
    } finally {
      setReadingFile(false);
    }
  };

  const handleSaveFile = async () => {
    if (!selectedFilePath || savingFile) return;

    setSavingFile(true);
    try {
      const response = await workspaceService.updateFile(selectedFilePath, fileContent, true);
      if (response.applied) {
        alert('File saved successfully.');
        loadWorkspaceFiles();
      }
    } catch (err) {
      console.error('Failed to save file updates', err);
    } finally {
      setSavingFile(false);
    }
  };

  const handleDeleteFile = async (path: string) => {
    if (window.confirm(`Are you sure you want to permanently delete: ${path}?`)) {
      try {
        const response = await workspaceService.deleteFile(path);
        if (response.success) {
          if (selectedFilePath === path) {
            setSelectedFilePath(null);
            setFileContent('');
          }
          loadWorkspaceFiles();
        }
      } catch (err) {
        console.error('Failed to delete file', err);
      }
    }
  };

  const handleCreateFile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFilePath.trim() || creatingFile) return;

    setCreatingFile(true);
    try {
      const response = await workspaceService.createFile(newFilePath, newFileContent, true);
      if (response.success) {
        setCreateDialogOpen(false);
        setNewFilePath('');
        setNewFileContent('');
        loadWorkspaceFiles();
        handleSelectFile(newFilePath);
      }
    } catch (err) {
      console.error('Failed to create file', err);
    } finally {
      setCreatingFile(false);
    }
  };

  const handleGenerateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName.trim() || generatingProject) return;

    setGeneratingProject(true);
    try {
      const response = await workspaceService.createProject(projectType, projectName);
      alert(response.message);
      setProjectDialogOpen(false);
      setProjectName('');
      loadWorkspaceFiles();
    } catch (err) {
      console.error('Failed to generate project boilerplate', err);
    } finally {
      setGeneratingProject(false);
    }
  };

  // Helper to resolve tracking chip
  const getFileTrackingChip = (path: string) => {
    if (!workspaceData) return null;
    const { tracking } = workspaceData;

    let label = '';
    let color: 'success' | 'warning' | 'default' = 'default';

    if (tracking.modified?.includes(path)) {
      label = 'Modified';
      color = 'warning';
    } else if (tracking.untracked?.includes(path)) {
      label = 'Untracked';
      color = 'success';
    } else {
      return null;
    }

    return (
      <Chip
        label={label}
        size="small"
        color={color}
        sx={{
          fontSize: '0.6rem',
          height: 18,
          borderRadius: '4px',
          fontWeight: 600,
        }}
      />
    );
  };

  const filteredFiles = workspaceData?.files.filter((file) =>
    file.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 128px)', gap: 3 }}>
      {/* Page Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #24304f', pb: 2.5 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: 'text.primary' }}>
            Workspace Manager
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
            Browse code structures, inspect repository files, and scaffold project templates.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1.5}>
          <Button
            variant="outlined"
            startIcon={<CodeIcon />}
            onClick={() => setProjectDialogOpen(true)}
            sx={{
              borderColor: 'accent.primary',
              color: 'accent.primary',
              '&:hover': { borderColor: 'accent.secondary', bgcolor: 'rgba(0, 242, 254, 0.05)' },
            }}
          >
            Scaffold Project
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
            sx={{
              bgcolor: 'accent.primary',
              color: 'brand.bg',
              fontWeight: 700,
              '&:hover': { bgcolor: 'accent.secondary' },
            }}
          >
            New File
          </Button>
        </Stack>
      </Box>

      {/* Main split dashboard view */}
      <Grid container spacing={3} sx={{ flex: 1, minHeight: 0 }}>
        {/* Left Side: File tree / explorer */}
        <Grid size={{ xs: 12, md: 4 }} sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <Paper
            variant="outlined"
            sx={{
              p: 2,
              bgcolor: 'brand.panel',
              borderColor: '#24304f',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
              overflow: 'hidden',
            }}
          >
            <Stack direction="row" spacing={1}>
              <TextField
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search file structures..."
                size="small"
                fullWidth
                slotProps={{
                  input: {
                    startAdornment: <SearchIcon fontSize="small" sx={{ mr: 1, color: 'text.disabled' }} />,
                  }
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    bgcolor: 'brand.bg',
                    borderRadius: '6px',
                    '& fieldset': { borderColor: '#24304f' },
                  },
                }}
              />
              <IconButton onClick={loadWorkspaceFiles} sx={{ color: 'accent.primary' }}>
                <RefreshIcon />
              </IconButton>
            </Stack>
            <Divider sx={{ borderColor: '#24304f' }} />

            {/* Scrollable File List */}
            <Box sx={{ flex: 1, overflowY: 'auto', pr: 0.5 }}>
              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                  <CircularProgress size={24} sx={{ color: 'accent.primary' }} />
                </Box>
              ) : filteredFiles.length === 0 ? (
                <Typography variant="body2" align="center" sx={{ color: 'text.disabled', py: 4 }}>
                  No matching files found.
                </Typography>
              ) : (
                <List disablePadding>
                  {filteredFiles.map((file) => {
                    const isSelected = selectedFilePath === file;
                    return (
                      <ListItem
                        key={file}
                        disablePadding
                        secondaryAction={
                          <IconButton edge="end" size="small" color="error" onClick={() => handleDeleteFile(file)}>
                            <DeleteIcon fontSize="inherit" />
                          </IconButton>
                        }
                      >
                        <ListItemButton
                          onClick={() => handleSelectFile(file)}
                          sx={{
                            borderRadius: '6px',
                            py: 1,
                            mr: 2.5,
                            bgcolor: isSelected ? 'rgba(0, 242, 254, 0.06)' : 'transparent',
                            color: isSelected ? 'accent.primary' : 'text.secondary',
                            '&:hover': { bgcolor: 'rgba(255,255,255,0.03)', color: 'text.primary' },
                          }}
                        >
                          <ListItemIcon sx={{ minWidth: 32, color: 'inherit' }}>
                            <FileIcon fontSize="small" />
                          </ListItemIcon>
                          <ListItemText
                            primary={
                              <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
                                <Typography
                                  variant="body2"
                                  noWrap
                                  sx={{
                                    fontFamily: 'Fira Code, monospace',
                                    fontSize: '0.8rem',
                                    fontWeight: isSelected ? 600 : 500,
                                  }}
                                >
                                  {file}
                                </Typography>
                                {getFileTrackingChip(file)}
                              </Stack>
                            }
                          />
                        </ListItemButton>
                      </ListItem>
                    );
                  })}
                </List>
              )}
            </Box>
          </Paper>
        </Grid>

        {/* Right Side: File code editor */}
        <Grid size={{ xs: 12, md: 8 }} sx={{ height: '100%' }}>
          <Paper
            variant="outlined"
            sx={{
              bgcolor: 'brand.panel',
              borderColor: '#24304f',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            {selectedFilePath ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                {/* Editor Header panel */}
                <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #24304f', bgcolor: 'rgba(25, 35, 58, 0.2)' }}>
                  <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
                    <FolderIcon sx={{ color: 'accent.primary', fontSize: 18 }} />
                    <Typography variant="subtitle2" sx={{ fontFamily: 'Fira Code, monospace', fontWeight: 600, color: 'text.primary' }}>
                      {selectedFilePath}
                    </Typography>
                  </Stack>
                  <Button
                    variant="contained"
                    size="small"
                    startIcon={savingFile ? <CircularProgress size={14} color="inherit" /> : <SaveIcon />}
                    onClick={handleSaveFile}
                    disabled={savingFile || readingFile}
                    sx={{
                      bgcolor: 'accent.green',
                      color: '#ffffff',
                      fontWeight: 700,
                      '&:hover': { bgcolor: 'rgba(16, 185, 129, 0.8)' },
                    }}
                  >
                    Save File
                  </Button>
                </Box>

                {/* Text editor body */}
                <Box sx={{ flex: 1, minHeight: 0, position: 'relative' }}>
                  {readingFile ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                      <CircularProgress size={30} sx={{ color: 'accent.primary' }} />
                    </Box>
                  ) : (
                    <TextField
                      value={fileContent}
                      onChange={(e) => setFileContent(e.target.value)}
                      multiline
                      fullWidth
                      variant="standard"
                      slotProps={{
                        input: {
                          disableUnderline: true,
                          sx: {
                            fontFamily: 'Fira Code, monospace',
                            fontSize: '0.85rem',
                            color: '#e2e8f0',
                            lineHeight: 1.6,
                            p: 3,
                            height: '100%',
                            overflowY: 'auto',
                            alignItems: 'flex-start',
                          },
                        }
                      }}
                      sx={{
                        height: '100%',
                        bgcolor: 'brand.code',
                        '& .MuiInputBase-root': {
                          height: '100%',
                        },
                      }}
                    />
                  )}
                </Box>
              </Box>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 1.5, p: 4, textAlign: 'center' }}>
                <CodeIcon sx={{ fontSize: 50, color: 'text.disabled' }} />
                <Typography variant="body1" sx={{ color: 'text.primary', fontWeight: 600 }}>
                  No File Selected
                </Typography>
                <Typography variant="body2" sx={{ color: 'text.secondary', maxWidth: 350 }}>
                  Select a codebase path from the file list to view, edit, or commit localized edits directly.
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Scaffold template Project dialog */}
      <Dialog open={projectDialogOpen} onClose={() => setProjectDialogOpen(false)} maxWidth="sm" fullWidth>
        <Box component="form" onSubmit={handleGenerateProject}>
          <DialogTitle sx={{ fontWeight: 700 }}>Scaffold Boilerplate Project</DialogTitle>
          <Divider sx={{ borderColor: '#24304f' }} />
          <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 3 }}>
            <FormControl fullWidth>
              <InputLabel id="project-type-label">Project Blueprint Type</InputLabel>
              <Select
                labelId="project-type-label"
                value={projectType}
                label="Project Blueprint Type"
                onChange={(e) => setProjectType(e.target.value)}
              >
                <MenuItem value="fastapi">FastAPI Server Blueprint</MenuItem>
                <MenuItem value="flask">Flask App Blueprint</MenuItem>
                <MenuItem value="cli">Python CLI Tool Blueprint</MenuItem>
                <MenuItem value="package">Python Pip Package Boilerplate</MenuItem>
                <MenuItem value="script">Raw Utility Script Blueprint</MenuItem>
              </Select>
            </FormControl>

            <TextField
              label="Scaffold Folder/Project Name"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="e.g., database_crawler"
              fullWidth
              required
            />
          </DialogContent>
          <DialogActions sx={{ p: 2.5 }}>
            <Button onClick={() => setProjectDialogOpen(false)} sx={{ color: 'text.secondary' }}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={!projectName.trim() || generatingProject}
              sx={{ bgcolor: 'accent.primary', color: 'brand.bg', fontWeight: 700 }}
            >
              {generatingProject ? <CircularProgress size={20} color="inherit" /> : 'Scaffold'}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>

      {/* New file creation dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="md" fullWidth>
        <Box component="form" onSubmit={handleCreateFile}>
          <DialogTitle sx={{ fontWeight: 700 }}>Create New File</DialogTitle>
          <Divider sx={{ borderColor: '#24304f' }} />
          <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 3 }}>
            <TextField
              label="Relative Path (from Workspace root)"
              value={newFilePath}
              onChange={(e) => setNewFilePath(e.target.value)}
              placeholder="e.g., backend/app/utils/validator.py"
              fullWidth
              required
            />
            <TextField
              label="Boilerplate File Content"
              value={newFileContent}
              onChange={(e) => setNewFileContent(e.target.value)}
              placeholder="# Write initial codes here..."
              multiline
              rows={8}
              fullWidth
              sx={{
                '& .MuiOutlinedInput-root': {
                  fontFamily: 'Fira Code, monospace',
                  fontSize: '0.85rem',
                },
              }}
            />
          </DialogContent>
          <DialogActions sx={{ p: 2.5 }}>
            <Button onClick={() => setCreateDialogOpen(false)} sx={{ color: 'text.secondary' }}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={!newFilePath.trim() || creatingFile}
              sx={{ bgcolor: 'accent.primary', color: 'brand.bg', fontWeight: 700 }}
            >
              {creatingFile ? <CircularProgress size={20} color="inherit" /> : 'Create File'}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Box>
  );
}
