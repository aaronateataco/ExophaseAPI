import { spawn, type ChildProcess } from 'node:child_process';
import { watch } from 'node:fs';

let child: ChildProcess | null = null;
let queued = false;

function render() {
  if (child) {
    queued = true;
    return;
  }

  child = spawn('tsx', ['scripts/render-scad.ts'], { stdio: 'inherit' });
  child.on('exit', () => {
    child = null;
    if (queued) {
      queued = false;
      render();
    }
  });
}

render();
// Watch the directory, not the file. Editors and the agent's file APIs save
// atomically (write a temp file, then rename over the target), which swaps the
// file's inode; a file-level watch stays bound to the old inode and misses
// every edit after the first. Watching src/ and filtering survives replacement.
watch('src', { persistent: true }, (_event, filename) => {
  if (filename === 'model.scad') {
    render();
  }
});
