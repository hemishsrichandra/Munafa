import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { SessionGate } from './session';
import { PwaControls } from './pwa';
import './styles.css';

createRoot(document.getElementById('root')).render(
  <>
    <PwaControls />
    <SessionGate>
      <App />
    </SessionGate>
  </>,
);
