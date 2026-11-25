// Runs the clodhub catalogue validator on recipe.json. Usage: node --import ./authoring/register-ts-js.mjs authoring/validate_recipe.mjs
// The clodhub checkout is CLODHUB, else ../../clodhub beside the recipes folder.
import { spawnSync } from "node:child_process";
import { existsSync } from 'node:fs';
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const here = fileURLToPath(new URL("..", import.meta.url));
const clodhub = process.env.CLODHUB ?? join(here, "..", "..", "clodhub");
if (!existsSync(join(clodhub, 'shared/src/foundations.ts'))) throw new Error('Selected catalogue validator has no foundation contract; set CLODHUB to a compatible checkout');
const components = process.env.OURPOKER_COMPONENTS ?? join(here, '..', '..', 'components');
const result = spawnSync(process.execPath, [join(clodhub, 'scripts/validate-recipe-file.ts'), join(here, 'recipe.json'), '--components', components], { stdio: 'inherit' });
if (result.error) throw result.error;
process.exit(result.status ?? 1);
