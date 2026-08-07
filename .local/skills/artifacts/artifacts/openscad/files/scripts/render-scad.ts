import { spawn } from 'node:child_process';
import { mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

const input = resolve('src/model.scad');
const output = resolve('public/model.stl');

await mkdir(dirname(output), { recursive: true });

const child = spawn('openscad', ['-o', output, input], { stdio: 'inherit' });

child.on('error', (error: NodeJS.ErrnoException) => {
  if (error.code === 'ENOENT') {
    console.error(
      'OpenSCAD is not installed. Add pkgs.openscad to the repl Nix environment, reload it, then rerun this command.',
    );
    process.exit(1);
  }

  throw error;
});

child.on('exit', (code) => {
  process.exit(code ?? 1);
});
