const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const pdfParse = require('pdf-parse');
const sessionService = require('../services/session');
const anthropic = require('../services/anthropic');
const extractionService = require('../services/extraction');
const { chatLimiter } = require('../middleware/rateLimiter');

// ── Multer configuration ──────────────────────────────────────────────
const uploadsDir = path.join(__dirname, '../../uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, uploadsDir),
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1e9);
    const ext = path.extname(file.originalname);
    cb(null, `${uniqueSuffix}${ext}`);
  },
});

const ALLOWED_TYPES = {
  'image/jpeg': 'image',
  'image/jpg': 'image',
  'image/png': 'image',
  'application/pdf': 'pdf',
};

const upload = multer({
  storage,
  limits: { fileSize: 10 * 1024 * 1024 }, // 10 MB
  fileFilter: (req, file, cb) => {
    if (ALLOWED_TYPES[file.mimetype]) {
      cb(null, true);
    } else {
      cb(new Error('Only JPG, JPEG, PNG, and PDF files are allowed'));
    }
  },
});

// ── Helper: process an uploaded file for Claude ───────────────────────
async function processFile(file) {
  const category = ALLOWED_TYPES[file.mimetype]; // 'image' or 'pdf'

  if (category === 'image') {
    const buffer = fs.readFileSync(file.path);
    return {
      type: 'image',
      filename: file.originalname,
      mediaType: file.mimetype,
      base64: buffer.toString('base64'),
      size: file.size,
    };
  }

  if (category === 'pdf') {
    const buffer = fs.readFileSync(file.path);
    const pdfData = await pdfParse(buffer);
    return {
      type: 'pdf',
      filename: file.originalname,
      extractedText: pdfData.text,
      pageCount: pdfData.numpages,
      size: file.size,
    };
  }

  throw new Error(`Unsupported file type: ${file.mimetype}`);
}

// ── POST /api/chat/message — Send a message (with optional file) ─────
router.post('/message', chatLimiter, upload.single('file'), async (req, res, next) => {
  try {
    const { session_id, content } = req.body;

    if (!session_id) {
      return res.status(400).json({ error: 'session_id is required' });
    }

    // At least content or a file must be provided
    if (!content && !req.file) {
      return res.status(400).json({ error: 'content or file is required' });
    }

    // Verify session exists and is active
    const session = await sessionService.getSession(session_id);
    if (!session) {
      return res.status(404).json({ error: 'Session not found' });
    }
    if (session.status !== 'active') {
      return res.status(400).json({ error: 'Session is no longer active' });
    }

    let messageContent;       // What we send to Claude (string or content-block array)
    let storedContent;         // What we store in the DB (always a string)
    let attachmentMeta = [];   // Metadata stored in the attachments JSONB column

    if (req.file) {
      // Process the uploaded file
      const fileData = await processFile(req.file);

      // Build multimodal content for Claude
      messageContent = anthropic.buildMultimodalContent(content || '', fileData);

      // For DB storage, keep a text representation
      if (fileData.type === 'image') {
        storedContent = content
          ? `${content}\n\n[Attached image: ${fileData.filename}]`
          : `[Attached image: ${fileData.filename}]`;
      } else {
        storedContent = content
          ? `${content}\n\n[Attached PDF: ${fileData.filename} — ${fileData.pageCount} pages]`
          : `[Attached PDF: ${fileData.filename} — ${fileData.pageCount} pages]`;
      }

      attachmentMeta = [{
        filename: fileData.filename,
        type: fileData.type,
        size: fileData.size,
        storedAs: req.file.filename,
        ...(fileData.pageCount ? { pageCount: fileData.pageCount } : {}),
      }];
    } else {
      // Text-only message
      messageContent = content;
      storedContent = content;
    }

    // Store user message in DB (text representation)
    await sessionService.addMessage(session_id, 'user', storedContent, attachmentMeta);

    // Get full conversation history from DB
    const dbMessages = await sessionService.getMessages(session_id);

    // Build the messages array for Claude.
    // For all previous messages, use the stored text content.
    // For the CURRENT message (last one), use the multimodal content if applicable.
    const claudeMessages = dbMessages.map((m, idx) => {
      if (idx === dbMessages.length - 1 && req.file) {
        // Current message with file — use multimodal content
        return { role: m.role, content: messageContent };
      }
      return { role: m.role, content: m.content };
    });

    // Send to Claude
    const aiResponse = await anthropic.chat(claudeMessages);

    // Store assistant response
    await sessionService.addMessage(session_id, 'assistant', aiResponse);

    // Check if intake is complete
    const isComplete = aiResponse.includes('[INTAKE_COMPLETE]');

    res.json({
      role: 'assistant',
      content: aiResponse,
      is_complete: isComplete,
    });
  } catch (err) {
    // Clean up uploaded file on error
    if (req.file && fs.existsSync(req.file.path)) {
      fs.unlinkSync(req.file.path);
    }
    next(err);
  }
});

// ── POST /api/chat/:sessionId/complete — Trigger extraction ──────────
router.post('/:sessionId/complete', async (req, res, next) => {
  try {
    const { sessionId } = req.params;

    // Verify session exists
    const session = await sessionService.getSession(sessionId);
    if (!session) {
      return res.status(404).json({ error: 'Session not found' });
    }

    // Run extraction
    const intake = await extractionService.extractIntakeData(sessionId);

    // Mark session as completed
    await sessionService.updateSessionStatus(sessionId, 'completed');

    res.json({
      message: 'Intake extraction complete',
      intake,
    });
  } catch (err) {
    next(err);
  }
});

// ── Multer error handler ─────────────────────────────────────────────
router.use((err, req, res, next) => {
  if (err instanceof multer.MulterError) {
    if (err.code === 'LIMIT_FILE_SIZE') {
      return res.status(400).json({ error: 'File too large. Maximum size is 10MB.' });
    }
    return res.status(400).json({ error: err.message });
  }
  if (err.message && err.message.includes('Only JPG')) {
    return res.status(400).json({ error: err.message });
  }
  next(err);
});

module.exports = router;
