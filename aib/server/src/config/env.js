require('dotenv').config({ path: require('path').resolve(__dirname, '../../../.env') });

const required = [
  'ANTHROPIC_API_KEY',
];

for (const key of required) {
  if (!process.env[key]) {
    console.error(`Missing required environment variable: ${key}`);
    process.exit(1);
  }
}

module.exports = {
  anthropicApiKey: process.env.ANTHROPIC_API_KEY,
  db: {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432', 10),
    database: process.env.DB_NAME || 'aib',
    user: process.env.DB_USER || 'aib',
    password: process.env.DB_PASSWORD || 'aib_password',
    connectionString: process.env.DATABASE_URL,
  },
  port: parseInt(process.env.PORT || '3000', 10),
  nodeEnv: process.env.NODE_ENV || 'development',
  frontendUrl: process.env.FRONTEND_URL || 'http://localhost:5173',
};
