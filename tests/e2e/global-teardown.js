const { execSync } = require('child_process');

async function globalTeardown() {
  console.log('Stopping Flask development server...');
  
  try {
    // Kill any remaining Flask processes on test port 8001
    execSync('pkill -f "python.*run.py" || true', { stdio: 'ignore' });
    execSync('lsof -ti:8001 | xargs kill -9 || true', { stdio: 'ignore' });
    console.log('Flask server stopped');
  } catch (error) {
    console.log('Error stopping Flask server (may already be stopped):', error.message);
  }
}

module.exports = globalTeardown;