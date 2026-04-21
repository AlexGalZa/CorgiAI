const db = require('../config/database');

/**
 * Create a new session
 * @returns {Promise<object>} - The created session
 */
async function createSession() {
  const result = await db.query(
    `INSERT INTO sessions (status) VALUES ('active') RETURNING *`
  );
  return result.rows[0];
}

/**
 * Get a session by ID
 * @param {string} sessionId - UUID
 * @returns {Promise<object|null>}
 */
async function getSession(sessionId) {
  const result = await db.query(
    `SELECT * FROM sessions WHERE id = $1`,
    [sessionId]
  );
  return result.rows[0] || null;
}

/**
 * Get session with its messages
 * @param {string} sessionId - UUID
 * @returns {Promise<object|null>}
 */
async function getSessionWithMessages(sessionId) {
  const session = await getSession(sessionId);
  if (!session) return null;

  const messages = await db.query(
    `SELECT id, role, content, attachments, created_at 
     FROM messages 
     WHERE session_id = $1 
     ORDER BY created_at ASC`,
    [sessionId]
  );

  return { ...session, messages: messages.rows };
}

/**
 * List sessions with optional status filter
 * @param {string} status - Optional status filter
 * @returns {Promise<Array>}
 */
async function listSessions(status) {
  let query = `SELECT * FROM sessions`;
  const params = [];

  if (status) {
    query += ` WHERE status = $1`;
    params.push(status);
  }

  query += ` ORDER BY created_at DESC`;

  const result = await db.query(query, params);
  return result.rows;
}

/**
 * Update session status
 * @param {string} sessionId - UUID
 * @param {string} status - New status
 * @returns {Promise<object>}
 */
async function updateSessionStatus(sessionId, status) {
  const updates = { status, updated_at: new Date() };
  if (status === 'completed') {
    updates.completed_at = new Date();
  }

  const result = await db.query(
    `UPDATE sessions 
     SET status = $1, updated_at = $2, completed_at = $3
     WHERE id = $4 
     RETURNING *`,
    [updates.status, updates.updated_at, updates.completed_at || null, sessionId]
  );
  return result.rows[0];
}

/**
 * Add a message to a session
 * @param {string} sessionId - UUID
 * @param {string} role - 'user' or 'assistant'
 * @param {string} content - Message text
 * @param {Array} attachments - Optional file metadata
 * @returns {Promise<object>}
 */
async function addMessage(sessionId, role, content, attachments = []) {
  const result = await db.query(
    `INSERT INTO messages (session_id, role, content, attachments) 
     VALUES ($1, $2, $3, $4) 
     RETURNING *`,
    [sessionId, role, content, JSON.stringify(attachments)]
  );

  // Update session timestamp
  await db.query(
    `UPDATE sessions SET updated_at = NOW() WHERE id = $1`,
    [sessionId]
  );

  return result.rows[0];
}

/**
 * Get all messages for a session
 * @param {string} sessionId - UUID
 * @returns {Promise<Array>}
 */
async function getMessages(sessionId) {
  const result = await db.query(
    `SELECT id, role, content, attachments, created_at 
     FROM messages 
     WHERE session_id = $1 
     ORDER BY created_at ASC`,
    [sessionId]
  );
  return result.rows;
}

module.exports = {
  createSession,
  getSession,
  getSessionWithMessages,
  listSessions,
  updateSessionStatus,
  addMessage,
  getMessages,
};
