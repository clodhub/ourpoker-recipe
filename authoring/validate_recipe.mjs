// Runs the clodhub catalogue validator on recipe.json. Usage: node --import ./authoring/register-ts-js.mjs authoring/validate_recipe.mjs
// The clodhub checkout is CLODHUB, else ../../clodhub beside the recipes folder. The validator reads every folder of the
// components directory it is given, so it is given a temporary one holding copies of only the components this recipe
// names (slot components and job candidates), from OURPOKER_COMPONENTS, else ../../components.
import { spawnSync } from "node:child_process";
import { cpSync, existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const here = fileURLToPath(new URL("..", import.meta.url));
const clodhub = process.env.CLODHUB ?? join(here, "..", "..", "clodhub");
if (!existsSync(join(clodhub, 'shared/src/foundations.ts'))) throw new Error('Selected catalogue validator has no foundation contract; set CLODHUB to a compatible checkout');
const components = process.env.OURPOKER_COMPONENTS ?? join(here, '..', '..', 'components');
const recipe = JSON.parse(readFileSync(join(here, 'recipe.json'), 'utf8'));
const short = (name) => name.slice(name.lastIndexOf('/') + 1);
const names = new Set([...recipe.components.map((slot) => short(slot.preferred.name)),
  ...(recipe.jobs ?? []).flatMap((job) => job.candidates.map((candidate) => short(candidate.component)))]);
const folder = mkdtempSync(join(tmpdir(), 'ourpoker-components-'));
let result;
try {
  for (const name of names) {
    const source = join(components, name);
    const manifest = JSON.parse(readFileSync(join(source, 'component.json'), 'utf8'));
    for (const path of ['component.json', ...manifest.files.map((file) => file.path)]) cpSync(join(source, path), join(folder, name, path));
  }
  result = spawnSync(process.execPath, [join(clodhub, 'scripts/validate-recipe-file.ts'), join(here, 'recipe.json'), '--components', folder], { stdio: 'inherit' });
} finally {
  rmSync(folder, { recursive: true, force: true });
}
if (result.error) throw result.error;
process.exit(result.status ?? 1);
