const express = require('express');
const router = express.Router();
const extractionService = require('../services/extraction');
const sessionService = require('../services/session');

// GET /api/intakes — List all completed intakes
router.get('/', async (req, res, next) => {
  try {
    const intakes = await extractionService.listIntakes();
    res.json(intakes);
  } catch (err) {
    next(err);
  }
});

// GET /api/intakes/:sessionId — Get extracted data for a specific intake
router.get('/:sessionId', async (req, res, next) => {
  try {
    const intake = await extractionService.getIntake(req.params.sessionId);
    if (!intake) {
      return res.status(404).json({ error: 'Intake not found' });
    }
    res.json(intake);
  } catch (err) {
    next(err);
  }
});

// GET /api/intakes/:sessionId/transcript — Get full conversation transcript
router.get('/:sessionId/transcript', async (req, res, next) => {
  try {
    const session = await sessionService.getSessionWithMessages(req.params.sessionId);
    if (!session) {
      return res.status(404).json({ error: 'Session not found' });
    }

    const transcript = session.messages.map(m => ({
      role: m.role,
      content: m.content,
      timestamp: m.created_at,
    }));

    res.json({
      session_id: session.id,
      status: session.status,
      created_at: session.created_at,
      completed_at: session.completed_at,
      transcript,
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
