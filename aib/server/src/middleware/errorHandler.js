/**
 * Global error handler middleware
 */
function errorHandler(err, req, res, next) {
  console.error('Error:', err.message);
  if (process.env.NODE_ENV === 'development') {
    console.error(err.stack);
  }

  // Anthropic API errors
  if (err.status && err.type) {
    return res.status(502).json({
      error: 'AI service error',
      message: 'Failed to get response from AI. Please try again.',
    });
  }

  // Database errors
  if (err.code && err.code.startsWith('2')) {
    return res.status(500).json({
      error: 'Database error',
      message: 'An internal error occurred. Please try again.',
    });
  }

  // JSON parse errors
  if (err.type === 'entity.parse.failed') {
    return res.status(400).json({
      error: 'Invalid JSON',
      message: 'Request body contains invalid JSON.',
    });
  }

  const statusCode = err.statusCode || 500;
  res.status(statusCode).json({
    error: err.message || 'Internal server error',
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
  });
}

module.exports = errorHandler;
