const { spawn, execSync } = require('child_process');
const path = require('path');

let flaskProcess = null;

async function globalSetup() {
  console.log('Starting Flask development server...');
  
  // Use port 8001 for testing
  const testPort = 8001;
  console.log(`Using port ${testPort} for tests`);
  
  // Kill any existing processes on the test port
  try {
    execSync(`lsof -ti:${testPort} | xargs kill -9 || true`, { stdio: 'ignore' });
    await new Promise(resolve => setTimeout(resolve, 1000)); // Wait for cleanup
  } catch (error) {
    // Ignore errors, port might not be in use
  }
  
  // Start Flask development server
  const flaskScript = path.join(__dirname, '..', '..', 'run.py');
  
  flaskProcess = spawn('python', [flaskScript], {
    env: {
      ...process.env,
      FLASK_ENV: 'development',
      DEBUG: 'false',
      DB_INIT_ON_START: 'false',
      PORT: testPort.toString(),
      // Use test database or in-memory database
      DATABASE_URL: 'sqlite:///:memory:',
      TESTING: 'true'
    },
    stdio: ['pipe', 'pipe', 'pipe']
  });

  // Wait for Flask to start
  return new Promise((resolve, reject) => {
    let output = '';
    
    flaskProcess.stdout.on('data', (data) => {
      output += data.toString();
      console.log('Flask stdout:', data.toString());
      
      // Check if Flask is ready
      if (output.includes('Running on http://127.0.0.1:8001') || 
          output.includes('Running on http://0.0.0.0:8001') ||
          output.includes('* Running on all addresses')) {
        console.log('Flask server detected as ready!');
        setTimeout(() => resolve(), 3000); // Give it 3 seconds to be fully ready
      }
    });

    flaskProcess.stderr.on('data', (data) => {
      const stderrOutput = data.toString();
      console.log('Flask stderr:', stderrOutput);
      
      // Also check stderr for startup messages
      if (stderrOutput.includes('Running on http://127.0.0.1:8001') || 
          stderrOutput.includes('Running on http://0.0.0.0:8001') ||
          stderrOutput.includes('* Running on all addresses')) {
        console.log('Flask server detected as ready from stderr!');
        setTimeout(() => resolve(), 3000); // Give it 3 seconds to be fully ready
      }
    });

    flaskProcess.on('error', (error) => {
      console.error('Failed to start Flask:', error);
      reject(error);
    });

    flaskProcess.on('close', (code) => {
      if (code !== 0) {
        console.error(`Flask process exited with code ${code}`);
        reject(new Error(`Flask exited with code ${code}`));
      }
    });

    // Timeout after 30 seconds
    setTimeout(() => {
      reject(new Error('Flask server failed to start within 30 seconds'));
    }, 30000);
  });
}

module.exports = globalSetup;
