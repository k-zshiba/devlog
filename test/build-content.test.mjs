import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, access, rm } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { findSlides, prepareContent, buildSlides } from '../scripts/build-content.mjs';

async function fixture(t, files) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'devlog-content-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const source = path.join(root, 'docs');
  await mkdir(source);
  for (const [name, content] of Object.entries(files)) {
    const filename = path.join(source, name);
    await mkdir(path.dirname(filename), { recursive: true });
    await writeFile(filename, content);
  }
  return { root, source };
}

test('routes only front-matter marp: true to slides and preserves source/assets', async (t) => {
  const files = {
    'article.md': '---\ntitle: Article\n---\n# Article\n',
    'disabled.md': '---\nmarp: false\n---\n# Article\n',
    'plain.md': '# Plain\n\nmarp: true\n',
    'nested/slides.md': '\uFEFF---\r\nmarp: true\r\n---\r\n# Slides\r\n',
    'other.markdown': '---\nmarp: true\n---\n# Other\n',
    'nested/image.svg': '<svg/>',
    '_config.yml': 'theme: minima\n',
  };
  const { root, source } = await fixture(t, files);
  const staged = path.join(root, 'staged');
  assert.deepEqual(await prepareContent(source, staged), ['nested/slides.md', 'other.markdown']);
  await assert.rejects(access(path.join(staged, 'nested/slides.md')), { code: 'ENOENT' });
  for (const name of ['article.md', 'disabled.md', 'plain.md', 'nested/image.svg', '_config.yml']) {
    assert.equal(await readFile(path.join(staged, name), 'utf8'), files[name]);
  }
  for (const [name, content] of Object.entries(files)) {
    assert.equal(await readFile(path.join(source, name), 'utf8'), content);
  }
  // Rebuilding discards stale articles, including one switched to slide mode.
  await writeFile(path.join(source, 'article.md'), '---\nmarp: true\n---\n# Switched');
  await prepareContent(source, staged);
  await assert.rejects(access(path.join(staged, 'article.md')), { code: 'ENOENT' });
});

for (const [name, content, expected] of [
  ['quoted boolean', '---\nmarp: "true"\n---', /marp must be true or false/],
  ['string value', '---\nmarp: slides\n---', /marp must be true or false/],
  ['invalid YAML', '---\nmarp: [\n---', /broken.md:/],
  ['unclosed front matter', '---\nmarp: true\n# Slide', /no closing/],
]) {
  test(`rejects ${name} instead of silently publishing the wrong format`, async (t) => {
    const { source } = await fixture(t, { 'broken.md': content });
    await assert.rejects(findSlides(source), expected);
  });
}

test('sets the preview base path only in the staged Jekyll config', async (t) => {
  const { root, source } = await fixture(t, { '_config.yml': 'theme: minima\n' });
  const staged = path.join(root, 'staged');
  await prepareContent(source, staged, '/devlog/pr-preview/pr-42');
  assert.match(await readFile(path.join(staged, '_config.yml'), 'utf8'), /baseurl: \/devlog\/pr-preview\/pr-42/);
  assert.equal(await readFile(path.join(source, '_config.yml'), 'utf8'), 'theme: minima\n');
});

test('converts a nested Japanese deck to slide HTML without rendering articles', async (t) => {
  const { root, source } = await fixture(t, {
    'talk/deck.md': '---\nmarp: true\ntitle: 日本語テスト\npaginate: true\n---\n# 一枚目\n\n<div class="card">図の内容</div>\n\n---\n\n# 二枚目\n',
    'article.md': '---\nmarp: false\n---\n# Article',
  });
  const destination = path.join(root, 'site');
  assert.deepEqual(await buildSlides(source, destination), ['talk/deck.md']);
  const html = await readFile(path.join(destination, 'talk/deck.html'), 'utf8');
  assert.match(html, /<title>日本語テスト<\/title>/);
  assert.match(html, /一枚目/);
  assert.match(html, /二枚目/);
  assert.match(html, /<div class="card">図の内容<\/div>/);
  assert.equal((html.match(/<section\b/g) || []).length, 2);
  assert.match(html, /data-marpit-pagination-total="2"/);
  await assert.rejects(access(path.join(destination, 'article.html')), { code: 'ENOENT' });
});

test('refuses to overwrite an existing page at the slide URL', async (t) => {
  const { root, source } = await fixture(t, { 'deck.md': '---\nmarp: true\n---\n# Slide' });
  const destination = path.join(root, 'site');
  await mkdir(destination);
  await writeFile(path.join(destination, 'deck.html'), 'existing article');
  await assert.rejects(buildSlides(source, destination), /output already exists/);
  assert.equal(await readFile(path.join(destination, 'deck.html'), 'utf8'), 'existing article');
});
