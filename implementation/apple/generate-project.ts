// Writes the Xcode project description (project.yml, the Info.plist files, export options) for the design's Apple
// targets with apple-host's renderer and installed settings. Run from this folder: `node generate-project.ts`, then
// `xcodegen generate`. SERVER_ADDRESS replaces the server address the design was installed with.
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { appleHostSettings, renderApple, writeApple } from "../components/apple-host/server/index.ts";

const components = new URL("../components/", import.meta.url);
const has = (path: string) => existsSync(new URL(path, components));
// Every installed component's Swift sources join the application's module; apple-host adds its own.
const componentSources = readdirSync(components).filter((name) => name !== "apple-host" && has(`${name}/apple/Sources`)).sort().map((name) => `../components/${name}/apple/Sources`);
const video = has("video-calls/apple/Sources");
const { files, message } = renderApple(appleHostSettings, {
  componentSources,
  packages: video ? [{ name: "LiveKit", url: "https://github.com/livekit/client-sdk-swift", from: "2.18.0" }] : [],
  serverAddress: process.env.SERVER_ADDRESS ?? "{{serverAddress}}",
  signingPrefix: "{{signingEnvironmentPrefix}}",
  appCategory: "public.app-category.card-games",
  cameraUsage: "Shows your face to the other players at the table.",
  microphoneUsage: "Lets the other players hear you.",
});
writeApple(fileURLToPath(new URL(".", import.meta.url)), files);
if (video) {
  const dependencyRoot = new URL('./dependency-locks/', import.meta.url);
  const inventory = JSON.parse(readFileSync(new URL('inventory.json', dependencyRoot), 'utf8'));
  if (!Array.isArray(inventory) || inventory.length !== 1 || inventory[0].path !== 'Package.resolved') throw new Error('invalid Apple dependency inventory');
  const source = new URL('Package.resolved', dependencyRoot);
  if (createHash('sha256').update(readFileSync(source)).digest('hex') !== inventory[0].digest) throw new Error('Apple dependency digest mismatch');
  const target = new URL('./OurPoker.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/', import.meta.url);
  mkdirSync(target, { recursive: true });
  cpSync(source, new URL('Package.resolved', target));
}
// The string catalogue with the design's languages only: the installed one holds all four.
const languages = "{{languages}}".split(" ");
const catalogue = JSON.parse(readFileSync(new URL("./strings/Localizable.xcstrings", import.meta.url), "utf8"));
for (const entry of Object.values(catalogue.strings) as { localizations: Record<string, unknown> }[]) {
  for (const code of Object.keys(entry.localizations)) if (!languages.includes(code)) delete entry.localizations[code];
}
writeFileSync(new URL("./OurPoker/Resources/Localizable.xcstrings", import.meta.url), JSON.stringify(catalogue, null, 2) + "\n");
console.log(`${message} Languages: ${languages.join(" ")}.`);
