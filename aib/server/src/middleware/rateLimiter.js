const rateLimit = require('express-rate-limit');

// General API rate limiter
const apiLimiter = rateLimit({
  windowMs: 1 * 60 * 1000, // 1 minute
  max: 60,
  message: { error: 'Too many requests, please try again later.' },
  standardHeaders: true,
  legacyHeaders: false,
});

// Chat-specific rate limiter (more restrictive since it calls Claude)
const chatLimiter = rateLimit({
  windowMs: 1 * 60 * 1000, // 1 minute
  max: 20,
  message: { error: "You're moving fast — give it a moment and try again." },
  standardHeaders: true,
  legacyHeaders: false,
});

module.exports = { apiLimiter, chatLimiter };
