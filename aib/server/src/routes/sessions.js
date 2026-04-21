const express = require('express');
const router = express.Router();
const sessionService = require('../services/session');

// POST /api/sessions — Create a new session
router.post('/', async (req, res, next) => {
  try {
    const session = await sessionService.createSession();
    res.status(201).json(session);
  } catch (err) {
    next(err);
  }
});

// GET /api/sessions — List all sessions
router.get('/', async (req, res, next) => {
  try {
    const { status } = req.query;
    const sessions = await sessionService.listSessions(status);
    res.json(sessions);
  } catch (err) {
    next(err);
  }
});

// GET /api/sessions/:id — Get session details with messages
router.get('/:id', async (req, res, next) => {
  try {
    const session = await sessionService.getSessionWithMessages(req.params.id);
    if (!session) {
      return res.status(404).json({ error: 'Session not found' });
    }
    res.json(session);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
