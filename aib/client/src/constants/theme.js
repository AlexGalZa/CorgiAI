// Corgi Insurance Broker brand theme
export const theme = {
  colors: {
    primary: '#E8751A',       // Brand orange
    primaryDark: '#C5610F',   // Darker orange for hover
    primaryLight: '#FFF3E8',  // Light orange background
    secondary: '#2D3748',     // Dark slate
    background: '#F7FAFC',    // Light gray background
    surface: '#FFFFFF',       // White surface
    text: '#1A202C',          // Near black text
    textSecondary: '#718096', // Gray text
    textLight: '#A0AEC0',    // Light gray text
    border: '#E2E8F0',       // Light border
    success: '#48BB78',       // Green
    error: '#F56565',         // Red
    warning: '#ECC94B',       // Yellow
    userBubble: '#E8751A',    // Orange for user messages
    assistantBubble: '#F7FAFC', // Light gray for assistant messages
  },
  fonts: {
    body: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
  borderRadius: {
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '20px',
    full: '9999px',
  },
  shadows: {
    sm: '0 1px 3px rgba(0, 0, 0, 0.08)',
    md: '0 4px 6px rgba(0, 0, 0, 0.07)',
    lg: '0 10px 25px rgba(0, 0, 0, 0.1)',
  },
};

export const quickStartChips = [
  "I need cyber liability insurance",
  "Looking for D&O coverage",
  "Help me with EPL insurance",
  "I need ERISA/fiduciary coverage",
  "Media liability insurance",
  "Not sure what I need — help me figure it out",
];
