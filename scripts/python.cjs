const { spawn } = require('node:child_process');
const path = require('node:path');
const python = path.join(
  process.cwd(),
  '.venv',
  process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
);
const child = spawn(python, process.argv.slice(2), { stdio: 'inherit', env: process.env });
child.on('error', (error) => {
  console.error(error.message);
  process.exit(1);
});
child.on('exit', (code) => process.exit(code ?? 1));
