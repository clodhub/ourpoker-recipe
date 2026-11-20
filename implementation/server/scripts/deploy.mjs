// Runs `wrangler deploy` with the given arguments from the current folder, with the server's installed Wrangler, or,
// when the server's dependencies are not installed, the version its package.json pins through npx. On a first deploy to a new worker name,
// Cloudflare can answer "This Worker does not exist" (code 10007) right after the upload, while the new worker is not
// yet visible; the deploy is then run again after 10, 20, 40 and 80 seconds until it passes.
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const server = join(dirname(fileURLToPath(import.meta.url)), "..");
const installed = join(server, "node_modules", ".bin", process.platform === "win32" ? "wrangler.cmd" : "wrangler");
const pinned = JSON.parse(readFileSync(join(server, "package.json"), "utf8")).devDependencies.wrangler;
const [wrangler, prefix] = existsSync(installed) ? [installed, []] : ["npx", ["--yes", `wrangler@${pinned}`]];
const args = [...prefix, "deploy", ...process.argv.slice(2)];
for (const wait of [0, 10, 20, 40, 80]) {
  if (wait) {
    console.error(`The new worker is not visible to Cloudflare yet; deploying again in ${wait} seconds.`);
    await new Promise((resolve) => setTimeout(resolve, wait * 1000));
  }
  const result = spawnSync(wrangler, args, { encoding: "utf8", shell: process.platform === "win32", stdio: ["inherit", "pipe", "pipe"] });
  process.stdout.write(result.stdout ?? "");
  process.stderr.write(result.stderr ?? "");
  if (result.status === 0) process.exit(0);
  if (!/code: 10007/.test(`${result.stdout}${result.stderr}`)) process.exit(result.status ?? 1);
}
process.exit(1);
