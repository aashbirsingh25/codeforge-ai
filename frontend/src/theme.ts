import { createTheme } from '@mui/material/styles';

declare module '@mui/material/styles' {
  interface Palette {
    brand?: {
      bg: string;
      panel: string;
      card: string;
      code: string;
    };
    accent?: {
      primary: string;
      secondary: string;
      green: string;
      red: string;
      purple: string;
    };
  }
  interface PaletteOptions {
    brand?: {
      bg: string;
      panel: string;
      card: string;
      code: string;
    };
    accent?: {
      primary: string;
      secondary: string;
      green: string;
      red: string;
      purple: string;
    };
  }
}

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00f2fe',
      light: '#4facfe',
      dark: '#00b4d8',
      contrastText: '#090d16',
    },
    secondary: {
      main: '#a855f7',
      light: '#c084fc',
      dark: '#7e22ce',
      contrastText: '#ffffff',
    },
    background: {
      default: '#090d16',
      paper: '#111726',
    },
    text: {
      primary: '#f8fafc',
      secondary: '#94a3b8',
      disabled: '#64748b',
    },
    error: {
      main: '#ef4444',
    },
    warning: {
      main: '#f59e0b',
    },
    success: {
      main: '#10b981',
    },
    brand: {
      bg: '#090d16',
      panel: '#111726',
      card: '#1b233a',
      code: '#05080e',
    },
    accent: {
      primary: '#00f2fe',
      secondary: '#4facfe',
      green: '#10b981',
      red: '#ef4444',
      purple: '#a855f7',
    },
  },
  typography: {
    fontFamily: ['Inter', 'sans-serif'].join(','),
    h1: {
      fontWeight: 800,
    },
    h2: {
      fontWeight: 700,
    },
    h3: {
      fontWeight: 700,
    },
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
    subtitle1: {
      fontWeight: 500,
    },
    subtitle2: {
      fontWeight: 500,
    },
    button: {
      textTransform: 'none',
      fontWeight: 600,
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#090d16',
          color: '#f8fafc',
          scrollbarColor: '#1b233a #090d16',
          '&::-webkit-scrollbar': {
            width: '8px',
            height: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: '#090d16',
          },
          '&::-webkit-scrollbar-thumb': {
            background: '#1b233a',
            borderRadius: '4px',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: '#24304f',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: '#111726',
          border: '1px solid #24304f',
          borderRadius: '12px',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
          padding: '8px 16px',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid #24304f',
        },
      },
    },
  },
});

export default theme;
