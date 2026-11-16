import { assert, load } from './runtime.mjs';
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const m = await load('server/index.ts');
const settings = { packageId: 'org.example.classdemo', applicationName: 'Class Demo', minSdk: 26 };
const rendered = m.renderAndroid(settings);
assert.deepEqual(m.renderAndroid(settings), rendered);
assert.match(rendered['app/build.gradle.kts'], /applicationId = "org.example.classdemo"/);
assert.match(rendered['app/build.gradle.kts'], /minSdk = 26/);
assert.ok(!rendered['app/src/main/AndroidManifest.xml'].includes('android.permission.CAMERA'));
assert.match(rendered['gradle/wrapper/gradle-wrapper.properties'], /distributionSha256Sum=[a-f0-9]{64}/);
assert.throws(() => m.validateSettings({ ...settings, packageId: '../bad' }));
assert.equal(m.resolveLanguage('fr-CA', ['en', 'fr'], 'en'), 'fr');
assert.throws(() => m.writeWrapper('unused', { '../outside': 'bad' }));
assert.throws(() => m.writeWrapper('unused', {}));
const directory = mkdtempSync(join(tmpdir(), 'android-class-'));
try {
  m.writeWrapper(directory);
  assert.match(readFileSync(join(directory, 'app/gradle.lockfile'), 'utf8'), /androidx\.compose/);
  assert.match(readFileSync(join(directory, 'gradle/verification-metadata.xml'), 'utf8'), /<sha256 value="[a-f0-9]{64}"/);
  const wrapper = readFileSync(join(directory, 'gradle/wrapper/gradle-wrapper.jar'));
  assert.equal(wrapper.subarray(0, 2).toString(), 'PK');
  const paths = ['buildscript-gradle.lockfile', 'app/buildscript-gradle.lockfile', 'app/gradle.lockfile', 'gradle/verification-metadata.xml'];
  const files = Object.fromEntries(paths.map(path => [path, readFileSync(join(directory, path), 'utf8')]));
  const missing = { ...files };
  delete missing['buildscript-gradle.lockfile'];
  const malformed = { ...files, 'app/gradle.lockfile': 'not a lock line' };
  const mismatch = { ...files, 'app/gradle.lockfile': files['app/gradle.lockfile'] + '\norg.example:missing:1.0.0=debugCompileClasspath\n' };
  const checksum = { ...files, 'gradle/verification-metadata.xml': files['gradle/verification-metadata.xml'].replace(/<sha256 value="[a-f0-9]{64}"/, '<sha256 value="bad"') };
  const empty = { ...files, 'app/gradle.lockfile': '' };
  const extra = { ...files, '../outside': 'bad' };
  const malformedXml = { ...files, 'gradle/verification-metadata.xml': files['gradle/verification-metadata.xml'].replace('</components>', '') };
  const duplicate = { ...files, 'buildscript-gradle.lockfile': files['buildscript-gradle.lockfile'] + '\nempty=classpath\nempty=classpath\n' };
  for (const [index, invalid] of [missing, malformed, mismatch, checksum, empty, extra, malformedXml, duplicate].entries()) {
    const output = join(directory, 'invalid-' + index);
    assert.throws(() => m.writeWrapper(output, invalid));
    assert.equal(existsSync(output), false);
  }
} finally {
  rmSync(directory, { recursive: true, force: true });
}
