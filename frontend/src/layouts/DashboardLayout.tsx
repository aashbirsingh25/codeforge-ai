import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Chip,
  Paper,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Chat as ChatIcon,
  PlayArrow as PlayArrowIcon,
  Folder as FolderIcon,
  Storage as StorageIcon,
  Assessment as AssessmentIcon,
  Settings as SettingsIcon,
  Construction as ConstructionIcon,
  Circle as CircleIcon,
} from '@mui/icons-material';

const drawerWidth = 260;

const navItems = [
  { path: '/', label: 'Dashboard', icon: DashboardIcon },
  { path: '/chat', label: 'AI Chat', icon: ChatIcon },
  { path: '/execution', label: 'Execution & Plan', icon: PlayArrowIcon },
  { path: '/workspace', label: 'Workspace', icon: FolderIcon },
  { path: '/memory', label: 'Memory Explorer', icon: StorageIcon },
  { path: '/metrics', label: 'Metrics', icon: AssessmentIcon },
  { path: '/settings', label: 'Settings', icon: SettingsIcon },
];

export default function DashboardLayout() {
  const location = useLocation();

  return (
    <Box sx={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', bgcolor: 'brand.bg' }}>
      {/* Sidebar navigation */}
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            bgcolor: 'brand.panel',
            borderRight: '1px solid #24304f',
            display: 'flex',
            flexDirection: 'column',
          },
        }}
      >
        {/* Title logo block */}
        <Box
          sx={{
            p: 3,
            borderBottom: '1px solid #24304f',
            display: 'flex',
            alignItems: 'center',
            gap: 1.5,
          }}
        >
          <ConstructionIcon sx={{ color: 'accent.primary', fontSize: 26 }} />
          <Typography
            variant="h6"
            sx={{
              fontWeight: 800,
              letterSpacing: '-0.5px',
              background: 'linear-gradient(90deg, #fff 0%, #94a3b8 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            CodeForge AI
          </Typography>
        </Box>

        {/* Sidebar Nav Items */}
        <List sx={{ flex: 1, px: 2, py: 3, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <ListItem key={item.path} disablePadding>
                <ListItemButton
                  component={Link}
                  to={item.path}
                  sx={{
                    borderRadius: '8px',
                    py: 1.25,
                    px: 2,
                    mb: 0.5,
                    color: isActive ? 'accent.primary' : 'text.secondary',
                    background: isActive
                      ? 'linear-gradient(90deg, rgba(0, 242, 254, 0.08) 0%, rgba(79, 172, 254, 0.08) 100%)'
                      : 'transparent',
                    borderLeft: isActive ? '3px solid #00f2fe' : '3px solid transparent',
                    '&:hover': {
                      color: 'text.primary',
                      bgcolor: 'rgba(255, 255, 255, 0.04)',
                    },
                    transition: 'all 0.2s ease-in-out',
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 36, color: 'inherit' }}>
                    <Icon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Typography
                        variant="body2"
                        sx={{
                          fontSize: '0.875rem',
                          fontWeight: isActive ? 600 : 500,
                        }}
                      >
                        {item.label}
                      </Typography>
                    }
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>

        {/* Core Status indicator at bottom */}
        <Box sx={{ p: 2, borderTop: '1px solid #24304f' }}>
          <Paper
            variant="outlined"
            sx={{
              p: 1.5,
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              bgcolor: 'rgba(27, 35, 58, 0.5)',
              borderColor: '#24304f',
              borderRadius: '8px',
            }}
          >
            <CircleIcon
              sx={{
                fontSize: 10,
                color: 'accent.green',
                filter: 'drop-shadow(0 0 4px #10b981)',
              }}
            />
            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600 }}>
              Status: Ready
            </Typography>
          </Paper>
        </Box>
      </Drawer>

      {/* Main content frame */}
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        {/* Top Navbar */}
        <AppBar
          position="static"
          color="transparent"
          elevation={0}
          sx={{
            borderBottom: '1px solid #24304f',
            bgcolor: 'brand.panel',
            zIndex: (theme) => theme.zIndex.drawer + 1,
          }}
        >
          <Toolbar sx={{ justifyContent: 'space-between', px: 4 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Typography variant="body2" sx={{ color: 'text.secondary', fontWeight: 500 }}>
                Environment:
              </Typography>
              <Chip
                label="production-foundation-refactor"
                size="small"
                sx={{
                  bgcolor: 'brand.card',
                  border: '1px solid #24304f',
                  color: 'accent.primary',
                  fontFamily: 'Fira Code, monospace',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  borderRadius: '4px',
                }}
              />
            </Box>
            <Box sx={{ textAlign: 'right' }}>
              <Typography variant="body2" sx={{ color: 'text.primary', fontWeight: 600 }}>
                Flagship Autonomous Agent Platform
              </Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontFamily: 'Fira Code, monospace' }}>
                v2.0.0-dev
              </Typography>
            </Box>
          </Toolbar>
        </AppBar>

        {/* Dynamic Route View Page */}
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: 4,
            overflowY: 'auto',
            bgcolor: 'brand.bg',
          }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
