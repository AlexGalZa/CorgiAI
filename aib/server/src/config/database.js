const { Pool } = require('pg');
const env = require('./env');

const pool = new Pool(
  env.db.connectionString
    ? { connectionString: env.db.connectionString }
    : {
        host: env.db.host,
        port: env.db.port,
        database: env.db.database,
        user: env.db.user,
        password: env.db.password,
      }
);

pool.on('error', (err) => {
  console.error('Unexpected database pool error:', err);
});

async function query(text, params) {
  const start = Date.now();
  const result = await pool.query(text, params);
  const duration = Date.now() - start;
  if (env.nodeEnv === 'development') {
    console.log('DB query', { text: text.substring(0, 80), duration: `${duration}ms`, rows: result.rowCount });
  }
  return result;
}

async function getClient() {
  return pool.connect();
}

async function testConnection() {
  try {
    await pool.query('SELECT NOW()');
    console.log('Database connected successfully');
    return true;
  } catch (err) {
    console.error('Database connection failed:', err.message);
    return false;
  }
}

module.exports = { query, getClient, pool, testConnection };
