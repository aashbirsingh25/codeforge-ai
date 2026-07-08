import { useEffect, useState } from 'react';
import { Snackbar, Alert } from '@mui/material';
import { subscribeToErrors } from '../services/api';

export default function ErrorSnackbar() {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    // Subscribe to global Axios interceptor errors
    const unsubscribe = subscribeToErrors((errMsg) => {
      setMessage(errMsg);
      setOpen(true);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const handleClose = (_?: any, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    };
    setOpen(false);
  };

  return (
    <Snackbar
      open={open}
      autoHideDuration={6000}
      onClose={handleClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
    >
      <Alert
        onClose={handleClose}
        severity="error"
        variant="filled"
        sx={{
          width: '100%',
          bgcolor: 'error.main',
          color: '#ffffff',
          fontWeight: 600,
          borderRadius: '8px',
          boxShadow: '0 4px 20px rgba(239, 68, 68, 0.3)',
        }}
      >
        {message}
      </Alert>
    </Snackbar>
  );
}
