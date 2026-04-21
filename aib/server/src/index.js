const express = require('express');
const cors = require('cors');
const path = require('path');
const env = require('./config/env');
const { testConnection } = require('./config/database');
const errorHandler = require('./middleware/errorHandler');
const { apiLimiter } = require('./middleware/rateLimiter');

// Routes
const sessionsRouter = require('./routes/sessions');
const chatRouter = require('./routes/chat');
const intakesRouter = require('./routes/intakes');

const app = express();

// Middleware
app.use(cors({
  origin: env.frontendUrl,
  credentials: true,
}));
app.use(express.json({ limit: '10mb' }));
app.use(apiLimiter);

// API Routes
app.use('/api/sessions', sessionsRouter);
app.use('/api/chat', chatRouter);
app.use('/api/intakes', intakesRouter);

// Health check
app.get('/api/health', async (req, res) => {
  const dbOk = await testConnection();
  res.json({
    status: dbOk ? 'healthy' : 'degraded',
    database: dbOk ? 'connected' : 'disconnected',
    timestamp: new Date().toISOString(),
  });
});

// Serve frontend static files in production
if (env.nodeEnv === 'production') {
  const frontendPath = path.join(__dirname, '../../client/dist');
  app.use(express.static(frontendPath));
  app.get('*', (req, res) => {
    res.sendFile(path.join(frontendPath, 'index.html'));
  });
}

// Error handler (must be last)
app.use(errorHandler);

// Start server
async function start() {
  const dbOk = await testConnection();
  if (!dbOk) {
    console.warn('Warning: Database not available. Some features will not work.');
  }

  app.listen(env.port, () => {
    console.log(`AIB Server running on port ${env.port}`);
    console.log(`Environment: ${env.nodeEnv}`);
    console.log(`Frontend URL: ${env.frontendUrl}`);
  });
}

start();
